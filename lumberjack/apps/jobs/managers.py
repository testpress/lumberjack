import copy

from apps.jobs.models import Output, Job
from celery import group
from lumberjack.celery import app

from .tasks import VideoTranscoder


class VideoTranscodeManager:
    def __init__(self, job):
        self.job = job

    def start(self):
        outputs = self.create_outputs()
        output_tasks = self.create_output_tasks(outputs)
        self.start_tasks(output_tasks)

    def restart(self):
        self.terminate_task()
        output_tasks = self.create_output_tasks(self.job.outputs.all())
        self.start_tasks(output_tasks)

    def start_tasks(self, tasks):
        job = group(tasks)
        task = job.apply_async()
        self.save_background_task_to_job(task)

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
                priority=output_settings.get("priority", 9),
            )
            output.save()
            outputs.append(output)
        return outputs

    def get_output_folder_path(self, output_settings):
        return self.job.settings["destination"] + "/" + output_settings["name"]

    def create_output_tasks(self, outputs):
        return [
            VideoTranscoder.s(job_id=self.job.id, output_id=output.id).set(
                queue="transcoding", priority=output.priority
            )
            for output in outputs
        ]

    def save_background_task_to_job(self, task):
        task.save()
        self.job.background_task_id = task.id
        self.update_job_status(Job.QUEUED)

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

    def get_job_info(self):
        return self.job.job_info
