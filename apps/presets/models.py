import uuid

from django.db import models
from django.utils.text import slugify

from model_utils.models import TimeStampedModel


class JobTemplate(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField("Name", max_length=255, unique=True)
    slug = models.SlugField("Slug", max_length=255, unique=True, blank=True, db_index=True)
    settings = models.JSONField("Settings", null=True)
    destination = models.CharField("Destination", max_length=1024)
    segment_length = models.PositiveSmallIntegerField("HLS Segments length", blank=True, null=True, default=10)
    format = models.CharField("Output Format", max_length=255)

    class Meta:
        ordering = ("-created",)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.pk:
            self.slug = slugify(self.name)
        super(JobTemplate, self).save(*args, **kwargs)


class AbstractOutputPreset(TimeStampedModel):
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


class OutputPreset(AbstractOutputPreset):
    job_template = models.ForeignKey(JobTemplate, null=True, on_delete=models.SET_NULL, related_name="output_presets")
