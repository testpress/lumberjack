import factory
from factory.django import DjangoModelFactory


class JobFactory(DjangoModelFactory):
    class Meta:
        model = "jobs.Job"

    input_url = "s3://bucket/key"
    output_url = "s3://bucket/output_key/video.m3u8"


class OutputFactory(DjangoModelFactory):
    class Meta:
        model = "jobs.Output"

    job = factory.SubFactory(JobFactory)
    video_bitrate = 1500000
    width = 1280
    height = 720
    name = "720p"
