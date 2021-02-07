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

"""A module that pushes input to ffmpeg to transcode into various formats."""

import subprocess

from django.conf import settings

from apps.ffmpeg.command_generator import CommandGenerator
from apps.ffmpeg.log_parser import LogParser, ProgressObserver
from apps.ffmpeg.utils import mkdir
from .base import PolitelyWaitOnFinishExecutor


class FFMpegTranscoder(PolitelyWaitOnFinishExecutor):
    STDOUT = subprocess.PIPE
    STDERR = subprocess.STDOUT

    def __init__(self, config, progress_callback=None, command=None):
        super().__init__()
        self.config = config
        self.progress_observer = progress_callback
        self.command = command or CommandGenerator(config).generate()
        self.event_source = None

    def pre_start(self):
        self.create_output_folder()

    def get_process_command(self):
        return self.command

    def post_start(self):
        self.event_source = LogParser(self._process)
        self.register_observers()
        self.event_source.start()

    def create_output_folder(self):
        output = self.config.get("output")
        path = "{}/{}/{}".format(settings.TRANSCODED_VIDEOS_PATH, self.config.get("id"), output.get("name"))
        mkdir(path)

    def post_stop(self):
        if self.event_source:
            self.event_source.stop()

    def register_observers(self):
        if self.progress_observer:
            observer = ProgressObserver(self.progress_observer)
            self.event_source.register(observer)
