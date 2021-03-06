# Generated by Django 3.1 on 2020-09-07 04:45

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import model_utils.fields
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="JobTemplate",
            fields=[
                (
                    "created",
                    model_utils.fields.AutoCreatedField(
                        default=django.utils.timezone.now, editable=False, verbose_name="created"
                    ),
                ),
                (
                    "modified",
                    model_utils.fields.AutoLastModifiedField(
                        default=django.utils.timezone.now, editable=False, verbose_name="modified"
                    ),
                ),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=255, unique=True, verbose_name="Name")),
                ("slug", models.SlugField(blank=True, max_length=255, unique=True, verbose_name="Slug")),
                ("settings", models.JSONField(null=True, verbose_name="Settings")),
                ("destination", models.CharField(max_length=1024, verbose_name="Destination")),
                (
                    "segment_length",
                    models.PositiveSmallIntegerField(
                        blank=True, default=10, null=True, verbose_name="HLS Segments length"
                    ),
                ),
                ("format", models.CharField(max_length=255, verbose_name="Output Format")),
            ],
            options={"ordering": ("-created",),},
        ),
        migrations.CreateModel(
            name="OutputPreset",
            fields=[
                (
                    "created",
                    model_utils.fields.AutoCreatedField(
                        default=django.utils.timezone.now, editable=False, verbose_name="created"
                    ),
                ),
                (
                    "modified",
                    model_utils.fields.AutoLastModifiedField(
                        default=django.utils.timezone.now, editable=False, verbose_name="modified"
                    ),
                ),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=255, verbose_name="Output Name")),
                (
                    "video_encoder",
                    models.CharField(
                        choices=[("h264", "H244"), ("hevc", "HEVC")],
                        default="h264",
                        max_length=100,
                        verbose_name="Video Encoder",
                    ),
                ),
                ("video_bitrate", models.PositiveIntegerField(verbose_name="Video Bitrate")),
                ("video_preset", models.CharField(default="faster", max_length=100, verbose_name="Video Preset")),
                ("audio_encoder", models.CharField(default="aac", max_length=100, verbose_name="Audio Encoder")),
                ("audio_bitrate", models.PositiveIntegerField(default=128000, verbose_name="Audio Bitrate")),
                ("width", models.PositiveSmallIntegerField(verbose_name="Video Width")),
                ("height", models.PositiveSmallIntegerField(verbose_name="Video Height")),
                (
                    "job_template",
                    models.ForeignKey(
                        null=True, on_delete=django.db.models.deletion.SET_NULL, to="presets.jobtemplate"
                    ),
                ),
            ],
            options={"ordering": ("-created",), "abstract": False,},
        ),
    ]
