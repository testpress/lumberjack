import abc

import m3u8
from mpegdash.nodes import BaseURL
from mpegdash.parser import MPEGDASHParser
from smart_open import parse_uri

from apps.ffmpeg.outputs import OutputFileFactory


class ManifestGenerator(object):
    OUTPUT_FILE_NAME = None

    def __init__(self, job):
        self.output_cdn_url = job.output_cdn_url
        self.job = job
        self.relative_output_path = self.get_relative_output_path()
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
        upload_url = self.job.output_url + self.OUTPUT_FILE_NAME
        storage = OutputFileFactory.create(upload_url)
        storage.save_text(self.manifest_content, upload_url)


class DashManifestGenerator(ManifestGenerator):
    OUTPUT_FILE_NAME = "video.mpd"

    def generate(self):
        manifest_paths = []
        for output in self.job.outputs.order_by("created"):
            manifest_paths.append(output.name + "_dash/")

        initial_manifest_path = self.output_cdn_url + self.relative_output_path + manifest_paths[0] + "video.mpd"
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
            manifest_path = self.output_cdn_url + self.relative_output_path + path + "video.mpd"
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


class HLSManifestGenerator(ManifestGenerator):
    OUTPUT_FILE_NAME = "video.m3u8"

    @property
    def manifest_header(self):
        return "#EXTM3U\n#EXT-X-VERSION:3\n"

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

    def generate_manifest_content(self):
        content = self.manifest_header
        media_details = self.get_media_details()
        for media_detail in media_details:
            content += (
                f"#EXT-X-STREAM-INF:BANDWIDTH={media_detail['bandwidth']},"
                f"RESOLUTION={media_detail['resolution']}\n{media_detail['name']}\n\n"
            )
        return content

    def generate(self):
        manifest_paths = []
        for output in self.job.outputs.order_by("created"):
            manifest_paths.append(output.name + "_hls/")

        initial_manifest_path = self.output_cdn_url + self.relative_output_path + manifest_paths[0] + "video.m3u8"
        main_manifest = m3u8.load(initial_manifest_path)

        if not main_manifest.playlists:
            return self.generate_manifest_content()

        for pl in main_manifest.playlists:
            pl.media[0].uri = manifest_paths[0] + pl.media[0].uri
            pl.uri = manifest_paths[0] + pl.uri

        for path in manifest_paths[1:]:
            manifest_path = self.output_cdn_url + self.relative_output_path + path + "video.m3u8"
            manifest = m3u8.load(manifest_path)
            for pl in manifest.playlists:
                pl.media[0].uri = path + pl.media[0].uri
                pl.uri = path + pl.uri
            main_manifest.playlists.append(pl)
        return main_manifest.dumps()
