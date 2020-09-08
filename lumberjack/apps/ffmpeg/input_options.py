from abc import ABC, abstractmethod

from smart_open import parse_uri
import boto3

from django.conf import settings


class InputOptionsFactory(object):
    @staticmethod
    def get(input_url):
        if parse_uri(input_url).scheme == "s3":
            return S3InputOptions()
        return FileStorageInputOptions()


class AbstractInputOptions(ABC):
    @property
    @abstractmethod
    def options(self):
        pass

    @property
    def __dict__(self):
        return self.options


class FileStorageInputOptions(AbstractInputOptions):
    @property
    def options(self):
        return {"buffer_size": 1024}


class S3InputOptions(AbstractInputOptions):
    @property
    def options(self):
        session = boto3.Session(
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_CODE,
        )
        return {"session": session, "buffer_size": 32000}
