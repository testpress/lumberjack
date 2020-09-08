from django.contrib import admin

from apps.jobs.models import Job, Output

admin.site.register(Job)
admin.site.register(Output)
