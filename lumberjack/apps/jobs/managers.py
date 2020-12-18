import json

from apps.jobs.models import Job
from lumberjack.celery import app


class VideoTranscoder:
    def __init__(self, job):
        self.job = job

    def start(self, sync=False):
        self.job.create_outputs()
        self.start_tasks(sync)

    def restart(self, sync=False):
        self.stop()
        self.start_tasks(sync)

    def start_tasks(self, sync=False):
        self.update_job_status(Job.QUEUED)
        queue = "transcoding"
        if self.job.meta_data and json.loads(self.job.meta_data).get("queue"):
            meta_data = json.loads(self.job.meta_data)
            queue = meta_data.get("queue", queue)

        for output in self.job.outputs.all():
            output.start_task(queue, sync)

    def update_job_status(self, status):
        self.job.status = status
        self.job.save()

    def stop(self):
        if self.job.status == Job.COMPLETED:
            return

        for output in self.job.outputs.all():
            app.control.revoke(output.background_task_id, terminate=True, signal="SIGUSR1")
        self.update_job_status(Job.CANCELLED)
