import subprocess
import shlex

from smart_open import open

from apps.ffmpeg.command_generator import CommandGenerator
from apps.ffmpeg.input_options import InputOptionsFactory
from apps.ffmpeg.utils import mkdir
from apps.ffmpeg.monitor import (
    Observable, Monitor,
    ProgressObserver, OutputObserver, FFmpegEvent
)


class Manager:
    def __init__(self, options, monitor: callable = None):
        self.monitor = monitor
        self.options = options
        self.command = CommandGenerator(options).generate()

    def run(self):
        self.observable = Observable()
        self.create_observers()
        self.register_observers()
        self.executor = Executor(self.options)
        self.monitor = Monitor(self.executor.process, self.observable)
        self.monitor.start()
        self.executor.run()

    def create_observers(self):
        self.progress_observer = ProgressObserver(self.monitor)
        self.output_observer = OutputObserver(self.options.get("output")["url"], self.options.get("output")["local_path"])

    def register_observers(self):
        self.observable.register(FFmpegEvent.OUTPUT_EVENT, self.output_observer)
        self.observable.register(FFmpegEvent.PROGRESS_EVENT, self.progress_observer)


class Executor:
    def __init__(self, options):
        self.command = CommandGenerator(options).generate()
        self.input = options.get("input")
        output = options.get("output")
        path = "{}/{}/{}".format(output.get("local_path"), options.get("id"), output.get("name"))
        mkdir(path)
        self.start_process()

    @property
    def options(self):
        return {
            'stdin': subprocess.PIPE,
            'stdout': subprocess.PIPE,
            'stderr': subprocess.STDOUT,
            'universal_newlines': True
        }

    def run(self):
        self.read_input()
        self.process.wait()

        # self.stop_process()

    def start_process(self):
        self._process = subprocess.Popen(shlex.split(self.command), **self.options)

    def read_input(self):
        options = InputOptionsFactory.get(self.input)
        for content in open(self.input, 'rb', transport_params=options.__dict__):
            self.process.stdin.buffer.write(content)
        self.process.stdin.close()

    def stop_process(self):
        self._process.terminate()

    @property
    def process(self):
        return self._process
