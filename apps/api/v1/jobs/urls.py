from django.urls import path

from .views import CreateJobView, JobsView

urlpatterns = [path("create/", CreateJobView.as_view()), path("", JobsView.as_view())]
