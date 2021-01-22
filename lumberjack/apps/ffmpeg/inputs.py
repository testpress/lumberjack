import abc

from smart_open import parse_uri
import boto3

from django.conf import settings


def get_input_path(path):
    if path.startswith("http"):
        return path

    if path.startswith("s3://"):
        return S3InputPath(path).generate()

    return path


def generate_file_name_from_format(format):
    if format.lower() == "mp4":
        return "video.mp4"
    elif format.lower() == "hls":
        return "video.m3u8"


class InputPath(abc.ABC):
    def __init__(self, source):
        self.source = source

    @abc.abstractmethod
    def generate(self):
        pass


class S3InputPath(InputPath):
    def __init__(self, source):
        super().__init__(source)
        session = boto3.Session(
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name="ap-southeast-1",
        )
        self.client = session.client("s3")
        self.source = source

    def generate(self):
        s3_path = parse_uri(self.source)
        params = {
            "Bucket": s3_path.bucket_id,
            "Key": s3_path.key_id,
        }
        response = self.client.generate_presigned_url("get_object", Params=params, ExpiresIn=86400)
        return response
