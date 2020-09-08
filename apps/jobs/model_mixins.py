class JobNotifierMixin:
    def notify_webhook(self):
        from .tasks import PostDataToWebhookTask

        if not self.webhook_url:
            return

        PostDataToWebhookTask.apply_async(args=(self.job_info, self.webhook_url))
