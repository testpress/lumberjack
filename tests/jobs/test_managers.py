import mock

from django.test import TestCase

from tests.jobs.mixins import Mixin
from apps.jobs.managers import VideoTranscodeManager
from apps.jobs.models import Output, Job


class TestVideoTranscodeManager(TestCase, Mixin):
    @property
    def job_settings(self):
        return {
            "id": "37446775ea3d45f7a46685c729707ef0",
            "name": "Template1",
            "input": "s3://abc/demo/bbb_sunflower_1080p_60fps_normal.mp4",
            "format": "HLS",
            "outputs": [
                {
                    "name": "360p",
                    "audio": {"codec": "aac", "bitrate": 128000},
                    "video": {"codec": "h264", "width": 640, "height": 360, "preset": "faster", "bitrate": 1500000},
                }
            ],
            "template": "fcdf3b6457dd4a7cb496f4bd3e27de4d",
            "file_name": "video.m3u8",
            "destination": "s3://abc/demo/lumberjack/test1",
            "segmentLength": 10,
        }

    def setUp(self) -> None:
        self.job = self.create_job(settings=self.job_settings)
        self.manager = VideoTranscodeManager(self.job)

    @mock.patch("apps.jobs.managers.chord")
    def test_start_should_start_background_task(self, mock_celery_chord):
        mock_celery_chord.return_value.return_value.task_id = 12
        self.manager.start()

        mock_celery_chord.assert_called()
        self.assertEqual(12, self.job.background_task_id)

    @mock.patch("apps.jobs.managers.chord")
    def test_start_should_create_outputs_for_job(self, mock_celery_chord):
        mock_celery_chord.return_value.return_value.task_id = 12
        self.manager.start()

        self.assertEqual(1, self.job.outputs.count())
        self.assertEqual(Output.objects.filter(job_id=self.job.id).first(), self.job.outputs.first())

    @mock.patch("apps.jobs.managers.AsyncResult")
    def test_stop_should_revoke_background_task(self, mock_async_result):
        self.manager.stop()

        self.assertEqual(Job.CANCELLED, self.job.status)

    def test_get_job_info_method_return_job_info(self):
        self.assertEqual(self.job.job_info, self.manager.get_job_info())
