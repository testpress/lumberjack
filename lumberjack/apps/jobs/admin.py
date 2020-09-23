from django.contrib import admin
from django_object_actions import DjangoObjectActions

from apps.jobs.managers import VideoTranscodeManager
from apps.jobs.models import Job, Output


def stop_tasks(modeladmin, request, queryset):
    for job in queryset:
        transcode_manager = VideoTranscodeManager(job)
        transcode_manager.stop()


stop_tasks.short_description = "Stop selected jobs"


class JobAdmin(DjangoObjectActions, admin.ModelAdmin):
    def restart(self, request, obj):
        transcode_manager = VideoTranscodeManager(obj)
        transcode_manager.restart()

    restart.label = "Restart"
    restart.short_description = "Restart this job"
    change_actions = ("restart",)
    actions = [stop_tasks]

    search_fields = ["id"]
    list_filter = ["status", "template"]


class OutputAdmin(admin.ModelAdmin):
    search_fields = ["job__id"]
    list_filter = ["status"]


admin.site.register(Job, JobAdmin)
admin.site.register(Output, OutputAdmin)
