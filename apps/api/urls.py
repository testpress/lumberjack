from django.urls import path, include

urlpatterns = [
    path("v1/", include(("apps.api.v1.urls", "v1"), namespace="v1")),
]
