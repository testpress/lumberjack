from rest_framework.generics import CreateAPIView, ListAPIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view

from django.shortcuts import get_object_or_404

from apps.jobs.models import Job
from .serializers import JobSerializer
from apps.jobs.managers import VideoTranscoder


class CreateJobView(CreateAPIView):
    queryset = Job.objects.all()
    serializer_class = JobSerializer

    def perform_create(self, serializer):
        job = serializer.save()
        VideoTranscoder(job).start()


class JobsView(ListAPIView):
    queryset = Job.objects.all()
    serializer_class = JobSerializer


@api_view(["GET"])
def job_info_view(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    return Response(data=JobSerializer(instance=job).data, status=status.HTTP_200_OK)


@api_view(["POST"])
def cancel_job_view(request):
    job_id = request.data["job_id"]
    job = get_object_or_404(Job, id=job_id)
    VideoTranscoder(job).stop()
    return Response(status=status.HTTP_200_OK)


@api_view(["POST"])
def restart_job_view(request):
    job_id = request.data["job_id"]
    job = get_object_or_404(Job, id=job_id)
    VideoTranscoder(job).restart()
    return Response(status=status.HTTP_200_OK)
