import abc
import os

import m3u8
from mpegdash.nodes import BaseURL
from mpegdash.parser import MPEGDASHParser
from smart_open import parse_uri, open

from django.conf import settings

from apps.ffmpeg.outputs import OutputFileFactory
from apps.ffmpeg.input_options import InputOptionsFactory


class ManifestGenerator(object):
    OUTPUT_FILE_NAME = None

    def __init__(self, job):
        self.job = job
        self.manifest_content = ""

    def read_file(self, path):
        with open(path, "r", transport_params=self.options.__dict__) as fp:
            return fp.read()

    @property
    def options(self):
        return InputOptionsFactory.get(self.job.output_url)

    def get_relative_output_path(self):
        uri = parse_uri(self.job.output_url)
        if uri.scheme == "s3":
            return uri.key_id

    def run(self):
        self.manifest_content = self.generate()
        self.upload()

    @abc.abstractmethod
    def generate(self):
        pass

    def upload(self):
        destination, file_name = os.path.split(self.job.output_url)
        storage = OutputFileFactory.create(destination + "/" + self.OUTPUT_FILE_NAME)
        storage.save_text(self.manifest_content)


class DashManifestGenerator(ManifestGenerator):
    OUTPUT_FILE_NAME = "video.mpd"

    def generate(self):
        manifest_paths = []
        for output in self.job.outputs.order_by("created"):
            manifest_paths.append(output.name + settings.DASH_OUTPUT_PATH_PREFIX + "/")

        initial_manifest_path = self.job.output_url + manifest_paths[0] + "video.mpd"
        initial_manifest = MPEGDASHParser.parse(self.read_file(initial_manifest_path))
        main_adaptation_set = self.get_adaptation_set(initial_manifest, "video")

        for representation in main_adaptation_set.representations:
            self.add_base_url_to_representation(representation, manifest_paths[0])

        for representation in self.get_adaptation_set(initial_manifest, "audio").representations:
            self.add_base_url_to_representation(representation, manifest_paths[0])

        for path in manifest_paths[1:]:
            manifest_path = self.job.output_url + path + "video.mpd"
            mpd = MPEGDASHParser.parse(self.read_file(manifest_path))
            for adaptation_set in mpd.periods[0].adaptation_sets:
                if adaptation_set.content_type == "video":
                    for representation in adaptation_set.representations:
                        self.add_base_url_to_representation(representation, path)
                        main_adaptation_set.representations.append(representation)
        return MPEGDASHParser.get_as_doc(initial_manifest).toprettyxml()

    def add_base_url_to_representation(self, representation, base_url_path):
        base_url = BaseURL()
        base_url.base_url_value = base_url_path
        representation.base_urls = base_url

    def get_adaptation_set(self, mpd, content_type):
        for adaptation_set in mpd.periods[0].adaptation_sets:
            if adaptation_set.content_type == content_type:
                return adaptation_set
        return None


class HLSManifestGeneratorForPackager(ManifestGenerator):
    OUTPUT_FILE_NAME = "video.m3u8"

    def generate(self):
        manifest_paths = []
        for output in self.job.outputs.order_by("created"):
            manifest_paths.append(output.name + settings.HLS_OUTPUT_PATH_PREFIX + "/")

        initial_manifest_path = self.job.output_url + manifest_paths[0] + "video.m3u8"
        main_manifest = m3u8.loads(self.read_file(initial_manifest_path))

        for playlist in main_manifest.playlists:
            self.add_base_bath_to_playlist(playlist, manifest_paths[0])

        for path in manifest_paths[1:]:
            manifest_path = self.job.output_url + path + "video.m3u8"
            manifest = m3u8.loads(self.read_file(manifest_path))
            for playlist in manifest.playlists:
                self.add_base_bath_to_playlist(playlist, path)
                main_manifest.playlists.append(playlist)
        return main_manifest.dumps()

    def add_base_bath_to_playlist(self, playlist, path):
        for media in playlist.media:
            media.uri = path + media.uri
        playlist.uri = path + playlist.uri


class HLSManifestGeneratorForFFMpeg(ManifestGenerator):
    OUTPUT_FILE_NAME = "video.m3u8"

    @property
    def manifest_header(self):
        return "#EXTM3U\n#EXT-X-VERSION:3\n"

    def generate(self):
        content = self.manifest_header
        media_details = self.get_media_details()
        for media_detail in media_details:
            content += (
                f"#EXT-X-STREAM-INF:BANDWIDTH={media_detail['bandwidth']},"
                f"RESOLUTION={media_detail['resolution']}\n{media_detail['name']}\n\n"
            )
        return content

    def get_media_details(self):
        media_details = []
        for output in self.job.outputs.order_by("created"):
            media_detail = {
                "bandwidth": output.video_bitrate,
                "resolution": output.resolution,
                "name": f"{output.name}/video.m3u8",
            }
            media_details.append(media_detail)
        return media_details
