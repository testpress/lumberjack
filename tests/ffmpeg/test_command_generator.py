import binascii

from django.test import TestCase, override_settings

from apps.ffmpeg.command_generator import CommandGenerator, HLSKeyInfoFile


class TestCommandGenerator(TestCase):
    @property
    def data(self):
        return {
            "id": "1232",
            "input": "s3://media.testpress.in/institute/demo/videos/raw_video.mp4",
            "segmentLength": 10,
            "destination": "s3://media.testpress.in/institute/demo/videos/",
            "format": "HLS",
            "encryption": {
                "key": "ecd0d06eaf884d8226c33928e87efa33",
                "url": "https://demo.testpress.in/api/v2.4/encryption_key/abcdef/"
            },
            "output": {
                "name": "360p",
                "url": "s3://media.testpress.in/institute/demo/videos/transcoded",
                "video": {
                    "width": 360,
                    "height": 640,
                    "codec": "h264",
                    "bitrate": 500000
                },
                "audio": {
                    "codec": "AAC",
                    "bitrate": "48000"
                }
            }
        }

    def setUp(self) -> None:
        self.command_generator = CommandGenerator(self.data)

    @override_settings(TRANSCODED_VIDEOS_PATH='tests/ffmpeg/data')
    def test_command_generator_should_convert_options_to_ffmpeg_command(self):
        ffmpeg_command = "ffmpeg -y -i - -c:a AAC -c:v h264 -preset fast -s 360x640 -b:v 500000 -format hls " \
                 "-hls_list_size 0 -hls_time 10 -hls_segment_filename tests/ffmpeg/data/1232/360p/video_%d.ts " \
                 "-hls_key_info_file tests/ffmpeg/data/1232/key/enc.keyinfo " \
                 "tests/ffmpeg/data/1232/video.m3u8"

        self.assertEqual(ffmpeg_command, self.command_generator.generate())

    def test_ffmpeg_binary_name_should_be_correct_in_command_generator(self):
        self.assertEqual("ffmpeg -y", self.command_generator.ffmpeg_binary)

    def test_input_argument_should_input_pipe(self):
        self.assertDictEqual({"i": "-"}, self.command_generator.input_argument)

    @override_settings(TRANSCODED_VIDEOS_PATH='tests/ffmpeg/data')
    def test_output_path_should_use_path_from_settings(self):
        output_path = "tests/ffmpeg/data/1232/video.m3u8"
        self.assertEqual(output_path, self.command_generator.output_path)


class TestHLSKeyInfoFile(TestCase):
    def setUp(self) -> None:
        self.key = "abcde12345"
        self.key_url = "https://google.com"
        self.local_path = "tests/ffmpeg/data"

    def test_string_representation_should_be_key_info_url(self):
        hls_key_info_file = HLSKeyInfoFile(self.key, self.key_url, self.local_path)
        self.assertEqual("tests/ffmpeg/data/enc.keyinfo", str(hls_key_info_file))

    def test_key_should_be_stored_in_file(self):
        hls_key_info_file = HLSKeyInfoFile(self.key, self.key_url, self.local_path+"/test_key")
        hls_key_info_file.store_key()

        with open(self.local_path+"/test_key/enc.key", "rb") as key:
            self.assertEqual(self.key, binascii.hexlify(key.read()).decode("utf8"))

