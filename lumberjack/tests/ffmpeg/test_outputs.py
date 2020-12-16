from mock import patch

from moto import mock_s3
from botocore.exceptions import ClientError

from django.test import SimpleTestCase

from apps.ffmpeg.outputs import OutputFactory, FileStorage, S3


class TestOutputFactory(SimpleTestCase):
    def test_factory_should_create_s3_storage_for_s3_url(self):
        input_options = OutputFactory.create("s3://bucket/key")

        self.assertTrue(isinstance(input_options, S3))

    def test_factory_should_create_file_storage_instance_for_other_url(self):
        input_options = OutputFactory.create("file://a/b/c")

        self.assertTrue(isinstance(input_options, FileStorage))


class TestS3Storage(SimpleTestCase):
    def setUp(self) -> None:
        self.s3_mock = mock_s3()
        self.s3_mock.start()
        self.s3_storage = S3("s3://somebucket/folder")
        self.s3_storage.client.create_bucket(Bucket="somebucket")

    @patch("os.remove")
    def test_store_should_upload_files_to_s3_and_remove_it(self, mock_os_remove):
        self.s3_storage.save("tests/ffmpeg/data")

        s3_response = self.s3_storage.client.get_object(Bucket="somebucket", Key="folder/video.mp4")
        self.assertEqual(200, s3_response["ResponseMetadata"]["HTTPStatusCode"])
        self.assertTrue(mock_os_remove.called)

    @patch("os.remove")
    def test_delete_should_delete_folder_from_s3(self, mock_os_remove):
        self.s3_storage.save("tests/ffmpeg/data")
        self.s3_storage.delete("folder")

        with self.assertRaises(ClientError):
            self.s3_storage.client.head_object(Bucket="somebucket", Key="folder/video.mp4")

    @patch("os.remove")
    def test_delete_should_not_delete_if_root_folder(self, mock_os_remove):
        self.s3_storage.save("tests/ffmpeg/data")
        self.s3_storage.delete("/")

        s3_response = self.s3_storage.client.get_object(Bucket="somebucket", Key="folder/video.mp4")
        self.assertEqual(200, s3_response["ResponseMetadata"]["HTTPStatusCode"])

    def tearDown(self) -> None:
        self.s3_mock.stop()
