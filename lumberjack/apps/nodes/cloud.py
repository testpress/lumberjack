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

from typing import Optional

from apps.ffmpeg.outputs import OutputFactory
from .base import ProcessStatus, ThreadedNodeBase


class CloudNode(ThreadedNodeBase):
    def __init__(self, input_dir: str, url: str):
        super().__init__(thread_name="cloud", continue_on_exception=True)
        self._input_dir: str = input_dir
        self.url: str = url
        self.output = OutputFactory.create(self.url)

    def _thread_single_pass(self):
        self.output.save(self._input_dir, is_transcode_completed=self._status == ProcessStatus.Finished)

    def stop(self, status: Optional[ProcessStatus]) -> None:
        super().stop(status)
        # Perform uploading once at last to upload final manifest file.
        self._thread_single_pass()
