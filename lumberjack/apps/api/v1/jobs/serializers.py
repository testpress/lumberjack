from rest_framework import serializers

from apps.jobs.models import Job


class JobSerializer(serializers.ModelSerializer):
    webhook_url = serializers.URLField(required=False, allow_blank=True, allow_null=True)
    encryption_key = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    key_url = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def validate(self, attrs):
        if not attrs.get("template") and not attrs.get("settings"):
            raise serializers.ValidationError("Must include either Job Settings or Template")
        return attrs

    class Meta:
        model = Job
        fields = ["template", "settings", "input_url", "output_url", "webhook_url", "encryption_key", "key_url"]