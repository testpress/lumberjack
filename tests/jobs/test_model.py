import mock

from django.test import TestCase

from .mixins import Mixin


class TestJobModel(Mixin, TestCase):
    def setUp(self) -> None:
        self.job.webhook_url = "http://domain.com"
        self.job.save()

    @mock.patch("apps.jobs.tasks.PostDataToWebhookTask")
    def test_job_info_should_be_posted_to_webhook_on_status_change(self, mock_post_data_to_webhook):
        self.job.status = "Completed"
        self.job.save()

        mock_post_data_to_webhook.apply_async.assert_called()
        mock_post_data_to_webhook.apply_async.assert_called_with(args=(self.job.job_info, self.job.webhook_url))
