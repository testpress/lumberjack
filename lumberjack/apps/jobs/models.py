import uuid
import os
import copy
import json

from django.db import models
from django.utils.translation import ugettext_lazy as _

from .mixins import JobNotifierMixin
from lumberjack.celery import app

from model_utils.models import TimeStampedModel, TimeFramedModel
from model_utils.fields import StatusField
from model_utils import Choices


class Job(TimeStampedModel, JobNotifierMixin):
    NOT_STARTED = "not_started"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ERROR = "error"

    STATUS = Choices(
        (NOT_STARTED, "Not Started"),
        (QUEUED, "Queued"),
        (PROCESSING, "Processing"),
        (COMPLETED, "Completed"),
        (CANCELLED, "Cancelled"),
        (ERROR, "Error"),
    )

    id = models.UUIDField("Job Id", primary_key=True, default=uuid.uuid4, editable=False, db_index=True)
    template = models.ForeignKey("presets.JobTemplate", null=True, on_delete=models.SET_NULL)
    settings = models.JSONField("Job Settings", null=True)
    background_task_id = models.UUIDField("Background Task Id", db_index=True, null=True, max_length=255)
    progress = models.PositiveSmallIntegerField("Progress", default=0)
    status = StatusField()
    input_url = models.CharField("Input URL", max_length=1024)
    output_url = models.CharField("Output URL", max_length=1024)
    webhook_url = models.URLField("Webhook URL", null=True)
    encryption_key = models.CharField("Encryption Key", max_length=1024, null=True)
    key_url = models.CharField("Encryption Key URL", max_length=1024, null=True)
    meta_data = models.JSONField("Meta Data", null=True)
    start_time = models.DateTimeField(_("start"), null=True, blank=True)
    end_time = models.DateTimeField(_("end"), null=True, blank=True)

    class Meta:
        ordering = ("-created",)

    def __str__(self):
        return f"JOB {self.id} - {self.get_status_display()}"

    def update_progress(self):
        progress_dict = self.outputs.aggregate(models.Avg("progress"))
        self.progress = progress_dict["progress__avg"]
        self.save(update_fields=["progress"])

    def create_outputs(self):
        job_settings = copy.deepcopy(self.settings)
        outputs = []
        for output_settings in job_settings.pop("outputs"):
            output_settings["url"] = self.settings["destination"] + "/" + output_settings["name"]
            job_settings["output"] = output_settings

            output = Output(
                name=output_settings["name"],
                video_encoder=output_settings["video"]["codec"],
                video_bitrate=output_settings["video"]["bitrate"],
                video_preset=output_settings["video"]["preset"],
                audio_encoder=output_settings["audio"]["codec"],
                audio_bitrate=output_settings["audio"]["bitrate"],
                width=output_settings["video"]["width"],
                height=output_settings["video"]["height"],
                settings=job_settings,
                job=self,
            )
            output.save()
            outputs.append(output)
        return outputs

    def populate_settings(self):
        if self.template is not None:
            settings = self.template.settings or {}
            settings["template"] = self.template.id.hex
        else:
            settings = self.settings or {}

        destination, file_name = os.path.split(self.output_url)
        settings.update(
            {"id": self.id.hex, "destination": destination, "file_name": file_name, "input": self.input_url}
        )

        if self.encryption_key:
            settings.update({"encryption": {"key": self.encryption_key, "url": self.key_url}})

        self.settings = settings

    def start(self, sync=False):
        self.status = Job.QUEUED
        self.save()

        queue = "transcoding"
        if self.meta_data and json.loads(self.meta_data).get("queue"):
            meta_data = json.loads(self.meta_data)
            queue = meta_data.get("queue", queue)

        for output in self.outputs.all():
            output.start_task(queue, sync)

    def stop(self):
        if self.status == Job.COMPLETED:
            return

        for output in self.outputs.all():
            output.stop_task()
        self.status = Job.CANCELLED
        self.save()

    def save(self, *args, **kwargs):
        self.populate_settings()
        super().save(*args, **kwargs)


class AbstractOutput(TimeStampedModel):
    VIDEO_ENCODERS = (("h264", "H244"), ("hevc", "HEVC"))

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField("Output Name", max_length=255)
    video_encoder = models.CharField("Video Encoder", max_length=100, default="h264", choices=VIDEO_ENCODERS)
    video_bitrate = models.PositiveIntegerField("Video Bitrate")
    video_preset = models.CharField("Video Preset", max_length=100, default="faster")
    audio_encoder = models.CharField("Audio Encoder", max_length=100, default="aac")
    audio_bitrate = models.PositiveIntegerField("Audio Bitrate", default=128000)
    width = models.PositiveSmallIntegerField("Video Width")
    height = models.PositiveSmallIntegerField("Video Height")

    class Meta:
        ordering = ("-created",)
        abstract = True

    def __str__(self):
        return self.name


class Output(AbstractOutput):
    NOT_STARTED = "not_started"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ERROR = "error"

    STATUS = Choices(
        (NOT_STARTED, "Not Started"),
        (QUEUED, "Queued"),
        (PROCESSING, "Processing"),
        (COMPLETED, "Completed"),
        (CANCELLED, "Cancelled"),
        (ERROR, "Error"),
    )

    job = models.ForeignKey(Job, null=True, on_delete=models.SET_NULL, related_name="outputs")
    status = StatusField()
    progress = models.PositiveSmallIntegerField("Progress", default=0)
    background_task_id = models.UUIDField("Background Task Id", db_index=True, null=True, max_length=255)
    settings = models.JSONField("Settings", null=True)
    error_message = models.TextField("Error Message", null=True, blank=True)
    start_time = models.DateTimeField(_("start"), null=True, blank=True)
    end_time = models.DateTimeField(_("end"), null=True, blank=True)

    @property
    def resolution(self):
        return f"{self.width}x{self.height}"

    def start_task(self, queue, sync=False):
        from .tasks import VideoTranscoderTask

        if sync:
            task = VideoTranscoderTask.apply(kwargs={"job_id": self.job.id, "output_id": self.id})
        else:
            task = VideoTranscoderTask.apply_async(kwargs={"job_id": self.job.id, "output_id": self.id}, queue=queue)
        self.background_task_id = task.task_id
        self.save()

    def stop_task(self):
        app.control.revoke(self.background_task_id, terminate=True, signal="SIGUSR1")

    def __str__(self):
        if self.status == self.PROCESSING:
            return f"{self.name} - {self.job_id} - {self.progress}% Transcoded"
        return f"{self.name} - {self.job_id} - {self.get_status_display()}"
