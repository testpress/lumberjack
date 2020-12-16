import json

import requests
from celery import Task
from django.core.serializers.json import DjangoJSONEncoder

from lumberjack.celery import app
from .runnables import VideoTranscoderRunnable, ManifestGeneratorRunnable


class LumberjackTask(Task):
    runnable = None

    def run(self, *args, **kwargs):
        self.runnable(*args, **kwargs, task_id=self.request.id).run()


class VideoTranscoderTask(LumberjackTask):
    runnable = VideoTranscoderRunnable


VideoTranscoderTask = app.register_task(VideoTranscoderTask())


class ManifestGeneratorTask(LumberjackTask):
    runnable = ManifestGeneratorRunnable


ManifestGeneratorTask = app.register_task(ManifestGeneratorTask())


class PostDataToWebhookTask(LumberjackTask):
    def run(self, data, url):
        data_json = json.dumps(data, cls=DjangoJSONEncoder)

        try:
            requests.post(url, data=data_json, headers={"Content-Type": "application/json"})
        except requests.ConnectionError:
            self.retry()


PostDataToWebhookTask = app.register_task(PostDataToWebhookTask())
