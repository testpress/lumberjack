import abc
import os

from smart_open import parse_uri
import boto3
from botocore.exceptions import ClientError


class OutputFactory:
    @staticmethod
    def create(url, **options):
        if parse_uri(url).scheme == "s3":
            return S3(url)
        return FileStorage()


class Storage(abc.ABC):
    @abc.abstractmethod
    def store(self, directory, **options):
        pass


class S3(Storage):
    def __init__(self, destination_url):
        session = boto3.Session(
            aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
            aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
            region_name="ap-southeast-1"
        )
        self.client = session.client("s3")
        self.destination_url = destination_url
        self.is_uploading = False

    def store(self, directory, exclude_m3u8=False):
        if self.is_uploading:
            return

        self.is_uploading = True
        for root, dirs, files in os.walk(directory):
            for filename in files:
                if filename.endswith(".tmp") or exclude_m3u8 and filename.endswith(".m3u8"):
                    continue
                local_path = os.path.join(root, filename)
                relative_path = os.path.relpath(local_path, directory)
                s3_path = parse_uri(os.path.join(self.destination_url, relative_path))

                try:
                    self.client.head_object(Bucket=s3_path.bucket_id, Key=s3_path.key_id)
                    os.remove(local_path)
                except ClientError:
                    self.client.upload_file(local_path, s3_path.bucket_id, s3_path.key_id)
                    os.remove(local_path)
        self.is_uploading = False


class FileStorage(Storage):
    def store(self, *args, **options):
        pass
