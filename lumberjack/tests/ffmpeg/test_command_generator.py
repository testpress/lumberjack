import binascii
import shutil
import mock
from collections import OrderedDict

from django.test import SimpleTestCase, override_settings

from apps.ffmpeg.command_generator import CommandGenerator, HLSKeyInfoFile


class TestCommandGenerator(SimpleTestCase):
    @property
    def data(self):
        return {
            "id": "1232",
            "input": "https://domain.com/path/videos/raw_video.mp4",
            "segmentLength": 10,
            "destination": "s3://media.testpress.in/institute/demo/videos/",
            "format": "HLS",
            "file_name": "video.m3u8",
            "encryption": {
                "key": "ecd0d06eaf884d8226c33928e87efa33",
                "url": "https://demo.testpress.in/api/v2.4/encryption_key/abcdef/",
            },
            "output": {
                "name": "360p",
                "url": "s3://media.testpress.in/institute/demo/videos/transcoded",
                "video": {"width": 360, "height": 640, "codec": "h264", "bitrate": 500000},
                "audio": {"codec": "aac", "bitrate": "48000"},
            },
        }

    def setUp(self) -> None:
        self.command_generator = CommandGenerator(self.data)

    @override_settings(TRANSCODED_VIDEOS_PATH="tests/ffmpeg/data")
    def test_command_generator_should_convert_options_to_ffmpeg_command(self):
        ffmpeg_command = (
            "ffmpeg -hide_banner -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 300 "
            "-i https://domain.com/path/videos/raw_video.mp4"
            " -c:a aac -c:v h264 -preset fast -s 360x640 -b:v 500000 -format hls "
            "-hls_list_size 0 -hls_time 10 -hls_segment_filename tests/ffmpeg/data/1232/360p/video_%d.ts "
            "-hls_key_info_file tests/ffmpeg/data/1232/key/enc.keyinfo -max_muxing_queue_size 9999 "
            "tests/ffmpeg/data/1232/360p/video.m3u8"
        )

        self.assertEqual(ffmpeg_command, self.command_generator.generate())

    def test_ffmpeg_binary_name_should_be_correct_in_command_generator(self):
        self.assertEqual("ffmpeg -hide_banner", self.command_generator.ffmpeg_binary)

    def test_input_argument_should_return_input_url(self):
        input_args = OrderedDict(
            [
                ("reconnect", 1),
                ("reconnect_streamed", 1),
                ("reconnect_delay_max", 300),
                ("i", "https://domain.com/path/videos/raw_video.mp4"),
            ]
        )
        self.assertDictEqual(input_args, self.command_generator.input_argument)

    @mock.patch("apps.ffmpeg.inputs.boto3.Session.client")
    def test_input_argument_should_be_signed_url_for_s3(self, mock_boto_client):
        data = self.data
        data["input"] = "s3://bucket/input.mp4"
        mock_boto_client.return_value.generate_presigned_url.return_value = "hello"
        command_generator = CommandGenerator(data)

        input_args = OrderedDict([("i", "hello")])
        self.assertDictEqual(input_args, command_generator.input_argument)

    @override_settings(TRANSCODED_VIDEOS_PATH="tests/ffmpeg/data")
    def test_output_path_should_use_path_from_settings(self):
        output_path = "tests/ffmpeg/data/1232/360p/video.m3u8"
        self.assertEqual(output_path, self.command_generator.output_path)


class TestHLSKeyInfoFile(SimpleTestCase):
    def setUp(self) -> None:
        self.key = "abcde12345"
        self.key_url = "https://google.com"
        self.local_path = "tests/ffmpeg/data/1232"

    def test_string_representation_should_be_key_info_url(self):
        hls_key_info_file = HLSKeyInfoFile(self.key, self.key_url, self.local_path)
        self.assertEqual("tests/ffmpeg/data/1232/enc.keyinfo", str(hls_key_info_file))

    def test_key_should_be_stored_in_file(self):
        hls_key_info_file = HLSKeyInfoFile(self.key, self.key_url, self.local_path + "/test_key")
        hls_key_info_file.save_key()

        with open(self.local_path + "/test_key/enc.key", "rb") as key:
            self.assertEqual(self.key, binascii.hexlify(key.read()).decode("utf8"))

    def tearDown(self) -> None:
        shutil.rmtree(self.local_path)
