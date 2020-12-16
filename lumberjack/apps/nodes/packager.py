import os
import subprocess
import enum

from typing import List

from .base import PolitelyWaitOnFinish

INIT_SEGMENT = {
    "audio": "{dir}/audio_init.{format}",
    "video": "{dir}/video_{resolution_name}_init.{format}",
}

MEDIA_SEGMENT = {
    "audio": "{dir}/audio_$Number$.{format}",
    "video": "{dir}/video_{resolution_name}_$Number$.{format}",
}

SINGLE_SEGMENT = {
    "audio": "{dir}/audio_{language}_{channels}c_{bitrate}.{format}",
    "video": "{dir}/video_{resolution_name}_{bitrate}.{format}",
}


class PackagerNode(PolitelyWaitOnFinish):
    def __init__(self, config, output_dir):
        super().__init__()
        self._output_dir = output_dir
        self._segment_dir = os.path.join(output_dir, config.get("segment_folder", ""))
        self.config = config

    def start(self):
        args = ["packager"]
        args += [self._setup_video_stream(self.config.get("output"))]
        args += [self._setup_audio_stream(self.config.get("output"))]
        args += [
            "--segment_duration",
            str(self.config.get("segment_size", 10)),
        ]

        args += self._setup_manifest_format()
        self._process = self._create_process(args, stderr=subprocess.STDOUT, stdout=None)

    def _setup_video_stream(self, stream) -> str:
        stream_dict = {
            "in": stream.get("pipe") or stream.get("input"),
            "stream": "video",
        }

        if stream.get("segment_per_file", True):
            stream_dict["init_segment"] = INIT_SEGMENT["video"].format(
                dir=self._segment_dir, resolution_name=stream.get("name"), format="mp4"
            )
            stream_dict["segment_template"] = MEDIA_SEGMENT["video"].format(
                dir=self._segment_dir, resolution_name=stream.get("name"), format="mp4"
            )

        return ",".join(key + "=" + value for key, value in stream_dict.items())

    def _setup_audio_stream(self, stream) -> str:
        stream_dict = {
            "in": stream.get("pipe") or stream.get("input"),
            "stream": "audio",
        }

        if stream.get("segment_per_file", True):
            stream_dict["init_segment"] = INIT_SEGMENT["audio"].format(
                dir=self._segment_dir, resolution_name=stream.get("name"), format="mp4"
            )
            stream_dict["segment_template"] = MEDIA_SEGMENT["audio"].format(
                dir=self._segment_dir, resolution_name=stream.get("name"), format="mp4"
            )

        return ",".join(key + "=" + value for key, value in stream_dict.items())

    def _setup_manifest_format(self) -> List[str]:
        args: List[str] = []
        if self.config.get("format") in ["dash", "adaptive"]:
            if self.config.get("playlist_type") == "vod":
                args += [
                    "--generate_static_live_mpd",
                ]
            args += [
                "--mpd_output",
                os.path.join(self._output_dir, self.config.get("dash_output", "video.mpd")),
            ]

        if self.config.get("format") in ["hls", "adaptive"]:
            if self.config.get("playlist_type") == "live":
                args += [
                    "--hls_playlist_type",
                    "LIVE",
                ]
            else:
                args += [
                    "--hls_playlist_type",
                    "VOD",
                ]
            args += [
                "--hls_master_playlist_output",
                os.path.join(self._output_dir, self.config.get("hls_output", "video.m3u8")),
            ]
        return args
