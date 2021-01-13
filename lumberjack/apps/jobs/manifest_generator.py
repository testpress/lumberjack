import abc
import os

import m3u8
from mpegdash.nodes import BaseURL
from mpegdash.parser import MPEGDASHParser
from smart_open import parse_uri, open
from m3u8.model import PlaylistList

from django.conf import settings

from apps.ffmpeg.outputs import OutputFileFactory
from apps.ffmpeg.input_options import InputOptionsFactory


class ManifestMerger(object):
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
        self.manifest_content = self.merge()
        self.upload()

    @abc.abstractmethod
    def merge(self):
        pass

    def upload(self):
        destination, file_name = os.path.split(self.job.output_url)
        storage = OutputFileFactory.create(destination + "/" + self.OUTPUT_FILE_NAME)
        storage.save_text(self.manifest_content)


class DashManifestGenerator(ManifestMerger):
    OUTPUT_FILE_NAME = "video.mpd"

    def merge(self):
        manifest_paths = self.get_relative_manifest_paths()
        initial_manifest = self.modify_base_manifest(manifest_paths[0])
        main_adaptation_set = self.get_adaptation_set(initial_manifest, "video")
        main_adaptation_set.representations = self.add_base_url_to_representations(manifest_paths)
        self.change_id_in_representations(main_adaptation_set)
        return MPEGDASHParser.get_as_doc(initial_manifest).toprettyxml()

    def get_relative_manifest_paths(self):
        manifest_paths = []
        for output in self.job.outputs.order_by("created"):
            manifest_paths.append(output.name + settings.DASH_OUTPUT_PATH_PREFIX + "/")
        return manifest_paths

    def add_base_url_to_representation(self, representation, base_url_path):
        base_url = BaseURL()
        base_url.base_url_value = base_url_path
        representation.base_urls = base_url

    def get_adaptation_set(self, mpd, content_type):
        for adaptation_set in mpd.periods[0].adaptation_sets:
            if adaptation_set.content_type == content_type:
                return adaptation_set
        return None

    def change_id_in_representations(self, adaptation_set):
        for i, representation in enumerate(adaptation_set.representations):
            representation.id = i

    def modify_representations(self, adaptation_set, output_path):
        for representation in adaptation_set.representations:
            representation.width = adaptation_set.width
            representation.height = adaptation_set.height
            self.add_base_url_to_representation(representation, output_path)
        return adaptation_set.representations

    def modify_base_manifest(self, manifest_path):
        initial_manifest_path = self.job.output_url + manifest_path + self.OUTPUT_FILE_NAME
        initial_manifest = MPEGDASHParser.parse(self.read_file(initial_manifest_path))

        for representation in self.get_adaptation_set(initial_manifest, "audio").representations:
            self.add_base_url_to_representation(representation, manifest_path)
        return initial_manifest

    def add_base_url_to_representations(self, manifest_paths):
        all_representations = []
        for i, path in enumerate(manifest_paths):
            manifest_path = self.job.output_url + path + self.OUTPUT_FILE_NAME
            mpd = MPEGDASHParser.parse(self.read_file(manifest_path))
            adaptation_set = self.get_adaptation_set(mpd, "video")
            modified_representations = self.modify_representations(adaptation_set, path)
            all_representations.extend(modified_representations)
        return all_representations


class HLSManifestGeneratorForPackager(ManifestMerger):
    OUTPUT_FILE_NAME = "video.m3u8"

    def merge(self):
        manifest_paths = self.get_relative_manifest_paths()
        main_manifest = self.modify_base_manifest(manifest_paths[0])
        main_manifest.playlists = self.add_base_path_to_playlists(manifest_paths)
        return main_manifest.dumps()

    def add_base_bath_to_playlist(self, playlist, path):
        for media in playlist.media:
            media.uri = path + media.uri
        playlist.uri = path + playlist.uri

    def modify_base_manifest(self, path):
        initial_manifest_path = self.job.output_url + path + self.OUTPUT_FILE_NAME
        main_manifest = m3u8.loads(self.read_file(initial_manifest_path))
        self.modify_media_uri(main_manifest, path)
        return main_manifest

    def modify_media_uri(self, manifest, path):
        for media in manifest.media:
            media.uri = path + media.uri

    def add_base_path_to_playlists(self, paths):
        playlists = PlaylistList()
        for path in paths:
            manifest_path = self.job.output_url + path + self.OUTPUT_FILE_NAME
            manifest = m3u8.loads(self.read_file(manifest_path))
            for playlist in manifest.playlists:
                self.add_base_bath_to_playlist(playlist, path)
                playlists.append(playlist)
        return playlists

    def get_relative_manifest_paths(self):
        manifest_paths = []
        for output in self.job.outputs.order_by("created"):
            manifest_paths.append(output.name + settings.HLS_OUTPUT_PATH_PREFIX + "/")
        return manifest_paths


class HLSManifestGeneratorForFFMpeg(ManifestMerger):
    OUTPUT_FILE_NAME = "video.m3u8"

    @property
    def manifest_header(self):
        return "#EXTM3U\n#EXT-X-VERSION:3\n"

    def merge(self):
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
