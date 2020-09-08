from django.contrib import admin

from apps.presets.models import JobTemplate, OutputPreset

admin.site.register(JobTemplate)


class OutputPresetAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if obj and obj.job_template:
            obj.job_template.populate_settings()
            obj.job_template.save()


admin.site.register(OutputPreset, OutputPresetAdmin)
