import subprocess
import shlex

from sentry_sdk import configure_scope, capture_message

from django.conf import settings

from apps.ffmpeg.command_generator import CommandGenerator
from apps.ffmpeg.utils import mkdir
from apps.ffmpeg.log_parser import LogParser, ProgressObserver


class FFMpegManager:
    def __init__(self, options, monitor: callable = None):
        self.monitor = monitor
        self.options = options
        self.command = CommandGenerator(options).generate()
        self.local_path = "{}/{}/{}".format(
            settings.TRANSCODED_VIDEOS_PATH, options.get("id"), options.get("output").get("name")
        )

    def run(self):
        self.create_observers()
        self.executor = Executor(self.options)
        self.log_parser = LogParser(self.executor.process)
        self.register_observers()
        self.log_parser.start()
        self.executor.run()

    def stop(self):
        self.executor.stop_process()

    def create_observers(self):
        self.progress_observer = ProgressObserver(self.monitor)

    def register_observers(self):
        self.event_source.register(self.progress_observer)


class Executor:
    def __init__(self, options):
        self.command = CommandGenerator(options).generate()
        self.input = options.get("input")
        output = options.get("output")
        path = "{}/{}/{}".format(settings.TRANSCODED_VIDEOS_PATH, options.get("id"), output.get("name"))
        mkdir(path)
        self.start_process()

    @property
    def options(self):
        return {
            "stdout": subprocess.PIPE,
            "stderr": subprocess.STDOUT,
            "universal_newlines": True,
        }

    def run(self):
        self.process.wait()
        if self.process.returncode != 0:
            error = "\n".join(self.process.stdout.readlines())
            self.stop_process()
            raise FFMpegException(error)
        self.stop_process()
        if self.is_process_running():
            self.log_process_details_to_sentry()

    def is_process_running(self):
        return self.process.poll() is None

    def log_process_details_to_sentry(self):
        with configure_scope() as scope:
            scope.set_extra("FFMpeg Command", self.command)
            scope.set_extra("Process Return code", self.process.returncode)
            scope.set_extra("Process PID", self.process.pid)
            capture_message("FFMpeg process Not terminated")

    def start_process(self):
        self._process = subprocess.Popen(shlex.split(self.command), **self.options)

    def stop_process(self):
        self._process.terminate()

    @property
    def process(self):
        return self._process


class FFMpegException(Exception):
    pass
