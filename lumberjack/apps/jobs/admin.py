from django.contrib import admin
from django_object_actions import DjangoObjectActions

from apps.jobs.managers import VideoTranscoder
from apps.jobs.models import Job, Output


def stop_tasks(modeladmin, request, queryset):
    for job in queryset:
        transcode_manager = VideoTranscoder(job)
        transcode_manager.stop()


stop_tasks.short_description = "Stop selected jobs"


def restart_tasks(modeladmin, request, queryset):
    for job in queryset:
        transcode_manager = VideoTranscoder(job)
        transcode_manager.restart()


restart_tasks.short_description = "Restart selected jobs"


class JobAdmin(DjangoObjectActions, admin.ModelAdmin):
    def restart(self, request, obj):
        transcode_manager = VideoTranscoder(obj)
        transcode_manager.restart()

    def get_status(self, obj):
        return obj.get_status_display()

    get_status.short_description = "Status"

    restart.label = "Restart"
    restart.short_description = "Restart this job"
    change_actions = ("restart",)
    actions = [stop_tasks, restart_tasks]

    search_fields = ["id"]
    list_filter = ["status", "template"]
    list_display = ["id", "get_status", "progress", "created", "start_time", "end_time"]


class OutputAdmin(admin.ModelAdmin):
    def get_status(self, obj):
        return obj.get_status_display()

    get_status.short_description = "Status"

    search_fields = ["job__id"]
    list_filter = ["status"]
    list_display = ["name", "job_id", "get_status", "progress", "created", "start_time", "end_time"]


admin.site.register(Job, JobAdmin)
admin.site.register(Output, OutputAdmin)
