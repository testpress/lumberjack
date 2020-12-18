import mock
import json

from django.test import TestCase

from tests.jobs.mixins import Mixin
from apps.jobs.managers import VideoTranscoder
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
        self.create_output(self.job)
        self.manager = VideoTranscoder(self.job)

    @mock.patch("apps.jobs.managers.VideoTranscoderTask")
    def test_start_should_start_background_task(self, mock_celery_group):
        mock_celery_group.apply_async().task_id = "4c1761d8-c0cd-4068-a997-ccab60592943"
        self.manager.start()

        mock_celery_group.apply_async.assert_called()
        self.assertEqual("4c1761d8-c0cd-4068-a997-ccab60592943", str(self.job.outputs.first().background_task_id))

    @mock.patch("apps.jobs.managers.VideoTranscoderTask")
    def test_start_should_create_outputs_for_job(self, mock_celery_group):
        mock_celery_group.apply_async().task_id = 12
        self.manager.start()

        self.assertEqual(2, self.job.outputs.count())
        self.assertEqual(Output.objects.filter(job_id=self.job.id).first(), self.job.outputs.first())

    @mock.patch("apps.jobs.managers.VideoTranscoderTask")
    def test_start_with_sync_should_should_run_synchronously(self, mock_celery_group):
        mock_celery_group.apply().task_id = 12
        self.manager.start(sync=True)

        self.assertEqual(2, self.job.outputs.count())
        self.assertEqual(Output.objects.filter(job_id=self.job.id).first(), self.job.outputs.first())

    @mock.patch("apps.jobs.managers.app.control")
    def test_stop_should_revoke_background_task(self, mock_celery_control):
        self.manager.stop()

        self.assertEqual(Job.CANCELLED, self.job.status)
        mock_celery_control.revoke.assert_called()

    @mock.patch("apps.jobs.managers.VideoTranscoderTask")
    @mock.patch("apps.jobs.managers.app.control")
    def test_restart_job_should_stop_running_task_and_start_again(self, mock_celery_control, mock_celery_group):
        mock_celery_group.apply_async().task_id = "4c1761d8-c0cd-4068-a997-ccab60592943"
        self.manager.restart()

        mock_celery_control.revoke.assert_called()
        mock_celery_group.apply_async.assert_called()
        self.assertEqual("4c1761d8-c0cd-4068-a997-ccab60592943", str(self.job.outputs.first().background_task_id))

    def test_outputs_should_run_in_specific_queue_if_provided_in_job_meta(self):
        self.job.meta_data = json.dumps({"queue": "priority"})
        self.job.save()
        self.create_output(job=self.job)
        tasks = self.manager.create_output_tasks(self.job.outputs.all())

        self.assertEqual("priority", tasks[0].options.get("queue"))

    def test_outputs_should_not_have_queue_if_not_provided_in_job_meta(self):
        self.job.meta_data = None
        self.job.save()
        self.create_output(job=self.job)
        tasks = self.manager.create_output_tasks(self.job.outputs.all())

        self.assertEqual(None, tasks[0].options.get("queue"))
