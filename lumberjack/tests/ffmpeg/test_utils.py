from django.test import SimpleTestCase
from apps.ffmpeg.utils import ExtensionGenerator


class TestExtensionGenerator(SimpleTestCase):
    def test_mp4_should_be_returned_for_mp4_type(self):
        extension = ExtensionGenerator().get("MP4")

        self.assertEqual("mp4", extension)

    def test_m3u8_should_be_returned_for_hls(self):
        extension = ExtensionGenerator().get("HLS")

        self.assertEqual("m3u8", extension)

    def test_m3u8_should_be_returned_for_dash(self):
        extension = ExtensionGenerator().get("DASH")

        self.assertEqual("mpd", extension)
