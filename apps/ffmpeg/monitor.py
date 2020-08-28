import threading
import re

from apps.ffmpeg.outputs import OutputFactory


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


class ProgressObserver(Observer):
    def __init__(self, progress_callback: callable):
        self.callback = progress_callback

    def notify(self, progress, **kwargs):
        if self.callback:
            self.callback(progress)


class OutputObserver(Observer):
    def __init__(self, url, directory):
        self.output = OutputFactory.create(url)
        self.directory = directory

    def notify(self, percentage, **kwargs):
        exclude_m3u8 = False
        if percentage < 100:
            exclude_m3u8 = True
        self.output.store(self.directory, exclude_m3u8)


class Observable:
    def __init__(self):
        self._observers = dict()

    def register(self, event_type, observer: Observer):
        if event_type in self._observers:
            observers = self._observers[event_type]
            observers.append(observer)
        else:
            observers = {observer}
        self._observers[event_type] = observers

    def unregister(self, event_type, observer: Observer):
        if event_type in self._observers:
            self._observers[event_type].remove(observer)

    def notify(self, event):
        if event.type in self._observers:
            observers = self._observers[event.type]
            for observer in observers:
                observer.notify(event.data)


class Monitor:
    def __init__(self, process, observable):
        self.duration = 1
        self.time = 0
        self.process = process
        self.observable = observable
        self.thread = threading.Thread(target=self.run)

    def run(self):
        while True:
            events = self.parse_log()
            if events:
                for event in events:
                    self.observable.notify(event)
            else:
                break

    def parse_log(self):
        while True:
            events = []
            log = self.process.stdout.readline().strip()
            if self.is_stdout_finished(log):
                return False

            percentage = self.get_percentage(log)
            events.append(self.create_progress_event(percentage))

            if self.has_output_files(log):
                events.append(self.create_output_event(percentage))
            return events

    def is_stdout_finished(self, log):
        return log == '' and self.process.poll() is not None

    def create_progress_event(self, percentage):
        return FFmpegEvent(FFmpegEvent.PROGRESS_EVENT, percentage)

    def create_output_event(self, percentage):
        return FFmpegEvent(FFmpegEvent.OUTPUT_EVENT, percentage)

    def get_percentage(self, log):
        self.duration = self.parse_time('Duration: ', log, self.duration)
        self.time = self.parse_time('time=', log, self.time)
        return round(self.time/self.duration * 100)

    def has_output_files(self, log):
        regex_pattern = re.compile("(Opening .* for writing)")
        return regex_pattern.search(log)

    def parse_time(self, regex, string, default):
        time = re.search('(?<=' + regex + ')\w+:\w+:\w+', string)
        return convert_to_sec(time.group(0)) if time else default

    def start(self):
        self.thread.start()

    def stop(self):
        if self.thread.is_alive():
            self.thread.join()
