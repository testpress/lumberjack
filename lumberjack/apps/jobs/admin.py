from django.contrib import admin
from django_object_actions import DjangoObjectActions

from apps.jobs.managers import VideoTranscodeManager
from apps.jobs.models import Job, Output


class JobAdmin(DjangoObjectActions, admin.ModelAdmin):
    def restart(self, request, obj):
        transcode_manager = VideoTranscodeManager(obj)
        transcode_manager.restart()

    restart.label = "Restart"
    restart.short_description = "Restart this job"
    change_actions = ("restart",)


admin.site.register(Job, JobAdmin)
admin.site.register(Output)
