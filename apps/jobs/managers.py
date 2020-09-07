from celery.result import AsyncResult
from celery import chord

from .tasks import VideoTranscoder, ManifestGenerator
from apps.jobs.models import Output, Job


class VideoTranscodeManager:
    def __init__(self, job):
        self.job = job

    def start(self):
        output_tasks = self.create_output_tasks()
        task = chord(output_tasks)(ManifestGenerator.s(job_id=self.job.id))
        self.update_job_status_and_task_id(task.task_id)

    def create_outputs(self):
        job_settings = self.job.settings
        outputs = []
        for output_settings in job_settings.pop("outputs"):
            output_settings["url"] = job_settings["destination"] + "/" + output_settings["name"]
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

    def create_output_tasks(self):
        outputs = self.create_outputs()
        return [VideoTranscoder.s(job_id=self.job.id, output_id=output.id) for output in outputs]

    def update_job_status_and_task_id(self, task_id):
        self.job.background_task_id = task_id
        self.update_job_status(Job.QUEUED)

    def update_job_status(self, status):
        self.job.status = status
        self.job.save()

    def stop(self):
        if self.job.status == Job.COMPLETED:
            return

        AsyncResult(self.job.background_task_id).revoke(terminate=True)
        self.update_job_status(Job.CANCELLED)

    def get_job_info(self):
        return self.job.job_info
