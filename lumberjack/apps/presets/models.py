import uuid

from django.db import models
from django.utils.text import slugify

from model_utils.models import TimeStampedModel

from apps.jobs.models import AbstractOutput


class JobTemplate(TimeStampedModel):
    PLAYLIST_TYPE = (("vod", "VOD"), ("live", "Live"))

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField("Name", max_length=255, unique=True)
    slug = models.SlugField("Slug", max_length=255, unique=True, blank=True, db_index=True)
    settings = models.JSONField("Settings", null=True, blank=True)
    destination = models.CharField("Destination", max_length=1024)
    segment_length = models.PositiveSmallIntegerField("HLS Segments length", blank=True, null=True, default=10)
    playlist_type = models.CharField(
        "VOD/Live",
        help_text="Applicable only for adaptive streaming",
        null=True,
        blank=True,
        choices=PLAYLIST_TYPE,
        max_length=100,
    )
    format = models.CharField("Output Format", max_length=255)

    class Meta:
        ordering = ("-created",)

    def __str__(self):
        return self.name

    def populate_settings(self):
        settings = {
            "name": self.name,
            "segmentLength": self.segment_length,
            "format": self.format,
            "playlist_type": self.playlist_type,
        }
        output_presets = []
        for output_preset in self.output_presets.all():
            output_presets.append(output_preset.settings)
        settings.update({"outputs": output_presets})
        self.settings = settings

    def save(self, *args, **kwargs):
        if not self.pk:
            self.slug = slugify(self.name)
        self.populate_settings()
        super(JobTemplate, self).save(*args, **kwargs)


class OutputPreset(AbstractOutput):
    job_template = models.ForeignKey(JobTemplate, null=True, on_delete=models.SET_NULL, related_name="output_presets")

    @property
    def settings(self):
        return {
            "name": self.name,
            "video": {
                "width": self.width,
                "height": self.height,
                "codec": self.video_encoder,
                "bitrate": self.video_bitrate,
                "preset": self.video_preset,
            },
            "audio": {"codec": self.audio_encoder, "bitrate": self.audio_bitrate},
        }
