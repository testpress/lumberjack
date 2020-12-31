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
import abc
import enum
import sys
import threading
import time

from typing import Optional


class ProcessStatus(enum.Enum):
    Running = 0
    Finished = 1
    Errored = 2


class BaseThreadExecutor(object):
    """A base class for nodes that run a thread.
    The thread repeats some callback in a background thread.
    """

    def __init__(self, thread_name: str, continue_on_exception: bool):
        super().__init__()
        self._status = ProcessStatus.Finished
        self._thread_name = thread_name
        self._continue_on_exception = continue_on_exception
        self._thread = threading.Thread(target=self._thread_main, name=thread_name)

    def _thread_main(self) -> None:
        while self._status == ProcessStatus.Running:
            try:
                self.run()
            except:
                print("Exception in", self._thread_name, "-", sys.exc_info())

                if self._continue_on_exception:
                    print("Continuing.")
                else:
                    print("Quitting.")
                    self._status = ProcessStatus.Errored
                    return

            # Yield time to other threads.
            time.sleep(1)

    @abc.abstractmethod
    def run(self):
        """Runs a single step of the thread loop.
        This is implemented by subclasses to do whatever it is they do.  It will be
        called repeatedly by the base class from the node's background thread.  If
        this method raises an exception, the behavior depends on the
        continue_on_exception argument in the constructor.  If
        continue_on_exception is true, the the thread will continue.  Otherwise, an
        exception will stop the thread and therefore the node.
        """
        pass

    def start(self) -> None:
        self._status = ProcessStatus.Running
        self._thread.start()

    def stop(self, status: Optional[ProcessStatus]) -> None:
        self._status = ProcessStatus.Finished
        self._thread.join()

    def check_status(self) -> ProcessStatus:
        return self._status
