# Copyright 2019 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import tempfile
import uuid
import copy
from typing import List
import threading

from django.conf import settings

from apps.executors.base import Status, BaseExecutor
from apps.executors.cloud import CloudUploader
from apps.executors.transcoder import FFMpegTranscoder
from apps.executors.packager import ShakaPackager
from apps.presets.models import JobTemplate


class OneToManyPipeWriter(threading.Thread):
    def __init__(self, input_pipe):
        super().__init__()
        self.input_pipe = input_pipe
        self.output_pipes = []

    def register_output_pipe(self, pipe):
        self.output_pipes.append(pipe)

    def run(self) -> None:
        output_file_pointers = [open(pipe, "wb") for pipe in self.output_pipes]
        while True:
            with open(self.input_pipe, "rb") as fifo:
                for line in fifo:
                    for fp in output_file_pointers:
                        fp.write(line)
            for fp in output_file_pointers:
                fp.close()


class LumberjackController(object):
    def __init__(self) -> None:
        global_temp_dir = tempfile.gettempdir()

        # Create a temp dir of our own, inside the global temp dir, and with a name that indicates who made it.
        self._temp_dir = tempfile.mkdtemp(dir=global_temp_dir, prefix="lumberjack-", suffix="")

        self._executors: List[BaseExecutor] = []

    def __enter__(self) -> "LumberjackController":
        return self

    def __exit__(self, *unused_args) -> None:
        self.stop()

    def _create_pipe(self):
        """Create a uniquely-named named pipe in the controller's temp directory.

        Raises:
          RuntimeError: If the platform doesn't have mkfifo.
        Returns:
          The path to the named pipe, as a string.
        """

        if not hasattr(os, "mkfifo"):
            raise RuntimeError("Platform not supported due to lack of mkfifo")

        path = os.path.join(self._temp_dir, str(uuid.uuid4()))
        readable_by_owner_only = 0o600  # Unix permission bits
        os.mkfifo(path, mode=readable_by_owner_only)

        return path

    def start(self, config, progress_callback=None) -> "LumberjackController":

        if self._executors:
            raise RuntimeError("Controller already started!")

        local_path = "{}/{}/{}".format(
            settings.TRANSCODED_VIDEOS_PATH, config.get("id"), config.get("output").get("name")
        )
        if self.is_packaging_needed(config):
            config["output"]["pipe"] = self._create_pipe()
            self.add_packagers(config, config["output"]["pipe"])

        else:
            self._executors.append(CloudUploader(local_path, config.get("output")["url"]))

        self._executors.append(FFMpegTranscoder(config, progress_callback))
        for executor in self._executors:
            executor.start()
        return self

    def is_packaging_needed(self, config):
        # If only hls output without fairplay is necessary then FFMpeg itself can be used
        if config.get("format") == JobTemplate.HLS and not config.get("drm_encryption", {}).get("fairplay", None):
            return False

        if config.get("format") in [JobTemplate.BOTH_HLS_AND_DASH, JobTemplate.DASH, JobTemplate.HLS]:
            return True

        return False

    def add_packagers(self, config, ffmpeg_output_pipe):
        local_path = "{}/{}/{}".format(
            settings.TRANSCODED_VIDEOS_PATH, config.get("id"), config.get("output").get("name")
        )
        one_to_many_pipe_writer = OneToManyPipeWriter(input_pipe=ffmpeg_output_pipe)

        if config.get("format") in [JobTemplate.BOTH_HLS_AND_DASH, JobTemplate.HLS]:
            hls_config = self.prepare_hls_config(config)
            one_to_many_pipe_writer.register_output_pipe(hls_config["output"]["pipe"])
            hls_output_path = local_path + settings.HLS_OUTPUT_PATH_PREFIX
            self._executors.append(ShakaPackager(hls_config, hls_output_path))
            self._executors.append(
                CloudUploader(hls_output_path, config.get("output")["url"] + settings.HLS_OUTPUT_PATH_PREFIX)
            )

        if config.get("format") in [JobTemplate.BOTH_HLS_AND_DASH, JobTemplate.DASH]:
            dash_config = self.prepare_dash_config(config)
            dash_output_path = local_path + settings.DASH_OUTPUT_PATH_PREFIX
            one_to_many_pipe_writer.register_output_pipe(dash_config["output"]["pipe"])
            self._executors.append(ShakaPackager(dash_config, dash_output_path))
            self._executors.append(
                CloudUploader(dash_output_path, config.get("output")["url"] + settings.DASH_OUTPUT_PATH_PREFIX)
            )

        one_to_many_pipe_writer.start()

    def prepare_hls_config(self, config):
        hls_config = copy.deepcopy(config)
        if hls_config.get("drm_encryption"):
            hls_config["encryption"] = hls_config.get("drm_encryption").get("fairplay")
        hls_config["format"] = "hls"
        hls_config["output"]["pipe"] = self._create_pipe()
        return hls_config

    def prepare_dash_config(self, config):
        dash_config = copy.deepcopy(config)
        if dash_config.get("drm_encryption"):
            dash_config["encryption"] = dash_config.get("drm_encryption").get("widevine")
        dash_config["format"] = "dash"
        dash_config["output"]["pipe"] = self._create_pipe()
        return dash_config

    def check_status(self) -> Status:
        """Checks the status of all the nodes.
        If one node is errored, this returns Errored; otherwise if one node is
        finished, this returns Finished; this only returns Running if all nodes are
        running.  If there are no nodes, this returns Finished.
        """
        if not self._executors:
            return Status.Finished

        value = max(node.check_status().value for node in self._executors)
        return Status(value)

    def is_completed(self):
        return all([executor.check_status() != Status.Running for executor in self._executors])

    def stop(self) -> None:
        """Stop all nodes."""
        status = self.check_status()
        for executor in self._executors:
            executor.stop(status)
        self._executors = []
