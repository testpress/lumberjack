import json
import mock
import uuid

from django.test import RequestFactory, TestCase

from apps.api.v1.jobs.views import CreateJobView, job_info_view, cancel_job_view, restart_job_view
from apps.jobs.models import Job
from tests.jobs.mixins import Mixin as JobMixin


class Mixin:
    def make_request(self, data):
        request = self.factory.post("/api/v1/jobs/create", data=data)
        return CreateJobView.as_view()(request)


class TestCreateJobView(TestCase, Mixin, JobMixin):
    def setUp(self):
        self.factory = RequestFactory()

    @property
    def data(self):
        return {
            "template": self.job_template.id,
            "input_url": "s3://abc/video.mp4",
            "output_url": "s3://abc/video/output/video.m3u8",
            "meta_data": json.dumps({"content_url": "https://domain.com/chapters/chapter-3/40/"}),
        }

    @mock.patch("apps.api.v1.jobs.views.VideoTranscodeManager.start")
    def test_api_should_start_transcoding_for_valid_data(self, mock_video_transcode_manager):
        request = self.factory.post("/api/v1/jobs/create", data=self.data)
        response = CreateJobView.as_view()(request)

        self.assertEqual(201, response.status_code)
        self.assertTrue(Job.objects.filter(meta_data=self.data["meta_data"]).exists())
        mock_video_transcode_manager.assert_called()

    def test_api_should_fail_if_template_is_not_provided(self):
        data = self.data
        del data["template"]
        response = self.make_request(data)

        self.assertEqual(400, response.status_code)

    def test_api_should_fail_if_input_url_is_not_provided(self):
        data = self.data
        del data["input_url"]
        response = self.make_request(data)

        self.assertEqual(400, response.status_code)

    def test_api_should_fail_if_output_url_is_not_provided(self):
        data = self.data
        del data["output_url"]
        response = self.make_request(data)

        self.assertEqual(400, response.status_code)


class TestJobInfoView(TestCase, JobMixin):
    def setUp(self):
        self.factory = RequestFactory()

    def test_api_should_return_job_info_for_job(self):
        request = self.factory.get("/api/v1/jobs/%s" % self.job.id)
        response = job_info_view(request, self.job.id)

        self.assertEqual(200, response.status_code)
        self.assertEqual(response.data, self.job.job_info)

    def test_error_should_be_thrown_for_incorrect_job_id(self):
        request = self.factory.get("/api/v1/jobs/%s" % self.job.id)
        response = job_info_view(request, uuid.uuid4())

        self.assertEqual(404, response.status_code)

    def test_api_should_have_transcoding_details(self):
        request = self.factory.get("/api/v1/jobs/%s" % self.job.id)
        response = job_info_view(request, self.job.id)

        self.assertEqual(response.data["start_time"], self.job.start)
        self.assertEqual(response.data["end_time"], self.job.end)
        self.assertEqual(response.data["submission_time"], self.job.created)


class TestCancelJobView(TestCase, JobMixin):
    def setUp(self):
        self.factory = RequestFactory()

    @mock.patch("apps.api.v1.jobs.views.VideoTranscodeManager.stop")
    def test_api_should_cancel_job(self, mock_video_transcode_manager):
        request = self.factory.post("/api/v1/jobs/cancel", data={"job_id": self.job.id})
        response = cancel_job_view(request)

        self.assertEqual(200, response.status_code)
        mock_video_transcode_manager.assert_called()

    def test_error_should_be_thrown_for_incorrect_job_id(self):
        request = self.factory.post("/api/v1/jobs/cancel", data={"job_id": uuid.uuid4()})
        response = cancel_job_view(request)

        self.assertEqual(404, response.status_code)

    @mock.patch("apps.api.v1.jobs.views.VideoTranscodeManager.restart")
    def test_restart_api_should_restart_video_transcoding(self, mock_video_transcode_manager_restart):
        request = self.factory.post("/api/v1/jobs/restart", data={"job_id": self.job.id})
        response = restart_job_view(request)

        self.assertEqual(200, response.status_code)
        mock_video_transcode_manager_restart.assert_called()

    def test_restart_api_should_throw_error_for_incorrect_job_id(self):
        request = self.factory.post("/api/v1/jobs/restart", data={"job_id": uuid.uuid4()})
        response = restart_job_view(request)

        self.assertEqual(404, response.status_code)
