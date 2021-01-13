from django.test import TestCase

from tests.jobs.mixins import Mixin
from apps.jobs.manifest_generator import DashManifestGenerator, HLSManifestGeneratorForPackager
from mpegdash.parser import MPEGDASHParser
import mock
from smart_open import parse_uri


def mock_read_file(path, *args, **kwargs):
    file_path = parse_uri(path).key_id
    return open(file_path).read()


class TestDashManifestGenerator(TestCase, Mixin):
    def setUp(self):
        self.create_output(job=self.job, name="240p")
        self.job.output_url = "s3://bucket_url/tests/jobs/data/"
        self.job.save()

    @mock.patch("apps.jobs.manifest_generator.ManifestMerger.read_file", side_effect=mock_read_file)
    def test_dash_manifest_generator_should_combine_multiple_manifest_and(self, mock_open):
        manifest_generator = DashManifestGenerator(self.output.job)

        with open("tests/jobs/data/output.mpd", "r") as fp:
            expected_mpd = MPEGDASHParser().parse(fp.read())
            actual_mpd = MPEGDASHParser().parse(manifest_generator.merge())
            self.assertEqual(
                MPEGDASHParser.get_as_doc(expected_mpd).toxml(), MPEGDASHParser.get_as_doc(actual_mpd).toxml()
            )


class TestHLSManifestGenerator(TestCase, Mixin):
    def setUp(self):
        self.create_output(job=self.job, name="240p")
        self.job.output_url = "s3://bucket_url/tests/jobs/data/"
        self.job.save()

    @mock.patch("apps.jobs.manifest_generator.ManifestMerger.read_file", side_effect=mock_read_file)
    def test_dash_manifest_generator_should_combine_multiple_manifest_and(self, mock_read_file):
        manifest_generator = HLSManifestGeneratorForPackager(self.output.job)

        with open("tests/jobs/data/output.m3u8", "r") as fp:
            self.assertEqual(fp.read(), manifest_generator.merge())
