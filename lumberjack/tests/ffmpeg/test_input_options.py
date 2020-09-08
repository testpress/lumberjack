from django.test import SimpleTestCase

from boto3 import session

from apps.ffmpeg.input_options import InputOptionsFactory, S3InputOptions, FileStorageInputOptions


class TestInputOptionsFactory(SimpleTestCase):
    def test_factory_should_return_correct_s3_input_options_instance_for_s3_url(self):
        input_options = InputOptionsFactory.get("s3://bucket/key")

        self.assertTrue(isinstance(input_options, S3InputOptions))

    def test_should_return_input_options_instance_for_other_url(self):
        input_options = InputOptionsFactory.get("file://a/b/c")

        self.assertTrue(isinstance(input_options, FileStorageInputOptions))


class TestInputOptions(SimpleTestCase):
    def test_input_options_should_return_empty_dict(self):
        input_options = FileStorageInputOptions()

        self.assertDictEqual(input_options.__dict__, {"buffer_size": 1024})


class TestS3InputOptions(SimpleTestCase):
    def test_s3_input_options_should_return_boto_session(self):
        input_options = S3InputOptions().options
        session_param = input_options.get("session")

        self.assertTrue(isinstance(session_param, session.Session))
