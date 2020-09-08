from django.urls import path, include

urlpatterns = [
    path("jobs/", include(("apps.api.v1.jobs.urls", "jobs"), namespace="jobs")),
]
