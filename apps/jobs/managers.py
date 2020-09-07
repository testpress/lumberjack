from celery.result import AsyncResult
from celery import chord

from .tasks import VideoTranscoder, ManifestGenerator
from apps.jobs.models import Output


class VideoTranscodeManager:
    def __init__(self, job):
        self.job = job

    def start(self):
        tasks = []
        outputs = self.create_outputs()
        for output in outputs:
            tasks.append(VideoTranscoder.s(job_id=self.job.id, output_id=output.id))
        task = chord(tasks, ManifestGenerator.s(job_id=self.job.id)).apply_async()
        self.job.background_task_id = task.task_id
        self.job.save()

    def create_outputs(self):
        job_settings = self.job.settings
        outputs = []
        for output_settings in job_settings.get("outputs"):
            settings = self.job.settings
            output_settings["url"] = settings["destination"] + "/" + output_settings["name"]
            del settings["outputs"]
            settings["output"] = output_settings

            output = Output(
                name=output_settings["name"],
                video_encoder=output_settings["video"]["codec"],
                video_bitrate=output_settings["video"]["bitrate"],
                video_preset=output_settings["video"]["preset"],
                audio_encoder=output_settings["audio"]["codec"],
                audio_bitrate=output_settings["audio"]["bitrate"],
                width=output_settings["video"]["width"],
                height=output_settings["video"]["height"],
                settings=settings,
                job=self.job,
            )
            output.save()
            outputs.append(outputs)
        return outputs

    def stop(self):
        AsyncResult(self.job.background_task_id).revoke(terminate=True)

    def get_job_info(self):
        return self.job.job_info
