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
from typing import List

from django.conf import settings

from apps.executors.base import Status, BaseExecutor
from apps.executors.cloud import CloudUploader
from apps.executors.transcoder import FFMpegTranscoder
from apps.executors.packager import ShakaPackager


class LumberjackController(object):
    def __init__(self) -> None:
        global_temp_dir = tempfile.gettempdir()

        # Create a temp dir of our own, inside the global temp dir, and with a name that indicates who made it.
        self._temp_dir = tempfile.mkdtemp(dir=global_temp_dir, prefix="shaka-live-", suffix="")

        self._executors: List[BaseExecutor] = []

    def __enter__(self) -> "LumberjackController":
        return self

    def __exit__(self, *unused_args) -> None:
        self.stop()

    def _create_pipe(self):
        """Create a uniquely-named named pipe in the node's temp directory.

        Raises:
          RuntimeError: If the platform doesn't have mkfifo.
        Returns:
          The path to the named pipe, as a string.
        """

        if not hasattr(os, "mkfifo"):
            raise RuntimeError("Platform not supported due to lack of mkfifo")

        # Since the tempfile module creates actual files, use uuid to generate a
        # filename, then call mkfifo to create the named pipe.
        unique_name = str(uuid.uuid4())
        path = os.path.join(self._temp_dir, unique_name)

        readable_by_owner_only = 0o600  # Unix permission bits
        os.mkfifo(path, mode=readable_by_owner_only)

        return path

    def start(self, config, progress_callback=None) -> "LumberjackController":

        if self._executors:
            raise RuntimeError("Controller already started!")

        local_path = "{}/{}/{}".format(
            settings.TRANSCODED_VIDEOS_PATH, config.get("id"), config.get("output").get("name")
        )
        # Add shaka packager only if encryption has drm
        if config.get("format") in ["adaptive", "hls", "dash"]:
            config["output"]["pipe"] = self._create_pipe()
            self._executors.append(ShakaPackager(config, local_path))

        self._executors.append(CloudUploader(local_path, config.get("output")["url"]))
        self._executors.append(FFMpegTranscoder(config, progress_callback))
        for executor in self._executors:
            executor.start()
        return self

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

    def stop(self) -> None:
        """Stop all nodes."""
        status = self.check_status()
        for executor in self._executors:
            executor.stop(status)
        self._executors = []
