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
from typing import List

from django.conf import settings

from .base import ExecutorStatus, BaseExecutor
from .cloud import CloudUploader


class MainTranscodingExecutor(object):
    def __init__(self) -> None:
        self._nodes: List[BaseExecutor]  = []

    def __enter__(self) -> "MainTranscodingExecutor":
        return self

    def __exit__(self, *unused_args) -> None:
        self.stop()

    def start(self, config) -> "MainTranscodingExecutor":
        local_path = "{}/{}/{}".format(
            settings.TRANSCODED_VIDEOS_PATH, config.get("id"), config.get("output").get("name")
        )
        self._nodes.append(CloudUploader(local_path, config.get("output")["url"]))
        for node in self._nodes:
            node.start()
        return self

    def check_status(self) -> ExecutorStatus:
        """Checks the status of all the nodes.
        If one node is errored, this returns Errored; otherwise if one node is
        finished, this returns Finished; this only returns Running if all nodes are
        running.  If there are no nodes, this returns Finished.
        """
        if not self._nodes:
            return ExecutorStatus.Finished

        value = max(node.check_status().value for node in self._nodes)
        return ExecutorStatus(value)

    def stop(self) -> None:
        """Stop all nodes."""
        status = self.check_status()
        for node in self._nodes:
            node.stop(status)
        self._nodes = []
