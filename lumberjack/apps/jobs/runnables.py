from django.shortcuts import get_object_or_404
from django.utils.timezone import now

from lumberjack.celery import app
from apps.ffmpeg.main import Manager, FFMpegException
from apps.ffmpeg.outputs import OutputFactory
from apps.jobs.models import Job, Output


class CeleryRunnable(object):
    REQUIRED_ARGUMENTS = []
    OPTIONAL_ARGUMENTS = []

    def __init__(self, *args, **kwargs):
        if self.REQUIRED_ARGUMENTS:
            for arg in self.REQUIRED_ARGUMENTS:
                if arg not in kwargs:
                    raise CeleryRunnableException("Relation %s is missing" % arg)

        self.__dict__.update(kwargs)

        for arg in self.OPTIONAL_ARGUMENTS:
            if arg not in kwargs:
                self.__dict__[arg] = None

    def do_run(self, *args, **kwargs):
        raise NotImplementedError("do_run method not implemented")

    def run(self, *args, **kwargs):
        self.do_run(*args, **kwargs)


class CeleryRunnableException(Exception):
    def __init__(self, message, cause=None):
        self.cause = cause
        self.message = message
        super(CeleryRunnableException, self).__init__(message, cause)


class VideoTranscoderRunnable(CeleryRunnable):
    def do_run(self, *args, **kwargs):
        self.initialize()

        if self.is_job_status_not_updated():
            self.update_job_start_time_and_initial_status()
            self.job.notify_webhook()
        self.update_output_status_and_time(Output.PROCESSING, start=now())

        try:
            self.start_transcoding()
            self.update_output_status_and_time(Output.COMPLETED, end=now())
        except FFMpegException as error:
            self.save_exception(error)
            self.update_output_status_and_time(Output.ERROR, end=now())
            self.stop_job_and_notify()

    def initialize(self):
        self.job = Job.objects.get(id=self.job_id)
        self.output = Output.objects.get(id=self.output_id)

    def is_job_status_not_updated(self):
        return self.job.status != Job.PROCESSING

    def update_job_start_time_and_initial_status(self):
        self.job.status = Job.PROCESSING
        self.job.start = now()
        self.job.save()

    def update_output_status_and_time(self, status, start=None, end=None):
        if start:
            self.output.start = start

        if end:
            self.output.end = end

        self.output.status = status
        self.output.save()

    def start_transcoding(self):
        ffmpeg_manager = Manager(self.output.settings, self.update_progress)
        ffmpeg_manager.run()

    def is_multiple_of_five(self, percentage):
        return (percentage % 5) == 0 and self.output.progress != percentage

    def update_progress(self, percentage):
        if self.is_multiple_of_five(percentage):
            self.output.progress = percentage
            self.output.save()
            self.job.update_progress()

    def save_exception(self, error):
        self.output.error_message = error
        self.output.save()

    def stop_job_and_notify(self):
        self.job.status = Job.ERROR
        self.job.save()
        self.job.notify_webhook()
        task = app.GroupResult.restore(str(self.job.background_task_id))
        if task:
            task.revoke(terminate=True)


class ManifestGeneratorRunnable(CeleryRunnable):
    def do_run(self, *args, **kwargs):
        self.initialize()
        self.generate_manifest_content()
        self.upload()
        self.complete_job()
        self.job.notify_webhook()

    def initialize(self):
        self.job = get_object_or_404(Job, id=self.job_id)
        self.manifest_content = ""

    def manifest_header(self):
        return "#EXTM3U\n#EXT-X-VERSION:3\n"

    def upload(self):
        storage = OutputFactory.create(self.job.output_url)
        storage.save_text(self.manifest_content, self.job.output_url)

    def get_media_details(self):
        media_details = []
        for output in self.job.outputs.order_by("created"):
            media_detail = {
                "bandwidth": output.video_bitrate,
                "resolution": output.resolution,
                "name": f"{output.name}/video.m3u8",
            }
            media_details.append(media_detail)
        return media_details

    def generate_manifest_content(self):
        content = self.manifest_header()
        media_details = self.get_media_details()
        for media_detail in media_details:
            content += (
                f"#EXT-X-STREAM-INF:BANDWIDTH={media_detail['bandwidth']},"
                f"RESOLUTION={media_detail['resolution']}\n{media_detail['name']}\n\n"
            )
        self.manifest_content = content

    def complete_job(self):
        self.job.status = Job.COMPLETED
        self.job.end = now()
        self.job.save()
