import shutil
import os

from django.test import SimpleTestCase

from apps.nodes.packager import PackagerNode
from apps.nodes.base import ProcessStatus
from apps.ffmpeg.utils import mkdir


class TestPackager(SimpleTestCase):
    @property
    def output_settings(self):
        return {
            "id": "1232",
            "input": "file://abc",
            "segmentLength": 10,
            "destination": "file:///abc",
            "file_name": "video.m3u8",
            "format": "adaptive",
            "output": {
                "input": "tests/ffmpeg/data/videoplayback.mp4",
                "name": "360p",
                "url": "s3://bucket_url/institute/demo/videos/transcoded/bunny",
                "local_path": "/abc/1232/360p",
                "video": {"width": 360, "height": 640, "codec": "h264", "bitrate": 500000},
                "audio": {"codec": "aac", "bitrate": "48000"},
            },
        }

    def setUp(self):
        mkdir("tests/nodes/data/")

    def test_start_should_run_packager_in_a_thread(self):
        packager = PackagerNode(self.output_settings, "tests/nodes/data/")
        packager.start()

        self.assertEqual(ProcessStatus.Running, packager.check_status())

    def test_status_should_be_finished_on_completion(self):
        packager = PackagerNode(self.output_settings, "tests/nodes/data/")
        packager.start()
        packager._process.wait()

        self.assertEqual(ProcessStatus.Finished, packager.check_status())

    def test_both_mpd_and_m3u8_should_be_generated_for_adaptive_format(self):
        packager = PackagerNode(self.output_settings, "tests/nodes/data/")
        packager.start()
        packager._process.wait()

        self.assertTrue(os.path.isfile("tests/nodes/data/audio_init.mp4"))
        self.assertTrue(os.path.isfile("tests/nodes/data/video_360p_init.mp4"))
        self.assertTrue(os.path.isfile("tests/nodes/data/video.m3u8"))
        self.assertTrue(os.path.isfile("tests/nodes/data/video.mpd"))

    def test_m3u8_should_be_generated_for_hls_format(self):
        config = self.output_settings
        config["format"] = "hls"
        packager = PackagerNode(self.output_settings, "tests/nodes/data/")
        packager.start()
        packager._process.wait()

        self.assertTrue(os.path.isfile("tests/nodes/data/audio_init.mp4"))
        self.assertTrue(os.path.isfile("tests/nodes/data/video_360p_init.mp4"))
        self.assertTrue(os.path.isfile("tests/nodes/data/video.m3u8"))

    def test_mpd_should_be_generated_for_hls_format(self):
        config = self.output_settings
        config["format"] = "dash"
        packager = PackagerNode(config, "tests/nodes/data/")
        packager.start()
        packager._process.wait()

        self.assertTrue(os.path.isfile("tests/nodes/data/audio_init.mp4"))
        self.assertTrue(os.path.isfile("tests/nodes/data/video_360p_init.mp4"))
        self.assertTrue(os.path.isfile("tests/nodes/data/video.mpd"))

    def tearDown(self) -> None:
        shutil.rmtree("tests/nodes/data/")
