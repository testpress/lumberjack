
import binascii

from django.conf import settings

from apps.ffmpeg.utils import mkdir
import os


class CommandGenerator(object):
    def __init__(self, options):
        self.options = options

    def generate(self):
        arguments = " ".join(self.to_args(**self.input_argument, **self.media_options))
        command = self.ffmpeg_binary + " " + arguments + " " + self.output_path
        return command

    def to_args(self, **kwargs: dict):
        args = []
        for key, value in kwargs.items():
            args.append('-{}'.format(key))
            if value is not None:
                args.append('{}'.format(value))

        return args

    @property
    def ffmpeg_binary(self):
        return 'ffmpeg -y'

    @property
    def input_argument(self):
        return {"i": "-"}

    @property
    def output_path(self):
        return "{}/{}/video.m3u8".format(settings.TRANSCODED_VIDEOS_PATH, self.options.get("id"))

    @property
    def media_options(self):
        if self.options.get("format").lower() == "hls":
            return HLSOptions(self.options).all
        return MediaOptions(self.options).all


class MediaOptions(object):
    DEFAULT_VIDEO_CODEC = "h265"
    DEFAULT_AUDIO_CODEC = "aac"
    DEFAULT_PRESET = "fast"

    def __init__(self, options):
        self.options = options
        self.output_options = options.get("output")
        self.video = self.output_options.get("video")
        self.audio = self.output_options.get("audio")

    def video_options(self):
        options = {
            "c:v": self.video.get("codec", self.DEFAULT_VIDEO_CODEC),
            "preset": self.video.get("preset", self.DEFAULT_PRESET),
            "s": "{}x{}".format(self.video.get("width"), self.video.get("height"))
        }

        if self.video.get("bitrate"):
            options["b:v"] = self.video.get("bitrate")

        return options

    def audio_options(self):
        return {
            "c:a": self.audio.get("codec", self.DEFAULT_AUDIO_CODEC)
        }

    @property
    def all(self) -> dict:
        args = {}
        args.update(self.audio_options())
        args.update(self.video_options())
        return args


class HLSOptions(MediaOptions):
    DEFAULT_SEGMENT_LENGTH = 10

    @property
    def key_folder_path(self):
        return "{}/{}/key".format(settings.TRANSCODED_VIDEOS_PATH, self.options.get("id"))

    @property
    def all(self):
        args = super().all
        args.update({
            "format": "hls",
            "hls_list_size": 0,
            "hls_time": self.options.get("segment_length", self.DEFAULT_SEGMENT_LENGTH),
            "hls_segment_filename": "{}/{}/{}/video_%d.ts".format(
                settings.TRANSCODED_VIDEOS_PATH, self.options.get("id"), self.output_options.get("name")
            ),
        })

        if self.options.get("encryption"):
            encryption_data = self.options.get("encryption")
            args["hls_key_info_file"] = HLSKeyInfoFile(
                encryption_data["key"], encryption_data["url"], self.key_folder_path
            )
        return args


class HLSKeyInfoFile:
    def __init__(self, key, key_url, local_path):
        self.key = key
        self.key_url = key_url
        mkdir(local_path)
        self.key_path = "{}/enc.key".format(local_path)
        self.key_info_file_path = "{}/enc.keyinfo".format(local_path)

    def __str__(self):
        self.store_key_locally()
        return self.key_info_file_path

    def store_key_locally(self):
        self.store_key()
        self.store_key_info()

    def store_key(self):
        with open(self.key_path, "wb") as key:
            key.write(binascii.unhexlify(self.key))

    def store_key_info(self):
        with open(self.key_info_file_path, 'w') as key_info_file:
            key_info_file.write("\n".join([self.key_url, self.key_path]))