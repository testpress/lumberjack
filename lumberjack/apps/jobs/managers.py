class VideoTranscoder:
    def __init__(self, job):
        self.job = job

    def start(self, sync=False):
        self.job.create_outputs()
        self.job.start(sync)

    def restart(self, sync=False):
        self.job.stop()
        self.job.start(sync)

    def stop(self):
        self.job.stop()
