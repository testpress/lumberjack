import copy
import json

from celery import chord, group

from .tasks import VideoTranscoderTask, ManifestGeneratorTask
from apps.jobs.models import Output, Job
from lumberjack.celery import app


class VideoTranscoder:
    def __init__(self, job):
        self.job = job

    def start(self, sync=False):
        outputs = self.create_outputs()
        output_tasks = self.create_output_tasks(outputs)
        self.start_tasks(output_tasks, sync)

    def restart(self, sync=False):
        self.terminate_task()
        print("Hello")
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

    def create_outputs(self):
        job_settings = copy.deepcopy(self.job.settings)
        outputs = []
        for output_settings in job_settings.pop("outputs"):
            output_settings["url"] = self.get_output_folder_path(output_settings)
            job_settings["output"] = output_settings

            output = Output(
                name=output_settings["name"],
                video_encoder=output_settings["video"]["codec"],
                video_bitrate=output_settings["video"]["bitrate"],
                video_preset=output_settings["video"]["preset"],
                audio_encoder=output_settings["audio"]["codec"],
                audio_bitrate=output_settings["audio"]["bitrate"],
                width=output_settings["video"]["width"],
                height=output_settings["video"]["height"],
                settings=job_settings,
                job=self.job,
            )
            output.save()
            outputs.append(output)
        return outputs

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
