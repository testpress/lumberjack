import io

from smart_open import open

from django.shortcuts import get_object_or_404

from apps.ffmpeg.main import Manager
from apps.ffmpeg.input_options import InputOptionsFactory
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
            self.set_job_status_as_processing()
            self.job.notify_webhook()
        self.update_output_status(Output.PROCESSING)

        try:
            self.start_transcoding()
            self.update_output_status(Output.COMPLETED)
        except Exception as error:
            self.save_exception(error)
            self.update_output_status(Output.ERROR)

    def initialize(self):
        self.job = Job.objects.get(id=self.job_id)
        self.output = Output.objects.get(id=self.output_id)

    def is_job_status_not_updated(self):
        return self.job.status != Job.PROCESSING

    def set_job_status_as_processing(self):
        self.job.status = Job.PROCESSING
        self.job.save()

    def update_output_status(self, status):
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


class ManifestGeneratorRunnable(CeleryRunnable):
    def do_run(self, *args, **kwargs):
        self.initialize()
        self.generate_manifest_content()
        self.upload()
        self.complete_job()
        self.job.notify_webhook()

    def initialize(self):
        self.job = get_object_or_404(Job, id=self.job_id)
        self.manifest_content = None

    def manifest_header(self):
        return "#EXTM3U\n#EXT-X-VERSION:3\n"

    def upload(self):
        file = io.BytesIO(self.manifest_content.encode()).read()
        options = InputOptionsFactory.get(self.job.output_url)
        with open(self.job.output_url, "wb", transport_params=options) as fout:
            fout.write(file)

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
                f"RESOLUTION={media_detail['resolution']}\n{media_detail['name']}.m3u8\n\n"
            )
        self.manifest_content = content

    def complete_job(self):
        self.job.status = Job.COMPLETED
        self.job.save()
