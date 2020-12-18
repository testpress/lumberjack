# Generated by Django 3.1 on 2020-12-18 08:29

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("presets", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="jobtemplate",
            name="settings",
            field=models.JSONField(blank=True, null=True, verbose_name="Settings"),
        ),
        migrations.AlterField(
            model_name="outputpreset",
            name="job_template",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="output_presets",
                to="presets.jobtemplate",
            ),
        ),
    ]
