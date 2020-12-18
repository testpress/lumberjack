import json

from celery import group

from apps.jobs.models import Job
from lumberjack.celery import app
from .tasks import VideoTranscoderTask


class VideoTranscoder:
    def __init__(self, job):
        self.job = job

    def start(self, sync=False):
        outputs = self.job.create_outputs()
        output_tasks = self.create_output_tasks(outputs)
        self.start_tasks(output_tasks, sync)

    def restart(self, sync=False):
        self.terminate_task()
        output_tasks = self.create_output_tasks(self.job.outputs.all())
        self.start_tasks(output_tasks, sync)

    def start_tasks(self, tasks, sync=False):
        self.update_job_status(Job.QUEUED)
        if sync:
            task = group(tasks).apply()
        else:
            task = group(tasks).apply_async()
            task.save()
        self.job.background_task_id = task.id
        self.job.save(update_fields=["background_task_id"])

    def get_output_folder_path(self, output_settings):
        return self.job.settings["destination"] + "/" + output_settings["name"]

    def create_output_tasks(self, outputs):
        if self.job.meta_data and json.loads(self.job.meta_data).get("queue"):
            meta_data = json.loads(self.job.meta_data)
            return [
                VideoTranscoderTask.s(job_id=self.job.id, output_id=output.id).set(queue=meta_data.get("queue"))
                for output in outputs
            ]
        return [VideoTranscoderTask.s(job_id=self.job.id, output_id=output.id) for output in outputs]

    def update_job_status(self, status):
        self.job.status = status
        self.job.save()

    def stop(self):
        if self.job.status == Job.COMPLETED:
            return

        self.update_job_status(Job.CANCELLED)
        self.terminate_task()

    def terminate_task(self):
        task = app.GroupResult.restore(str(self.job.background_task_id))
        if task:
            task.revoke(terminate=True, signal="SIGUSR1")
