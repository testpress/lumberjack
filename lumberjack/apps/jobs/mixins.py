class JobNotifierMixin:
    def notify_webhook(self):
        from apps.api.v1.jobs.serializers import JobSerializer
        from .tasks import PostDataToWebhookTask

        if not self.webhook_url:
            return

        PostDataToWebhookTask.apply_async(args=(JobSerializer(instance=self).data, self.webhook_url))
