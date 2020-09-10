from django.urls import path

from .views import CreateJobView, JobsView, job_info_view, cancel_job_view

urlpatterns = [
    path("create/", CreateJobView.as_view()),
    path("", JobsView.as_view()),
    path("<uuid:job_id>/", job_info_view),
    path("cancel/", cancel_job_view),
]
