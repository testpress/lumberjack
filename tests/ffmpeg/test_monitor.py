from django.test import SimpleTestCase

from apps.ffmpeg.monitor import Monitor, Observable, FFmpegEvent, Observer, ProgressObserver
from .utils import ProcessMock


class ProgressObserverMock(Observer):
    def __init__(self):
        self.called = False

    def notify(self, *args, **kwargs):
        self.called = True


class TestMonitor(SimpleTestCase):
    def test_observer_should_get_called_for_correct_event(self):
        self.observer = ProgressObserverMock()
        self.observable = Observable()
        self.observable.register(FFmpegEvent.PROGRESS_EVENT, self.observer)
        monitor = Monitor(ProcessMock(), self.observable)
        monitor.run()

        self.assertTrue(self.observer.called)

    def test_observer_should_not_get_called_for_incorrect_event(self):
        self.observer = ProgressObserverMock()
        self.observable = Observable()
        self.observable.register(FFmpegEvent.OUTPUT_EVENT, self.observer)
        monitor = Monitor(ProcessMock(), self.observable)
        monitor.run()

        self.assertFalse(self.observer.called)


class TestProgressObserver(SimpleTestCase):
    def setUp(self) -> None:
        self.progress = 0

    def callback(self, progress):
        self.progress = progress

    def test_progress_observer_should_call_callback_on_notify(self):
        observer = ProgressObserver(self.callback)
        observer.notify(20)

        self.assertEqual(20, self.progress)
