from .factories import JobFactory, OutputFactory, JobTemplateFactory

from exam import fixture


class Mixin(object):
    def create_job(self, **kwargs):
        return JobFactory(**kwargs)

    @fixture
    def job(self):
        return self.create_job()

    def create_output(self, job=None, **kwargs):
        job = job or self.job
        return OutputFactory(job=job, **kwargs)

    @fixture
    def output(self):
        return self.create_output()

    def create_job_template(self):
        return JobTemplateFactory()

    @fixture
    def job_template(self):
        return self.create_job_template()
