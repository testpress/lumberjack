import os
import logging


def mkdir(dirname: str) -> None:
    try:
        os.makedirs(dirname)
    except OSError as exc:
        logging.info(exc)


def generate_file_name_from_format(format):
    if format.lower() == "mp4":
        return "video.mp4"
    elif format.lower() == "hls":
        return "video.m3u8"
