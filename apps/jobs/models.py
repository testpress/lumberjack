import uuid

from django.db import models

from apps.presets.models import AbstractOutputPreset

from model_utils.models import TimeStampedModel, TimeFramedModel
from model_utils.fields import StatusField
from model_utils import Choices


class Job(TimeStampedModel, TimeFramedModel):
    STATUS = Choices('not_started', 'queued', 'started', 'processing', 'completed', 'cancelled', 'error')

    job_template = models.ForeignKey("presets.JobTemplate", null=True, on_delete=models.SET_NULL)
    job_settings = models.JSONField("Job Settings", null=True)
    job_id = models.UUIDField("Job Id", primary_key=True, default=uuid.uuid4, editable=False, db_index=True)
    background_task_id = models.UUIDField(
        "Background Task Id", default=uuid.uuid4, db_index=True, null=True, max_length=255
    )
    progress = models.PositiveSmallIntegerField("Progress", default=0)
    status = StatusField()
    input_url = models.CharField("Input URL", max_length=1024)


class Output(AbstractOutputPreset):
    STATUS = Choices('not_started', 'queued', 'started', 'processing', 'completed', 'cancelled', 'error')

    job = models.ForeignKey(Job, null=True, on_delete=models.SET_NULL)
    status = StatusField()
    progress = models.PositiveSmallIntegerField("Progress", default=0)
    background_task_id = models.UUIDField(
        "Background Task Id", default=uuid.uuid4, db_index=True, null=True, max_length=255
    )
