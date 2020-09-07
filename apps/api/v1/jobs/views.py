from rest_framework.generics import CreateAPIView, ListAPIView
from rest_framework.response import Response
from rest_framework import status

from apps.jobs.models import Job
from .serializers import JobSerializer
from apps.jobs.managers import VideoTranscodeManager


class CreateJobView(CreateAPIView):
    queryset = Job.objects.all()
    serializer_class = JobSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        job = serializer.save()
        job.populate_settings()
        job.save()
        transcode_manager = VideoTranscodeManager(job)
        transcode_manager.start()
        return Response(status=status.HTTP_201_CREATED)


class JobsView(ListAPIView):
    queryset = Job.objects.all()
    serializer_class = JobSerializer
