import time
import os

from celery.exceptions import SoftTimeLimitExceeded

from django.shortcuts import get_object_or_404
from django.utils.timezone import now
from django.db import transaction

from apps.ffmpeg.outputs import OutputFileFactory
from apps.jobs.controller import LumberjackController
from apps.executors.base import Status
from apps.jobs.models import Job, Output
from apps.ffmpeg.utils import generate_file_name_from_format


class LumberjackRunnable(object):
    REQUIRED_ARGUMENTS = []
    OPTIONAL_ARGUMENTS = []

    def __init__(self, *args, **kwargs):
        if self.REQUIRED_ARGUMENTS:
            for arg in self.REQUIRED_ARGUMENTS:
                if arg not in kwargs:
                    raise LumberjackRunnableException("Relation %s is missing" % arg)

        self.__dict__.update(kwargs)

        for arg in self.OPTIONAL_ARGUMENTS:
            if arg not in kwargs:
                self.__dict__[arg] = None

    def do_run(self, *args, **kwargs):
        raise NotImplementedError("do_run method not implemented")

    def run(self, *args, **kwargs):
        self.do_run(*args, **kwargs)


class LumberjackRunnableException(Exception):
    def __init__(self, message, cause=None):
        self.cause = cause
        self.message = message
        super(LumberjackRunnableException, self).__init__(message, cause)


class VideoTranscoderRunnable(LumberjackRunnable):
    def do_run(self, *args, **kwargs):
        self.initialize()
        controller = LumberjackController()

        with controller.start(self.output.settings, self.update_progress):
            try:
                while True:
                    status = controller.check_status()
                    if status == Status.Finished:
                        self.update_output_as_completed()
                        break
                    elif status == Status.Errored:
                        self.handle_ffmpeg_exception(None)
                        break
                    time.sleep(1)
            except RuntimeError as error:
                self.handle_ffmpeg_exception(error)
                controller.stop()
            except SoftTimeLimitExceeded:
                self.update_output_as_cancelled()
                controller.stop()

        with transaction.atomic():
            if self.is_transcoding_completed():
                self.complete_job()
                self.notify_webhook()
                self.generate_manifest()

    def handle_ffmpeg_exception(self, error):
        self.save_exception(error)
        self.update_output_as_error()
        self.stop_job()
        if not self.is_job_status_error():
            self.update_job_as_error_and_notify()

    def initialize(self):
        self.job = Job.objects.get(id=self.job_id)
        self.output = Output.objects.get(id=self.output_id)

        if self.job.status != Job.PROCESSING:
            self.job.status = Job.PROCESSING
            self.job.start_time = now()
            self.job.save()
            self.job.notify_webhook()
        self.update_output_as_processing()

    def is_transcoding_completed(self):
        return not self.job.outputs.exclude(status=Output.COMPLETED).exists()

    def complete_job(self):
        job = Job.objects.select_for_update().get(id=self.job.id)
        if job.status is not Job.COMPLETED:
            job.status = Job.COMPLETED
            job.end_time = now()
            job.save(update_fields=["status", "end_time"])

    def notify_webhook(self):
        self.job.refresh_from_db()
        self.job.notify_webhook()

    def is_multiple_of_five(self, percentage):
        return (percentage % 5) == 0 and self.output.progress != percentage

    def generate_manifest(self):
        ManifestGeneratorRunnable(job_id=self.job.id).run()

    def update_progress(self, percentage):
        if self.is_multiple_of_five(percentage):
            self.output.progress = percentage
            self.output.save()
            self.job.update_progress()

    def save_exception(self, error):
        self.output.error_message = error
        self.output.save()

    def update_output_as_cancelled(self):
        self.output.status = Output.CANCELLED
        self.output.save()

    def update_output_as_processing(self):
        self.output.status = Output.PROCESSING
        self.output.start_time = now()
        self.output.save()

    def update_output_as_completed(self):
        self.output.status = Output.COMPLETED
        self.output.end_time = now()
        self.output.save()

    def update_output_as_error(self):
        self.output.status = Output.ERROR
        self.output.end_time = now()
        self.output.save()

    def stop_job(self):
        for output in self.job.outputs.all():
            if output.id != self.output.id:  # Skip killing current task as it is going to be stopped anyway.
                output.stop_task()

    def is_job_status_error(self):
        return Job.objects.get(id=self.job.id).status == Job.ERROR

    def update_job_as_error_and_notify(self):
        self.job.status = Job.ERROR
        self.job.save()
        self.job.notify_webhook()


class ManifestGeneratorRunnable(LumberjackRunnable):
    def do_run(self, *args, **kwargs):
        self.initialize()
        self.generate_manifest_content()
        self.upload()

    def initialize(self):
        self.job = get_object_or_404(Job, id=self.job_id)
        self.manifest_content = ""

    def manifest_header(self):
        return "#EXTM3U\n#EXT-X-VERSION:3\n"

    def upload(self):
        destination, file_name = os.path.split(self.job.output_url)
        if not file_name:
            file_name = generate_file_name_from_format(self.job.settings.get("format"))

        storage = OutputFileFactory.create(destination + "/" + file_name)
        storage.save_text(self.manifest_content)

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
