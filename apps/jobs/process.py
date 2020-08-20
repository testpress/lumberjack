import logging
import subprocess
import shlex
import threading

from .utils import get_time


class FFMpegProcess(object):
    out = None
    err = None
    INPUT_BUFFER_SIZE = 32000000

    def __init__(self, commands: str, monitor: callable = None, **kwargs):
        self.input = kwargs.get("input")
        self.output = kwargs.get("output")
        self.process = subprocess.Popen(shlex.split(commands), **self.options)
        self.monitor = monitor

    @property
    def options(self):
        return {
            'stdin': subprocess.PIPE,
            'stdout': subprocess.PIPE,
            'stderr': subprocess.STDOUT,
            'universal_newlines': True
        }

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.process.kill()

    def _monitor(self):
        duration = 1
        time = 0
        log = []

        while True:
            line = self.process.stdout.readline().strip()
            if line == '' and self.process.poll() is not None:
                break

            if line != '':
                log += [line]

            if callable(self.monitor):
                if type(line) == str:
                    duration = get_time('Duration: ', line, duration)
                    time = get_time('time=', line, time)
                    self.monitor(line, duration, time, self.process)

        FFMpegProcess.out = log

    def start_monitoring(self):
        self.thread = threading.Thread(target=self._monitor)
        self.thread.start()

    def stop_thread(self):
        self.thread.join()

        if self.thread.is_alive():
            self.process.terminate()
            self.thread.join()
            error = 'Timeout! exceeded the timeout of seconds.'
            logging.error(error)
            raise RuntimeError(error)

    def process_input(self):
        curr = 0
        while curr < self.input.size:
            self.process.stdin.buffer.write(self.input.read(self.INPUT_BUFFER_SIZE))
            curr += self.INPUT_BUFFER_SIZE
        self.process.stdin.close()

    def run(self):
        self.start_monitoring()
        self.process_input()
        self.stop_thread()

        if self.process.poll():
            error = str(FFMpegProcess.err) if FFMpegProcess.err else str(FFMpegProcess.out)
            raise RuntimeError('Error Occurred: ', error)

        return FFMpegProcess.out, FFMpegProcess.err
