from django.test import SimpleTestCase

from apps.nodes.transcoder import TranscoderNode
from apps.nodes.base import ProcessStatus


class TestTranscoder(SimpleTestCase):
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
                "url": "s3://bucket_url/institute/demo/videos/transcoded/bunny",
                "local_path": "/abc/1232/360p",
                "video": {"width": 360, "height": 640, "codec": "h264", "bitrate": 500000},
                "audio": {"codec": "aac", "bitrate": "48000"},
            },
        }

    def test_process_status_should_be_running_on_starting_transcoder(self):
        transcoder = TranscoderNode(self.output_settings)
        transcoder.start()

        self.assertEqual(ProcessStatus.Running, transcoder.check_status())

    def test_event_observer_should_be_stopped_on_stopping_transcoder(self):
        transcoder = TranscoderNode(self.output_settings)
        transcoder.start()
        transcoder._process.terminate()
        transcoder.stop(ProcessStatus.Finished)

        self.assertFalse(transcoder.event_source.thread.is_alive())

    def test_observer_should_be_registered_if_progress_callback_is_passed(self):
        transcoder = TranscoderNode(self.output_settings, lambda x: x)
        transcoder.start()

        self.assertTrue(transcoder.event_source._observers.get("progress") is not None)
