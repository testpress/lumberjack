import mock
from django.test import SimpleTestCase

from apps.executors.base import Status
from apps.jobs.controller import CloudUploader


class TestCloudUploader(SimpleTestCase):
    @mock.patch("apps.ffmpeg.outputs.S3")
    def test_cloud_uploader_should_upload_local_directory_to_s3(self, mock_s3):
        mock_s3.return_value.save.return_value = mock.MagicMock()
        cloud_node = CloudUploader("/abc/1232/360p", "s3://bucket_url/abc")
        cloud_node._status = Status.Running
        cloud_node.start()

        mock_s3().save.assert_called_with("/abc/1232/360p", is_transcode_completed=False)
        cloud_node.stop(None)

    @mock.patch("apps.ffmpeg.outputs.S3")
    def test_upload_should_be_triggered_one_last_time_after_cloud_thread_stop(self, mock_s3):
        mock_s3.return_value.save.return_value = mock.MagicMock()
        cloud_node = CloudUploader("/abc/1232/360p", "s3://bucket_url/abc")
        cloud_node._status = Status.Running
        cloud_node.start()
        mock_s3.reset_mock()

        cloud_node.stop(None)
        mock_s3().save.assert_called_with("/abc/1232/360p", is_transcode_completed=True)
