from django.test import SimpleTestCase
from apps.nodes.controller import ControllerNode
from apps.nodes.base import ProcessStatus


class TestController(SimpleTestCase):
    @property
    def output_settings(self):
        return {
            "id": "1232",
            "input": "file://abc",
            "segmentLength": 10,
            "destination": "file:///abc",
            "file_name": "video.m3u8",
            "format": "HLS",
            "output": {
                "name": "360p",
                "url": "s3://bucket_url/institute/demo/videos/transcoded/bunny",
                "local_path": "/abc/1232/360p",
                "video": {"width": 360, "height": 640, "codec": "h264", "bitrate": 500000},
                "audio": {"codec": "aac", "bitrate": "48000"},
            },
        }

    def test_status_should_be_running_once_controller_is_started(self):
        controller = ControllerNode()
        controller.start(self.output_settings)

        self.assertEqual(ProcessStatus.Running, controller.check_status())
        controller.stop()

    def test_stop_should_stop_the_nodes_in_controller(self):
        controller = ControllerNode()
        controller.start(self.output_settings)
        controller.stop()

        self.assertEqual(ProcessStatus.Finished, controller.check_status())

    def test_process_should_get_completed_outside_context_manager(self):
        controller = ControllerNode()

        with controller.start(self.output_settings):
            self.assertEqual(ProcessStatus.Running, controller.check_status())

        self.assertEqual(ProcessStatus.Finished, controller.check_status())