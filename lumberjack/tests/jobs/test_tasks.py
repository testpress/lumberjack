import json
import mock
import responses
from requests.exceptions import ConnectionError
from moto import mock_s3
import boto3
from smart_open import parse_uri
from celery.exceptions import SoftTimeLimitExceeded

from django.test import TestCase
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder

from apps.jobs.runnables import VideoTranscoderRunnable, ManifestGeneratorRunnable
from apps.jobs.tasks import PostDataToWebhookTask
from apps.jobs.models import Job, Output
from apps.ffmpeg.main import FFMpegException
from .mixins import Mixin


class TestVideoTranscoder(Mixin, TestCase):
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
                "url": "file://media.testpress.in/institute/demo/videos/transcoded/bunny",
                "local_path": "/abc/1232/360p",
                "video": {"width": 360, "height": 640, "codec": "h264", "bitrate": 500000},
                "audio": {"codec": "aac", "bitrate": "48000"},
            },
        }

    def setUp(self) -> None:
        self.output.settings = json.dumps(self.output_settings)
        self.output.save()
        self.prepare_video_transcoder()

    def prepare_video_transcoder(self):
        self.video_transcoder = VideoTranscoderRunnable(
            job_id=self.output.job.id, output_id=self.output.id, task_id=13
        )
        self.video_transcoder.output = self.output
        self.video_transcoder.job = self.output.job

    @mock.patch("apps.jobs.runnables.Manager")
    def test_runnable_should_run_ffmpeg_manager(self, mock_ffmpeg_manager):
        self.video_transcoder.do_run()

        self.assertTrue(mock_ffmpeg_manager.called)

    def test_update_progress_should_update_progress_of_output_and_job(self):
        self.video_transcoder.update_progress(20)

        self.assertEqual(self.output.progress, 20)
        self.assertEqual(self.job.progress, 20)

    @mock.patch("apps.jobs.runnables.Manager", **{"return_value.run.side_effect": FFMpegException()})
    @mock.patch("apps.jobs.managers.app.GroupResult")
    def test_task_should_be_stopped_in_case_of_exception(self, mock_group_result, mock_ffmpeg_manager):
        task_mock = mock.MagicMock()
        mock_group_result.restore.return_value = [task_mock]
        self.video_transcoder.do_run()

        task_mock.revoke.assert_called_with(terminate=True, signal="SIGUSR1")
        self.assertEqual(self.video_transcoder.job.status, Job.ERROR)

    @mock.patch("apps.jobs.runnables.Manager", **{"return_value.run.side_effect": SoftTimeLimitExceeded()})
    @mock.patch("apps.jobs.managers.app.GroupResult")
    def test_task_should_stop_ffmpeg_process_in_case_of_soft_time_limit_exception(
        self, mock_group_result, mock_ffmpeg_manager
    ):
        task_mock = mock.MagicMock()
        mock_group_result.restore.return_value = [task_mock]
        self.video_transcoder.do_run()

        self.assertEqual(self.video_transcoder.output.status, Output.CANCELLED)
        mock_ffmpeg_manager().stop.assert_called()

    @mock.patch("apps.jobs.runnables.ManifestGeneratorRunnable")
    @mock.patch("apps.jobs.runnables.Manager")
    def test_manifest_generator_should_be_called_on_transcoding_completion(
        self, mock_ffmpeg_manager, mock_manifest_generator
    ):
        self.video_transcoder.do_run()

        mock_manifest_generator.assert_called()


class TestManifestGenerator(Mixin, TestCase):
    def setUp(self) -> None:
        self.output.status = Output.COMPLETED
        self.output.save()
        self.manifest_generator = ManifestGeneratorRunnable(job_id=self.output.job.id)
        self.manifest_generator.initialize()

    @property
    def media_details(self):
        return [
            {"bandwidth": self.output.video_bitrate, "resolution": self.output.resolution, "name": "720p/video.m3u8"}
        ]

    def test_media_details_should_return_list_of_media_detail(self):
        media_details = self.manifest_generator.get_media_details()

        self.assertDictEqual(self.media_details[0], media_details[0])

    def test_generate_manifest_content_should_generate_hls_content(self):
        self.manifest_generator.generate_manifest_content()

        expected_manifest_content = (
            "#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-STREAM-INF:BANDWIDTH=1500000,"
            "RESOLUTION=1280x720\n720p/video.m3u8\n\n"
        )
        self.assertEqual(expected_manifest_content, self.manifest_generator.manifest_content)

    def update_job_status_should_update_job_as_completed(self):
        self.manifest_generator.complete_job()

        self.assertEqual(Job.COMPLETED, self.job.status)

    def test_upload(self):
        self.start_s3_mock()
        self.manifest_generator.generate_manifest_content()
        self.manifest_generator.upload()

        uploaded_content = self.get_file_from_s3(self.job.output_url).read().decode("utf-8")
        self.assertEqual(uploaded_content, self.manifest_generator.manifest_content)

    def start_s3_mock(self):
        s3_mock = mock_s3()
        s3_mock.start()
        conn = boto3.resource("s3", region_name=settings.AWS_S3_REGION_CODE)
        conn.create_bucket(Bucket="bucket")

    def get_file_from_s3(self, url):
        s3_path = parse_uri(url)
        conn = boto3.resource("s3", region_name=settings.AWS_S3_REGION_CODE)
        return conn.Object(s3_path.bucket_id, s3_path.key_id).get()["Body"]

    def test_manifest_should_be_generated_only_for_completed_outputs(self):
        self.create_output(job=self.job, status=Output.PROCESSING)
        self.create_output(job=self.job, status=Output.COMPLETED, name="240p")
        self.manifest_generator.generate_manifest_content()

        expected_manifest_content = "#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-STREAM-INF:BANDWIDTH=1500000,RESOLUTION=1280x720\n720p/video.m3u8\n\n#EXT-X-STREAM-INF:BANDWIDTH=1500000,RESOLUTION=1280x720\n240p/video.m3u8\n\n"
        self.assertEqual(expected_manifest_content, self.manifest_generator.manifest_content)


class TestPostDataToWebhook(Mixin, TestCase):
    @property
    def url(self):
        return "http://domain.com/webhook/"

    @mock.patch("apps.jobs.tasks.requests")
    def test_data_should_be_posted_to_webhook(self, requests_mock):
        PostDataToWebhookTask.run(data=self.job.job_info, url=self.url)

        requests_mock.post.assert_called_with(
            "http://domain.com/webhook/",
            data=json.dumps(self.job.job_info, cls=DjangoJSONEncoder),
            headers={"Content-Type": "application/json"},
        )

    @responses.activate
    @mock.patch("apps.jobs.tasks.PostDataToWebhookTask.retry")
    def test_error(self, retry_mock):
        responses.add(responses.POST, self.url, body=ConnectionError("Gateway Error"))
        PostDataToWebhookTask.run(data=self.job.job_info, url=self.url)

        retry_mock.assert_called()
