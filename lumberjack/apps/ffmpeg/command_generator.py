import binascii
from collections import OrderedDict

from django.conf import settings

from apps.ffmpeg.utils import mkdir, generate_file_name_from_format
from .inputs import get_input_path


class CommandGenerator(object):
    def __init__(self, options):
        self.options = options

    def generate(self):
        arguments = " ".join(self.to_args(**self.input_argument, **self.media_options, **self.output_arguments))
        command = self.ffmpeg_binary + " " + arguments + " " + self.output_path
        return command

    def to_args(self, **kwargs: dict):
        args = []
        for key, value in kwargs.items():
            args.append("-{}".format(key))
            if value is not None:
                args.append("{}".format(value))

        return args

    @property
    def ffmpeg_binary(self):
        return "ffmpeg -hide_banner"

    @property
    def input_argument(self):
        path = self.options.get("input")
        FIVE_MINUTES = 300
        input_arguments = OrderedDict()

        if get_input_path(path).startswith("http"):
            input_arguments.update({"reconnect": 1, "reconnect_streamed": 1, "reconnect_delay_max": FIVE_MINUTES})

        input_arguments.update({"i": get_input_path(path)})
        return input_arguments

    @property
    def local_path(self):
        return "{}/{}".format(settings.TRANSCODED_VIDEOS_PATH, self.options.get("id"))

    @property
    def output_arguments(self):
        return {"max_muxing_queue_size": 9999}

    @property
    def output_path(self):
        file_name = self.options.get("file_name")
        if not file_name:
            file_name = generate_file_name_from_format(self.options.get("format"))

        return "{}/{}/{}".format(self.local_path, self.options.get("output")["name"], file_name)

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
            "s": "{}x{}".format(self.video.get("width"), self.video.get("height")),
        }

        if self.video.get("bitrate"):
            options["b:v"] = self.video.get("bitrate")

        return options

    def audio_options(self):
        options = {"c:a": self.audio.get("codec", self.DEFAULT_AUDIO_CODEC)}

        if self.audio.get("bitrate"):
            options["b:a"] = self.audio.get("bitrate")

        return options

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
        args.update(
            {
                "format": "hls",
                "hls_list_size": 0,
                "hls_time": self.options.get("segment_length", self.DEFAULT_SEGMENT_LENGTH),
                "hls_segment_filename": "{}/{}/{}/video_%d.ts".format(
                    settings.TRANSCODED_VIDEOS_PATH, self.options.get("id"), self.output_options.get("name")
                ),
            }
        )

        if self.options.get("encryption"):
            encryption_data = self.options.get("encryption")
            hls_key_info_file = HLSKeyInfoFile(encryption_data["key"], encryption_data["url"], self.key_folder_path)
            hls_key_info_file.create()
            args["hls_key_info_file"] = hls_key_info_file.path
        return args


class HLSKeyInfoFile:
    def __init__(self, key, key_url, local_path):
        self.key = key
        self.key_url = key_url
        mkdir(local_path)
        self.key_path = "{}/enc.key".format(local_path)
        self.key_info_file_path = "{}/enc.keyinfo".format(local_path)

    def create(self):
        self.save_key()
        self.save_key_info()

    @property
    def path(self):
        return self.key_info_file_path

    def __str__(self):
        return self.key_info_file_path

    def save_key(self):
        with open(self.key_path, "wb") as key:
            key.write(binascii.unhexlify(self.key))

    def save_key_info(self):
        with open(self.key_info_file_path, "w") as key_info_file:
            key_info_file.write("\n".join([self.key_url, self.key_path]))
