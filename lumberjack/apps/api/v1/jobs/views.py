from rest_framework.generics import CreateAPIView, ListAPIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view

from django.shortcuts import get_object_or_404

from apps.jobs.models import Job
from .serializers import JobSerializer
from apps.jobs.managers import VideoTranscodeManager


class CreateJobView(CreateAPIView):
    queryset = Job.objects.all()
    serializer_class = JobSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        self.start_transcoding()
        return Response(status=status.HTTP_201_CREATED, data=self.job.job_info)

    def perform_create(self, serializer):
        self.job = serializer.save()
        self.job.populate_settings()
        self.job.save()

    def start_transcoding(self):
        transcode_manager = VideoTranscodeManager(self.job)
        transcode_manager.start()


class JobsView(ListAPIView):
    queryset = Job.objects.all()
    serializer_class = JobSerializer


@api_view(["GET"])
def job_info_view(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    transcode_manager = VideoTranscodeManager(job)
    return Response(data=transcode_manager.get_job_info(), status=status.HTTP_200_OK)


@api_view(["POST"])
def cancel_job_view(request):
    job_id = request.data["job_id"]
    job = get_object_or_404(Job, id=job_id)
    transcode_manager = VideoTranscodeManager(job)
    transcode_manager.stop()
    return Response(status=status.HTTP_200_OK)
