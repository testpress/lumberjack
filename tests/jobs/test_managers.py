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

    @mock.patch("apps.jobs.managers.chord")
    def test_start_should_start_background_task(self, mock_celery_chord):
        mock_celery_chord.return_value.apply_async.return_value.task_id = 12
        job = self.create_job(settings=self.job_settings)
        manager = VideoTranscodeManager(job)
        manager.start()

        mock_celery_chord.assert_called()
        self.assertEqual(12, job.background_task_id)

    @mock.patch("apps.jobs.managers.chord")
    def test_start_should_create_outputs_for_job(self, mock_celery_chord):
        mock_celery_chord.return_value.apply_async.return_value.task_id = 12
        job = self.create_job(settings=self.job_settings)
        manager = VideoTranscodeManager(job)
        manager.start()

        self.assertEqual(1, job.outputs.count())
        self.assertEqual(Output.objects.filter(job_id=job.id).first(), job.outputs.first())

    @mock.patch("apps.jobs.managers.AsyncResult")
    def test_stop_should_revoke_background_task(self, mock_async_result):
        job = self.create_job(settings=self.job_settings)
        manager = VideoTranscodeManager(job)
        manager.stop()

        self.assertEqual(Job.CANCELLED, job.status)

    def test_get_job_info_method_return_job_info(self):
        job = self.create_job(settings=self.job_settings)
        manager = VideoTranscodeManager(job)

        self.assertEqual(job.job_info, manager.get_job_info())
