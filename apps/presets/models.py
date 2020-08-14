from django.db import models
from django.utils.text import slugify

from model_utils.models import TimeStampedModel


class JobTemplate(TimeStampedModel):
    slug = models.SlugField("Slug", max_length=255, unique=True, blank=True)
    name = models.CharField("Name", max_length=255)
    description = models.TextField("Description", null=True)
    output_group = models.ForeignKey("presets.OutputGroupPreset", null=True, on_delete=models.SET_NULL)
    settings = models.JSONField("Settings", null=True)

    def save(self, *args, **kwargs):
        if not self.pk:
            self.slug = slugify(self.name)
        super(JobTemplate, self).save(*args, **kwargs)


class OutputGroupPreset(TimeStampedModel):
    name = models.CharField("Output Group Name", max_length=255)
    destination = models.CharField("Destination", max_length=1024)
    segment_length = models.PositiveSmallIntegerField("HLS Segments length", blank=True, null=True)
    directory_name = models.CharField("Directory Name", max_length=255)
    encryption_method = models.CharField("Encryption Method", max_length=100, null=True)
    encryption_key = models.CharField("Encrytpion Key", max_length=1024, null=True)
    key_url = models.CharField("Encryption Key URL", max_length=1024, null=True)
    output_settings = models.JSONField("Output Settings", null=True)

    class Meta:
        ordering = ("-created",)

    def __str__(self):
        return self.name


class AbstractOutputPreset(TimeStampedModel):
    name = models.CharField("Output Name", max_length=255)
    video_encoder = models.CharField("Video Encoder", max_length=100, default="h264")
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
    preset_group = models.ForeignKey(OutputGroupPreset, null=True, on_delete=models.SET_NULL)
