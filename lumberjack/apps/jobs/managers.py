class VideoTranscoder:
    def __init__(self, job):
        self.job = job

    def start(self, sync=False, queue="transcoding"):
        self.job.create_outputs()
        self.job.start(sync, queue)

    def restart(self, sync=False, queue="transcoding"):
        self.job.stop()
        self.job.start(sync, queue)

    def stop(self):
        self.job.stop()
