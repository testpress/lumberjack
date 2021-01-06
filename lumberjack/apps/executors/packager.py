import os
import subprocess

from typing import List

from .base import PolitelyWaitOnFinishMixin
from apps.ffmpeg.utils import mkdir

INIT_SEGMENT_OUTPUT_TEMPLATE = {
    "audio": "{dir}/audio_init.{format}",
    "video": "{dir}/video_{resolution_name}_init.{format}",
}

MEDIA_SEGMENT_OUTPUT_TEMPLATE = {
    "audio": "{dir}/audio_$Number$.{format}",
    "video": "{dir}/video_{resolution_name}_$Number$.{format}",
}


class ShakaPackager(PolitelyWaitOnFinishMixin):
    def __init__(self, config, output_dir):
        super().__init__()
        self._output_dir = output_dir
        self._segment_dir = os.path.join(output_dir, config.get("segment_folder", ""))
        self.config = config
        mkdir(self._output_dir)

    def start_process(self):
        args = self.get_packager_command()
        return self._create_process(args, stderr=subprocess.STDOUT, stdout=None)

    def get_packager_command(self):
        args = ["packager"]
        args += [self._setup_video_stream(self.config.get("output"))]
        args += [self._setup_audio_stream(self.config.get("output"))]
        args += [
            "--segment_duration",
            str(self.config.get("segment_size", 10)),
        ]

        args += self._setup_manifest_format()
        return args

    def _setup_video_stream(self, stream) -> str:
        stream_dict = {
            "in": stream.get("pipe") or stream.get("input"),
            "stream": "video",
        }

        if stream.get("segment_per_file", True):
            stream_dict["init_segment"] = INIT_SEGMENT_OUTPUT_TEMPLATE["video"].format(
                dir=self._segment_dir, resolution_name=stream.get("name"), format="mp4"
            )
            stream_dict["segment_template"] = MEDIA_SEGMENT_OUTPUT_TEMPLATE["video"].format(
                dir=self._segment_dir, resolution_name=stream.get("name"), format="mp4"
            )

        return ",".join(key + "=" + value for key, value in stream_dict.items())

    def _setup_audio_stream(self, stream) -> str:
        stream_dict = {
            "in": stream.get("pipe") or stream.get("input"),
            "stream": "audio",
        }

        if stream.get("segment_per_file", True):
            stream_dict["init_segment"] = INIT_SEGMENT_OUTPUT_TEMPLATE["audio"].format(
                dir=self._segment_dir, resolution_name=stream.get("name"), format="mp4"
            )
            stream_dict["segment_template"] = MEDIA_SEGMENT_OUTPUT_TEMPLATE["audio"].format(
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

    def _setup_encryption(self) -> List[str]:
        args = []
        if self.config.get("encryption").get("widevine"):
            widevine = self.config.get("drm_encryption").get("widevine")
            args = [
                '--enable_widevine_encryption',
                '--key_server_url', widevine.key_server_url,
                '--content_id', widevine.content_id,
                '--signer', widevine.signer,
                '--aes_signing_key', widevine.aes_signing_key,
                '--aes_signing_iv', widevine.aes_signing_iv,
            ]
        elif self.config.get("encryption").get("fairplay"):
            fairplay = self.config.get("drm_encryption").get("fairplay")
            args = [
                '--enable_raw_key_encryption',
                '--keys',
                'label=AUDIO:key=%s' % fairplay.key,
                "--protection_systems", "Fairplay",
                "--iv", fairplay.iv,
                "--hls_key_uri", fairplay.uri
            ]
        return args
