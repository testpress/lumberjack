import os
import logging


def mkdir(dirname: str) -> None:
    try:
        os.makedirs(dirname)
    except OSError as exc:
        logging.info(exc)
        pass