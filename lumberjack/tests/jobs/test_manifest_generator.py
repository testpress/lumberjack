from django.test import TestCase

from tests.jobs.mixins import Mixin
from apps.jobs.manifest_generator import DashManifestGenerator, HLSManifestGeneratorForPackager


class TestDashManifestGenerator(TestCase, Mixin):
    def setUp(self):
        self.create_output(job=self.job, name="240p")
        self.job.output_url = "s3://bucket_url/tests/jobs/data/"
        self.job.output_cdn_url = ""
        self.job.save()

    def test_dash_manifest_generator_should_combine_multiple_manifest_and(self):
        manifest_generator = DashManifestGenerator(self.output.job)

        with open("tests/jobs/data/output.mpd", "r") as fp:
            self.assertEqual(fp.read(), manifest_generator.generate())


class TestHLSManifestGenerator(TestCase, Mixin):
    def setUp(self):
        self.create_output(job=self.job, name="240p")
        self.job.output_url = "s3://bucket_url/tests/jobs/data/"
        self.job.output_cdn_url = ""
        self.job.save()

    def test_dash_manifest_generator_should_combine_multiple_manifest_and(self):
        manifest_generator = HLSManifestGeneratorForPackager(self.output.job)

        with open("tests/jobs/data/output.m3u8", "r") as fp:
            self.assertEqual(fp.read(), manifest_generator.generate())
