import mock

from django.test import TestCase
from django.core.files import File

from apps.jobs.process import FFMpegProcess


class FFMpegProcessTestCase(TestCase):
    @property
    def ffmpeg_command(self):
        return "ffmpeg -i - -c:a aac -ar 48000 -b:a 128k -c:v h264 -s 1280x720" \
               " -b:v 1500k -preset faster  -f hls -hls_list_size 0 -hls_time 6 video.m3u8"

    @property
    def file_mock(self):
        file_mock = mock.MagicMock(spec=File, name='FileMock')
        file_mock.name = 'test1.txt'
        file_mock.size = 1000
        return file_mock

    @property
    def process_mock(self):
        process = mock.Mock()
        attrs = {'communicate.return_value': ('output', 'success'), 'stdout.readline.return_value': ""}
        process.configure_mock(**attrs)
        process.poll.return_value = False
        return process

    @mock.patch('subprocess.Popen')
    def test_subprocess(self, mock_subprocess_popen):
        mock_subprocess_popen.return_value = self.process_mock
        process = FFMpegProcess(self.ffmpeg_command, mock.MagicMock, input=self.file_mock)
        process.run()

        self.assertTrue(isinstance(process, FFMpegProcess))
