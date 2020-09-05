class JobNotifierMixin:
    def notify_webhook(self):
        from .tasks import PostDataToWebhookTask

        PostDataToWebhookTask.apply_async(args=(self.job_info, self.webhook_url))
