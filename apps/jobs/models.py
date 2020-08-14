from django.db import models

from apps.presets.models import OutputGroupPreset, AbstractOutputPreset

from model_utils.models import TimeStampedModel
from model_utils.fields import StatusField
from model_utils import Choices


class Job(TimeStampedModel):
    STATUS = Choices('not_started', 'queued', 'started', 'processing', 'completed', 'cancelled', 'error')

    job_template = models.ForeignKey("presets.JobTemplate", null=True, on_delete=models.SET_NULL)
    job_settings = models.JSONField("Job Settings", null=True)
    job_id = models.CharField("Job Id", unique=True, db_index=True, max_length=1024)
    celery_task_id = models.CharField("Celery Task Id", null=True, max_length=1024)
    progress = models.PositiveSmallIntegerField("Progress", default=0)
    status = StatusField()
    start = models.DateField("Start Time")
    end = models.DateField("End Time")
    output_group = models.ForeignKey("jobs.OutputGroup", null=True, on_delete=models.SET_NULL)
    input_url = models.CharField("Input URL", max_length=1024)


class OutputGroup(OutputGroupPreset):
    pass


class Output(AbstractOutputPreset):
    preset_group = models.ForeignKey(OutputGroup, null=True, on_delete=models.SET_NULL)
