import threading
import abc
import re

from apps.ffmpeg.outputs import OutputFileFactory


def convert_to_sec(time):
    h, m, s = time.split(":")
    return int(h) * 3600 + int(m) * 60 + int(s)


class Event(object):
    def __init__(self, type, data):
        self.type = type
        self.data = data


class FFmpegEvent(Event):
    PROGRESS_EVENT = "progress"
    OUTPUT_EVENT = "output"


class Observer:
    def notify(self, *args, **kwargs):
        pass

    @property
    @abc.abstractmethod
    def event_type(self):
        pass


class ProgressObserver(Observer):
    def __init__(self, progress_callback: callable):
        self.callback = progress_callback

    def notify(self, progress, **kwargs):
        if self.callback:
            self.callback(progress)

    @property
    def event_type(self):
        return FFmpegEvent.PROGRESS_EVENT


class OutputFileObserver(Observer):
    def __init__(self, url, directory):
        self.output = OutputFileFactory.create(url)
        self.directory = directory

    def notify(self, is_transcode_completed):
        self.output.save(self.directory, is_transcode_completed)

    @property
    def event_type(self):
        return FFmpegEvent.OUTPUT_EVENT


class Observable:
    def __init__(self):
        self._observers = dict()

    def register(self, observer: Observer):
        if observer.event_type in self._observers:
            observers = self._observers[observer.event_type]
            observers.append(observer)
        else:
            observers = {observer}
        self._observers[observer.event_type] = observers

    def unregister(self, observer: Observer):
        if observer.event_type in self._observers:
            self._observers[observer.event_type].remove(observer)

    def notify(self, event):
        if event.type in self._observers:
            observers = self._observers[event.type]
            for observer in observers:
                observer.notify(event.data)


class LogParser(Observable):
    def __init__(self, process):
        super().__init__()
        self.duration = 1
        self.time = 0
        self.process = process
        self.thread = threading.Thread(target=self.run)

    def run(self):
        while True:
            events = self.generate_events_from_log()
            for event in events:
                self.notify(event)
            if not events:
                self.notify_transcode_completed()
                break

    def generate_events_from_log(self):
        while True:
            events = []
            log = self.process.stdout.readline().strip()
            if self.is_stdout_finished(log):
                return events

            percentage = self.get_percentage(log)
            events.append(self.create_progress_event(percentage))

            if self.has_output_files(log):
                events.append(self.create_output_event())
            return events

    def is_stdout_finished(self, log):
        return log == "" and self.process.poll() is not None

    def notify_transcode_completed(self):
        event = self.create_output_event(is_transcode_completed=True)
        self.notify(event)

    def create_progress_event(self, percentage):
        return FFmpegEvent(FFmpegEvent.PROGRESS_EVENT, percentage)

    def create_output_event(self, is_transcode_completed=False):
        return FFmpegEvent(FFmpegEvent.OUTPUT_EVENT, is_transcode_completed)

    def get_percentage(self, log):
        self.duration = self.parse_time("Duration: ", log, self.duration)
        self.time = self.parse_time("time=", log, self.time)
        return round(self.time / self.duration * 100)

    def has_output_files(self, log):
        regex_pattern = re.compile("(Opening .* for writing)")
        return regex_pattern.search(log)

    def parse_time(self, regex, string, default):
        time = re.search("(?<=" + regex + ")\w+:\w+:\w+", string)
        return convert_to_sec(time.group(0)) if time else default

    def start(self):
        self.thread.start()

    def stop(self):
        if self.thread.is_alive():
            self.thread.join()
