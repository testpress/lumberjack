import subprocess
import shlex

from django.conf import settings

from apps.ffmpeg.command_generator import CommandGenerator
from apps.ffmpeg.utils import mkdir
from apps.ffmpeg.event_source import EventSource, ProgressObserver, OutputObserver


class Manager:
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
        self.event_source = EventSource(self.executor.process)
        self.register_observers()
        self.event_source.start()
        self.executor.run()

    def create_observers(self):
        self.progress_observer = ProgressObserver(self.monitor)
        self.output_observer = OutputObserver(self.options.get("output")["url"], self.local_path)

    def register_observers(self):
        self.event_source.register(self.output_observer)
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
            "stderr": subprocess.PIPE,
            "universal_newlines": True,
        }

    def run(self):
        self.process.wait()
        if self.process.returncode != 0:
            error = "\n".join(self.process.stderr.readlines())
            raise Exception(error)
        self.stop_process()

    def start_process(self):
        self._process = subprocess.Popen(shlex.split(self.command), **self.options)

    def stop_process(self):
        self._process.terminate()

    @property
    def process(self):
        return self._process
