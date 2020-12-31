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
import subprocess
import traceback
import os
import shlex

from typing import Optional


class Status(enum.Enum):
    Not_Started = 0
    Running = 1
    Finished = 2
    Errored = 3


class BaseExecutor(object):
    def start(self):
        pass

    def stop(self, status: Optional[Status]):
        pass

    def check_status(self) -> Status:
        pass


class BaseProcessExecutor(BaseExecutor):
    @abc.abstractmethod
    def __init__(self) -> None:
        self._process = None

    def __del__(self) -> None:
        # If the process isn't stopped by now, stop it here.  It is preferable to
        # explicitly call stop().
        self.stop(None)

    def start(self):
        self._process = self.start_process()

    @abc.abstractmethod
    def start_process(self):
        """Start the subprocess.
        Should be overridden by the subclass to construct a command line, call
        self._create_process.
        """
        pass

    def _create_process(self, args, stdout=None, stderr=None, shell=False):
        """A central point to create subprocesses, so that we can debug the
        command-line arguments.

        Args:
          args: An array of strings if shell is False, or a single string is shell
                is True; the command line of the subprocess.
          shell: If true, args must be a single string, which will be executed as a
                 shell command.
        Returns:
          The Popen object of the subprocess.
        """

        if type(args) is str:
            command = shlex.split(args)
        else:
            command = args

        return subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=stdout,
            stderr=stderr,
            shell=shell,
            universal_newlines=True,
        )

    def check_status(self) -> Status:
        """Returns the current Status of the node."""
        if not self._process:
            raise ValueError("Must have a process to check")

        self._process.poll()
        if self._process.returncode is None:
            return Status.Running

        if self._process.returncode == 0:
            return Status.Finished
        else:
            return Status.Errored

    def stop(self, status: Optional[Status]) -> None:
        """Stop the subprocess if it's still running."""
        if self._process:
            # Slightly more polite than kill.  Try this first.
            self._process.terminate()

            if self.check_status() == Status.Running:
                # If it's not dead yet, wait 1 second.
                time.sleep(1)
        self.post_stop()

    def post_stop(self):
        pass


class BaseThreadExecutor(BaseExecutor):
    """A base class for nodes that run a thread.
    The thread repeats some callback in a background thread.
    """
    def __init__(self, thread_name: str, continue_on_exception: bool):
        super().__init__()
        self._status = Status.Not_Started
        self._thread_name = thread_name
        self._continue_on_exception = continue_on_exception
        self._thread = threading.Thread(target=self._thread_main, name=thread_name)

    def _thread_main(self) -> None:
        while self._status == Status.Running:
            try:
                self.run()
            except:
                print("Exception in", self._thread_name, "-", sys.exc_info())

                if self._continue_on_exception:
                    print("Continuing.")
                else:
                    print("Quitting.")
                    self._status = Status.Errored
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
        self._status = Status.Running
        self._thread.start()

    def stop(self, status: Optional[Status]) -> None:
        self._status = Status.Finished
        self._thread.join()
        self.post_stop()

    def post_stop(self):
        # Can be implemented to perform clean up or other functions once thread is stopped
        pass

    def check_status(self) -> Status:
        return self._status


class PolitelyWaitOnFinishMixin(BaseProcessExecutor):
    """
    A mixin that makes stop() wait for the subprocess if status is Finished.
    This is as opposed to the base class behavior, in which stop() forces
    the subprocesses of a node to terminate.
    """

    def stop(self, status: Optional[Status]) -> None:
        if self._process and status == Status.Finished:
            try:
                self._process.wait(timeout=300)  # 5 min timeout
            except subprocess.TimeoutExpired:
                traceback.print_exc()
        super().stop(status)
        self.post_stop()
