import abc
import os
import re
import shutil
import io

from smart_open import parse_uri, open
import boto3
from botocore.exceptions import ClientError

from django.conf import settings


class OutputFileFactory:
    @staticmethod
    def create(url, **options):
        if parse_uri(url).scheme == "s3":
            return S3(url)
        return LocalFileStorage(url)


class Storage(abc.ABC):
    @abc.abstractmethod
    def save(self, directory, **options):
        pass

    @abc.abstractmethod
    def save_text(self, content: str):
        pass


class S3(Storage):
    INCOMPLETE_MANIFEST_FILES = r".*\.m3u8"

    def __init__(self, destination_url):
        session = boto3.Session(
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_CODE,
        )
        self.client = session.client("s3")
        self.destination_url = destination_url
        self.is_uploading = False

    def save(self, source_directory, is_transcode_completed=False):
        exclude_files = []
        if not is_transcode_completed:
            exclude_files = [self.INCOMPLETE_MANIFEST_FILES]

        if self.is_uploading:
            return

        self.upload_directory(source_directory, exclude_files)

    def upload_directory(self, source_directory, files_to_exclude):
        self.is_uploading = True
        for root, dirs, files in os.walk(source_directory):
            for filename in files:
                if self.should_skip_upload(filename, files_to_exclude):
                    continue

                absolute_path = os.path.join(root, filename)
                self.upload_file(absolute_path, source_directory)
                os.remove(absolute_path)
        self.is_uploading = False

    def should_skip_upload(self, filename, files_to_exclude=[]):
        if filename.endswith(".tmp"):
            return True

        regex = "(?:% s)" % "|".join(files_to_exclude)
        if files_to_exclude and re.match(regex, filename):
            return True
        return False

    def upload_file(self, absolute_file_path, source_directory):
        relative_path = os.path.relpath(absolute_file_path, source_directory)
        s3_path = parse_uri(os.path.join(self.destination_url, relative_path))

        try:
            self.client.head_object(Bucket=s3_path.bucket_id, Key=s3_path.key_id)
        except ClientError:
            self.client.upload_file(
                absolute_file_path, s3_path.bucket_id, s3_path.key_id, ExtraArgs={"ACL": "public-read"}
            )

    def save_text(self, content: str):
        s3_path = parse_uri(self.destination_url)
        file_obj = io.BytesIO(content.encode())
        self.client.upload_fileobj(file_obj, s3_path.bucket_id, s3_path.key_id, ExtraArgs={"ACL": "public-read"})


class LocalFileStorage(Storage):
    def __init__(self, destination_directory):
        self.destination_directory = destination_directory
        self.is_being_moved = False

    def save(self, source_directory, exclude_m3u8=False):
        if self.is_being_moved:
            return

        self.is_being_moved = True
        shutil.move(source_directory, self.destination_directory)
        self.is_being_moved = False

    def save_text(self, content):
        content_as_bytes = io.BytesIO(content.encode()).read()
        with open(self.destination_directory, "wb") as fout:
            fout.write(content_as_bytes)
