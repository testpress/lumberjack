import json
import mock
import shutil

from django.test import TestCase, override_settings

from apps.jobs.tasks import VideoTranscoderRunnable, ManifestGeneratorRunnable
from apps.ffmpeg.utils import mkdir
from .mixins import Mixin


class TestVideoTranscoder(Mixin, TestCase):
    @property
    def output_settings(self):
        return {
            "id": "1232",
            "input": "file://abc",
            "segmentLength": 10,
            "destination": "file:///abc",
            "file_name": "video.m3u8",
            "format": "HLS",
            "encryption": {
                "key": "ecd0d06eaf884d8226c33928e87efa33",
                "url": "https://demo.testpress.in/api/v2.4/encryption_key/abcdef/",
            },
            "output": {
                "name": "360p",
                "url": "file://media.testpress.in/institute/demo/videos/transcoded/bunny",
                "local_path": "/abc/1232/360p",
                "video": {"width": 360, "height": 640, "codec": "h264", "bitrate": 500000},
                "audio": {"codec": "aac", "bitrate": "48000"},
            },
        }

    def setUp(self) -> None:
        self.output.settings = json.dumps(self.output_settings)
        self.output.save()

    @mock.patch("apps.jobs.tasks.Manager")
    def test_ffmanager_should_run_on_running_video_transcoder_task(self, mock_ffmpeg_manager):
        VideoTranscoderRunnable(job_id=self.output.job.id, output_id=self.output.id).do_run()

        self.assertTrue(mock_ffmpeg_manager.called)


class TestManifestGenerator(Mixin, TestCase):
    def setUp(self) -> None:
        self.manifest_generator = ManifestGeneratorRunnable(job_id=self.output.job.id)
        self.manifest_generator.job = self.job

    @property
    def media_details(self):
        return [
            {"bandwidth": self.output.video_bitrate, "resolution": self.output.resolution, "name": "720p/video.m3u8"}
        ]

    def test_media_details_should_return_list_of_media_detail(self):
        media_details = self.manifest_generator.get_media_details()

        self.assertDictEqual(self.media_details[0], media_details[0])

    def test_manifest_content_should_return_manifest_(self):
        manifest_content = self.manifest_generator.get_manifest_content(self.media_details)

        expected_manifest_content = (
            "#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-STREAM-INF:BANDWIDTH=1500000,"
            "RESOLUTION=1280x720\n720p/video.m3u8.m3u8\n\n"
        )
        self.assertEqual(expected_manifest_content, manifest_content)

    @override_settings(TRANSCODED_VIDEOS_PATH="tests/ffmpeg/data")
    def test_write_to_file_should_write_content_in_manifest_file(self):
        manifest_path = f"tests/ffmpeg/data/{self.job.id}"
        mkdir(manifest_path)
        self.manifest_generator.write_to_file("hello")

        with open(manifest_path + "/video.m3u8", "rb") as manifest:
            self.assertEqual("hello", manifest.read().decode("utf8"))

        shutil.rmtree(manifest_path)
