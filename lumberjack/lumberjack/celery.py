from __future__ import absolute_import, unicode_literals

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "lumberjack.settings")
app = Celery("lumberjack")

app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks()

app.conf.broker_transport_options = {
    "queue_order_strategy": "priority",
}
app.conf.worker_prefetch_multiplier = 1
