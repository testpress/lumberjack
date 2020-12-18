from datetime import timedelta

import factory
from factory.django import DjangoModelFactory

from django.utils.timezone import now


class JobFactory(DjangoModelFactory):
    class Meta:
        model = "jobs.Job"

    input_url = "s3://bucket/key"
    output_url = "s3://bucket/output_key/video.m3u8"
    start_time = now()
    end_time = now() + timedelta(days=1)


class OutputFactory(DjangoModelFactory):
    class Meta:
        model = "jobs.Output"

    job = factory.SubFactory(JobFactory)
    video_bitrate = 1500000
    width = 1280
    height = 720
    name = "720p"


class JobTemplateFactory(DjangoModelFactory):
    class Meta:
        model = "presets.JobTemplate"

    segment_length = 10
    name = "Job Template"
