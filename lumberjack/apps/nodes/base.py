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


class ProcessStatus(enum.Enum):
    Running = 0
    Finished = 1
    Errored = 2


class NodeBase(object):
    @abc.abstractmethod
    def __init__(self) -> None:
        self._process = None

    def __del__(self) -> None:
        # If the process isn't stopped by now, stop it here.  It is preferable to
        # explicitly call stop().
        self.stop(None)

    @abc.abstractmethod
    def start(self):
        """Start the subprocess.

        Should be overridden by the subclass to construct a command line, call
        self._create_process, and assign the result to self._process.
        """
        pass

    def _create_process(self, args, env={}, merge_env=True, stdout=None, stderr=None, shell=False):
        """A central point to create subprocesses, so that we can debug the
        command-line arguments.

        Args:
          args: An array of strings if shell is False, or a single string is shell
                is True; the command line of the subprocess.
          env: A dictionary of environment variables to pass to the subprocess.
          merge_env: If true, merge env with the parent process environment.
          shell: If true, args must be a single string, which will be executed as a
                 shell command.
        Returns:
          The Popen object of the subprocess.
        """
        if merge_env:
            child_env = os.environ.copy()
            child_env.update(env)
        else:
            child_env = env
        return subprocess.Popen(
            shlex.split(args),
            env=child_env,
            stdin=subprocess.DEVNULL,
            stdout=stdout,
            stderr=stderr,
            shell=shell,
            universal_newlines=True,
        )

    def check_status(self) -> ProcessStatus:
        """Returns the current ProcessStatus of the node."""
        if not self._process:
            raise ValueError("Must have a process to check")

        self._process.poll()
        if self._process.returncode is None:
            return ProcessStatus.Running

        if self._process.returncode == 0:
            return ProcessStatus.Finished
        else:
            return ProcessStatus.Errored

    def stop(self, status: Optional[ProcessStatus]) -> None:
        """Stop the subprocess if it's still running."""
        if self._process:
            # Slightly more polite than kill.  Try this first.
            self._process.terminate()

            if self.check_status() == ProcessStatus.Running:
                # If it's not dead yet, wait 1 second.
                time.sleep(1)

            if self.check_status() == ProcessStatus.Running:
                # If it's still not dead, use kill.
                self._process.kill()
                # Wait for the process to die and read its exit code.  There is no way
                # to ignore a kill signal, so this will happen quickly.  If we don't do
                # this, it can create a zombie process.
                self._process.wait()


class ThreadedNodeBase(NodeBase):
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
                self._thread_single_pass()
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
    def _thread_single_pass(self):
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


class PolitelyWaitOnFinish(NodeBase):
    """
    A mixin that makes stop() wait for the subprocess if status is Finished.
    This is as opposed to the base class behavior, in which stop() forces
    the subprocesses of a node to terminate.
    """

    def stop(self, status: Optional[ProcessStatus]) -> None:
        if self._process and status == ProcessStatus.Finished:
            try:
                print("Waiting for ", self.__class__.__name__)
                self._process.wait(timeout=300)  # 5 min timeout
            except subprocess.TimeoutExpired:
                traceback.print_exc()
        super().stop(status)
