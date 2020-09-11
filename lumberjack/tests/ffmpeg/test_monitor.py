from django.test import SimpleTestCase

from apps.ffmpeg.event_source import EventSource, FFmpegEvent, Observer, ProgressObserver
from .utils import ProcessMock


class ObserverMock(Observer):
    def __init__(self, event_type):
        self.called = False
        self.type = event_type

    def notify(self, *args, **kwargs):
        self.called = True

    @property
    def event_type(self):
        return self.type


class TestMonitor(SimpleTestCase):
    def test_observer_should_get_called_for_correct_event(self):
        self.observer = ObserverMock(FFmpegEvent.PROGRESS_EVENT)
        event_source = EventSource(ProcessMock())
        event_source.register(self.observer)
        event_source.run()

        self.assertTrue(self.observer.called)

    def test_output_event_should_get_triggered_once_log_is_finished(self):
        self.output_event_observer = ObserverMock(FFmpegEvent.OUTPUT_EVENT)
        event_source = EventSource(ProcessMock())
        event_source.register(self.output_event_observer)
        event_source.run()

        self.assertTrue(self.output_event_observer.called)


class TestProgressObserver(SimpleTestCase):
    def setUp(self) -> None:
        self.progress = 0

    def callback(self, progress):
        self.progress = progress

    def test_progress_observer_should_call_callback_on_notify(self):
        observer = ProgressObserver(self.callback)
        observer.notify(20)

        self.assertEqual(20, self.progress)
