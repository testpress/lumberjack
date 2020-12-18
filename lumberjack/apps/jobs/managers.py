import json

from apps.jobs.models import Job
from lumberjack.celery import app
from .tasks import VideoTranscoderTask


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
        for output in self.job.outputs.all():
            if sync:
                task = VideoTranscoderTask.apply(kwargs={"job_id": self.job.id, "output_id": output.id})
            else:
                task = VideoTranscoderTask.apply_async(kwargs={"job_id": self.job.id, "output_id": output.id})
            output.background_task_id = task.task_id
            output.save()

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

        for output in self.job.outputs.all():
            app.control.revoke(output.background_task_id, terminate=True, signal="SIGUSR1")
        self.update_job_status(Job.CANCELLED)
