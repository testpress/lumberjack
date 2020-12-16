from django.urls import path

from .views import CreateJobView, JobsView, job_info_view, cancel_job_view, restart_job_view, clean_outputs_view

urlpatterns = [
    path("create/", CreateJobView.as_view()),
    path("", JobsView.as_view()),
    path("<uuid:job_id>/", job_info_view),
    path("cancel/", cancel_job_view),
    path("restart/", restart_job_view),
    path("clean/", clean_outputs_view),
]
