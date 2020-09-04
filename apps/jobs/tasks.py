import json

from celery import Task
from django.conf import settings
from django.shortcuts import get_object_or_404

from apps.ffmpeg.main import Manager
from apps.ffmpeg.outputs import OutputFactory
from apps.jobs.models import Job, Output
from lumberjack.celery import app


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


class CeleryTask(Task):
    runnable = None

    def run(self, *args, **kwargs):
        self.runnable(*args, **kwargs).run()


class VideoTranscoderRunnable(CeleryRunnable):
    def do_run(self, *args, **kwargs):
        self.job = Job.objects.get(id=self.job_id)
        self.output = Output.objects.get(id=self.output_id)
        self.update_status(Output.PROCESSING)

        try:
            self.start_transcoding()
            self.update_status(Output.COMPLETED)
        except Exception as error:
            self.store_exception(error)
            self.update_status(Output.ERROR)

    def update_status(self, status):
        self.output.status = status
        self.output.save()

    def start_transcoding(self):
        ffmpeg_manager = Manager(json.loads(self.output.settings), self.update_progress)
        ffmpeg_manager.run()

    def update_progress(self, percentage):
        if (percentage % 5) == 0 and self.output.progress != percentage:
            self.output.progress = percentage
            self.output.save()

    def store_exception(self, error):
        self.output.error_message = error
        self.output.save()


class VideoTranscoder(CeleryTask):
    runnable = VideoTranscoderRunnable


VideoTranscoder = app.register_task(VideoTranscoder())


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


class ManifestGenerator(CeleryTask):
    runnable = ManifestGeneratorRunnable


ManifestGenerator = app.register_task(ManifestGenerator())
