import os
import logging


def mkdir(dirname: str) -> None:
    try:
        os.makedirs(dirname)
    except OSError as exc:
        logging.info(exc)


class ExtensionGenerator:
    def get(self, file_type):
        if file_type.lower() == "mp4":
            return "mp4"
        elif file_type.lower() == "hls":
            return "m3u8"
        elif file_type.lower() == "dash":
            return "mpd"
