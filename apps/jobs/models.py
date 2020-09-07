import uuid

from django.db import models

from apps.presets.models import AbstractOutputPreset

from model_utils.models import TimeStampedModel, TimeFramedModel
from model_utils.fields import StatusField
from model_utils import Choices


class Job(TimeStampedModel, TimeFramedModel):
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

    class Meta:
        ordering = ("-created",)

    def __str__(self):
        return f"JOB {self.id} - {self.get_status_display()}"


class Output(AbstractOutputPreset):
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
