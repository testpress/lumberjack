class VideoTranscoder:
    def __init__(self, job):
        self.job = job

    def start(self, sync=False):
        self.job.create_outputs()
        self.job.start_trascoding(sync)

    def restart(self, sync=False):
        self.job.stop()
        self.job.start_trascoding(sync)

    def stop(self):
        self.job.stop()
