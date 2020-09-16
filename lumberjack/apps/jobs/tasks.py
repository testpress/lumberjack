import json

import requests
from celery import Task
from django.core.serializers.json import DjangoJSONEncoder

from lumberjack.celery import app
from .runnables import VideoTranscoderRunnable, ManifestGeneratorRunnable


class CeleryTask(Task):
    runnable = None

    def run(self, *args, **kwargs):
        self.runnable(*args, **kwargs).run()


class VideoTranscoder(CeleryTask):
    runnable = VideoTranscoderRunnable


VideoTranscoder = app.register_task(VideoTranscoder())


class ManifestGenerator(CeleryTask):
    runnable = ManifestGeneratorRunnable


ManifestGenerator = app.register_task(ManifestGenerator())


class PostDataToWebhookTask(CeleryTask):
    def run(self, data, url):
        data_json = json.dumps(data, cls=DjangoJSONEncoder)

        try:
            requests.post(url, data=data_json, headers={"Content-Type": "application/json"})
        except requests.ConnectionError:
            self.retry()


PostDataToWebhookTask = app.register_task(PostDataToWebhookTask())
