import abc
import os

import m3u8
from mpegdash.nodes import BaseURL
from mpegdash.parser import MPEGDASHParser
from smart_open import parse_uri

from django.conf import settings

from apps.ffmpeg.outputs import OutputFileFactory
from apps.ffmpeg.utils import generate_file_name_from_format


class ManifestGenerator(object):
    OUTPUT_FILE_NAME = None

    def __init__(self, job):
        self.output_cdn_url = job.output_cdn_url
        self.job = job
        self.manifest_content = ""

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
        if not file_name:
            file_name = generate_file_name_from_format(self.job.settings.get("format"))

        storage = OutputFileFactory.create(destination + "/" + file_name)
        storage.save_text(self.manifest_content)


class DashManifestGenerator(ManifestGenerator):
    OUTPUT_FILE_NAME = "video.mpd"

    def generate(self):
        manifest_paths = []
        for output in self.job.outputs.order_by("created"):
            manifest_paths.append(output.name + settings.DASH_OUTPUT_PATH_PREFIX + "/")

        initial_manifest_path = self.output_cdn_url + self.get_relative_output_path() + manifest_paths[0] + "video.mpd"
        initial_manifest = MPEGDASHParser.parse(initial_manifest_path)
        main_adaptation_set = self.get_adaptation_set(initial_manifest, "video")

        for representation in main_adaptation_set.representations:
            base_url = BaseURL()
            base_url.base_url_value = manifest_paths[0]
            representation.base_urls = base_url

        for representation in self.get_adaptation_set(initial_manifest, "audio").representations:
            base_url = BaseURL()
            base_url.base_url_value = manifest_paths[0]
            representation.base_urls = base_url

        for path in manifest_paths[1:]:
            manifest_path = self.output_cdn_url + self.get_relative_output_path() + path + "video.mpd"
            mpd = MPEGDASHParser.parse(manifest_path)
            for adaptation_set in mpd.periods[0].adaptation_sets:
                if adaptation_set.content_type == "video":
                    for representation in adaptation_set.representations:
                        base_url = BaseURL()
                        base_url.base_url_value = path
                        representation.base_urls = base_url
                        main_adaptation_set.representations.append(representation)
        return MPEGDASHParser.get_as_doc(initial_manifest).toprettyxml()

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

        initial_manifest_path = self.output_cdn_url + self.get_relative_output_path() + manifest_paths[0] + "video.m3u8"
        main_manifest = m3u8.load(initial_manifest_path)

        for playlist in main_manifest.playlists:
            playlist.media[0].uri = manifest_paths[0] + playlist.media[0].uri
            playlist.uri = manifest_paths[0] + playlist.uri

        for path in manifest_paths[1:]:
            manifest_path = self.output_cdn_url + self.get_relative_output_path() + path + "video.m3u8"
            manifest = m3u8.load(manifest_path)
            for playlist in manifest.playlists:
                playlist.media[0].uri = path + playlist.media[0].uri
                playlist.uri = path + playlist.uri
                main_manifest.playlists.append(playlist)
        return main_manifest.dumps()


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
