import shutil
import subprocess
from os import path

from django.test import SimpleTestCase, override_settings

from apps.ffmpeg.main import Executor


class TestExecutor(SimpleTestCase):
    @property
    def data(self):
        return {
            "id": "1232",
            "input": "tests/ffmpeg/data/video.mp4",
            "segmentLength": 1,
            "destination": "tests/ffmpeg/output/",
            "file_name": "video.m3u8",
            "format": "HLS",
            "encryption": {
                "key": "ecd0d06eaf884d8226c33928e87efa33",
                "url": "https://demo.testpress.in/api/v2.4/encryption_key/abcdef/",
            },
            "output": {
                "name": "360p",
                "url": "/institute/demo/videos/transcoded",
                "local_path": "tests/ffmpeg/data/test",
                "video": {"width": 360, "height": 640, "codec": "h264", "bitrate": 500000},
                "audio": {"codec": "aac", "bitrate": "48000"},
            },
        }

    @override_settings(TRANSCODED_VIDEOS_PATH="tests/ffmpeg/data")
    def test_process_should_return_subprocess(self):
        executor = Executor(self.data)

        self.assertTrue(isinstance(executor.process, subprocess.Popen))

    @override_settings(TRANSCODED_VIDEOS_PATH="tests/ffmpeg/data/test")
    def test_executor_should_store_transcoded_files_in_local_directory(self):
        executor = Executor(self.data)
        executor.run()

        self.assertTrue(path.exists("tests/ffmpeg/data/test/1232/video.m3u8"))
        self.assertTrue(path.exists("tests/ffmpeg/data/test/1232/360p/video_0.ts"))

    @override_settings(TRANSCODED_VIDEOS_PATH="tests/ffmpeg/data/test")
    def test_exception_should_be_raised_for_corrupt_file(self):
        data = self.data
        data["input"] = "tests/ffmpeg/data/corrupt_video.mp4"
        executor = Executor(self.data)

        self.assertRaises(Exception, executor.run())

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree("tests/ffmpeg/data/test")
        shutil.rmtree("tests/ffmpeg/data/1232")
