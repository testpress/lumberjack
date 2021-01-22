import shutil
import os

from django.test import SimpleTestCase

from apps.executors.packager import ShakaPackager
from apps.executors.base import Status
from apps.ffmpeg.utils import mkdir
from apps.presets.models import JobTemplate


class TestPackager(SimpleTestCase):
    @property
    def output_settings(self):
        return {
            "id": "1232",
            "input": "file://abc",
            "segmentLength": 10,
            "destination": "file:///abc",
            "file_name": "video.m3u8",
            "format": JobTemplate.BOTH_HLS_AND_DASH,
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
        packager = ShakaPackager(self.output_settings, "tests/nodes/data/")
        packager.start()

        self.assertEqual(Status.Running, packager.check_status())

    def test_status_should_be_finished_on_completion(self):
        packager = ShakaPackager(self.output_settings, "tests/nodes/data/")
        packager.start()
        packager._process.wait()

        self.assertEqual(Status.Finished, packager.check_status())

    def test_both_mpd_and_m3u8_should_be_generated_for_adaptive_format(self):
        packager = ShakaPackager(self.output_settings, "tests/nodes/data/")
        packager.start()
        packager._process.wait()

        self.assertTrue(os.path.isfile("tests/nodes/data/audio_init.mp4"))
        self.assertTrue(os.path.isfile("tests/nodes/data/video_360p_init.mp4"))
        self.assertTrue(os.path.isfile("tests/nodes/data/video.m3u8"))
        self.assertTrue(os.path.isfile("tests/nodes/data/video.mpd"))

    def test_m3u8_should_be_generated_for_hls_format(self):
        config = self.output_settings
        config["format"] = "hls"
        packager = ShakaPackager(self.output_settings, "tests/nodes/data/")
        packager.start()
        packager._process.wait()

        self.assertTrue(os.path.isfile("tests/nodes/data/audio_init.mp4"))
        self.assertTrue(os.path.isfile("tests/nodes/data/video_360p_init.mp4"))
        self.assertTrue(os.path.isfile("tests/nodes/data/video.m3u8"))

    def test_mpd_should_be_generated_for_hls_format(self):
        config = self.output_settings
        config["format"] = "dash"
        packager = ShakaPackager(config, "tests/nodes/data/")
        packager.start()
        packager._process.wait()

        self.assertTrue(os.path.isfile("tests/nodes/data/audio_init.mp4"))
        self.assertTrue(os.path.isfile("tests/nodes/data/video_360p_init.mp4"))
        self.assertTrue(os.path.isfile("tests/nodes/data/video.mpd"))

    def test_packager_command_should_return_command_to_package_output(self):
        config = self.output_settings
        config["format"] = "dash"
        packager = ShakaPackager(config, "tests/nodes/data/")
        expected_args = [
            "packager",
            "in=tests/ffmpeg/data/videoplayback.mp4,stream=video,init_segment=tests/nodes/data//video_360p_init.mp4,segment_template=tests/nodes/data//video_360p_$Number$.mp4",
            "in=tests/ffmpeg/data/videoplayback.mp4,stream=audio,init_segment=tests/nodes/data//audio_init.mp4,segment_template=tests/nodes/data//audio_$Number$.mp4",
            "--segment_duration",
            "10",
            "--mpd_output",
            "tests/nodes/data/video.mpd",
        ]

        self.assertEqual(expected_args, packager.get_process_command())

    def test_packager_process_command_should_return_widevine_encryption_args_for_dash(self):
        config = self.output_settings
        config.update(
            {
                "format": "dash",
                "encryption": {
                    "content_id": "abcd",
                    "signer": "lumberjack",
                    "aes_signing_key": "abcdef",
                    "aes_signing_iv": "fedcba",
                    "key_server_url": "https://google.com",
                },
            }
        )
        packager = ShakaPackager(config, "tests/nodes/data/")
        expected_args = [
            "packager",
            "in=tests/ffmpeg/data/videoplayback.mp4,stream=video,init_segment=tests/nodes/data//video_360p_init.mp4,segment_template=tests/nodes/data//video_360p_$Number$.mp4",
            "in=tests/ffmpeg/data/videoplayback.mp4,stream=audio,init_segment=tests/nodes/data//audio_init.mp4,segment_template=tests/nodes/data//audio_$Number$.mp4",
            "--segment_duration",
            "10",
            "--mpd_output",
            "tests/nodes/data/video.mpd",
            "--enable_widevine_encryption",
            "--key_server_url",
            "https://google.com",
            "--content_id",
            "abcd",
            "--signer",
            "lumberjack",
            "--aes_signing_key",
            "abcdef",
            "--aes_signing_iv",
            "fedcba",
        ]

        self.assertEqual(expected_args, packager.get_process_command())

    def test_packager_process_command_should_return_fairplay_encryption_args_for_hls(self):
        config = self.output_settings
        config.update(
            {
                "format": "hls",
                "encryption": {"content_id": "abcd", "key": "wfwefwe", "iv": "fedcba", "uri": "https://google.com"},
            }
        )
        packager = ShakaPackager(config, "tests/nodes/data/")
        expected_args = [
            "packager",
            "in=tests/ffmpeg/data/videoplayback.mp4,stream=video,init_segment=tests/nodes/data//video_360p_init.mp4,segment_template=tests/nodes/data//video_360p_$Number$.mp4",
            "in=tests/ffmpeg/data/videoplayback.mp4,stream=audio,init_segment=tests/nodes/data//audio_init.mp4,segment_template=tests/nodes/data//audio_$Number$.mp4",
            "--segment_duration",
            "10",
            "--hls_playlist_type",
            "VOD",
            "--hls_master_playlist_output",
            "tests/nodes/data/video.m3u8",
            "--enable_raw_key_encryption",
            "--keys",
            "label=:key=wfwefwe",
            "--protection_systems",
            "Fairplay",
            "--iv",
            "fedcba",
            "--hls_key_uri",
            "https://google.com",
        ]

        self.assertEqual(expected_args, packager.get_process_command())

    def tearDown(self) -> None:
        shutil.rmtree("tests/nodes/data/")
