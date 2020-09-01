from .factories import JobFactory, OutputFactory

from exam import fixture


class Mixin(object):
    def create_job(self):
        return JobFactory()

    @fixture
    def job(self):
        return self.create_job()

    def create_output(self, job=None):
        job = job or self.job
        return OutputFactory(job=job)

    @fixture
    def output(self):
        return self.create_output()
