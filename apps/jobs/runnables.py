from django.conf import settings
from django.shortcuts import get_object_or_404

from apps.ffmpeg.main import Manager
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
        self.job = Job.objects.get(id=self.job_id)
        self.output = Output.objects.get(id=self.output_id)

        if self.is_job_status_not_updated():
            self.update_job_status()
        self.update_output_status(Output.PROCESSING)

        try:
            self.start_transcoding()
            self.update_output_status(Output.COMPLETED)
        except Exception as error:
            self.store_exception(error)
            self.update_output_status(Output.ERROR)

    def is_job_status_not_updated(self):
        return self.job.status != Job.PROCESSING

    def update_job_status(self):
        self.job.status = Job.PROCESSING
        self.job.save()
        self.job.notify_webhook()

    def update_output_status(self, status):
        self.output.status = status
        self.output.save()

    def start_transcoding(self):
        ffmpeg_manager = Manager(self.output.settings, self.update_progress)
        ffmpeg_manager.run()

    def should_update_progress(self, percentage):
        return (percentage % 5) == 0 and self.output.progress != percentage

    def update_progress(self, percentage):
        if self.should_update_progress(percentage):
            self.output.progress = percentage
            self.output.save()
            self.job.update_progress()

    def store_exception(self, error):
        self.output.error_message = error
        self.output.save()


class ManifestGeneratorRunnable(CeleryRunnable):
    def do_run(self, *args, **kwargs):
        self.job = get_object_or_404(Job, id=self.job_id)
        media_details = self.get_media_details()
        content = self.generate_manifest_content(media_details)
        self.write_to_file(content)
        self.upload()
        self.update_job_status()

    def manifest_header(self):
        return "#EXTM3U\n#EXT-X-VERSION:3\n"

    def upload(self):
        path = f"{settings.TRANSCODED_VIDEOS_PATH}/{self.job.id}"
        output_storage = OutputFactory.create(self.job.output_url)
        output_storage.upload_directory(path)

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

    def generate_manifest_content(self, media_details):
        content = self.manifest_header()
        for media_detail in media_details:
            content += (
                f"#EXT-X-STREAM-INF:BANDWIDTH={media_detail['bandwidth']},"
                f"RESOLUTION={media_detail['resolution']}\n{media_detail['name']}.m3u8\n\n"
            )
        return content

    def write_to_file(self, content):
        manifest_local_path = f"{settings.TRANSCODED_VIDEOS_PATH}/{self.job.id}/video.m3u8"
        master_m3u8 = open(manifest_local_path, "wt")
        master_m3u8.write(content)
        master_m3u8.close()

    def update_job_status(self):
        self.job.status = Job.COMPLETED
        self.job.save()
        self.job.notify_webhook()
