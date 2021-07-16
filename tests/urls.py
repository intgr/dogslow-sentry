import time

from django.http import HttpResponse
from django.urls import re_path


def okay_view(request):
    return HttpResponse("OKAY", status=200, content_type="text/plain")


def slow_view(request):
    time.sleep(1)
    return HttpResponse("SLOW", status=200, content_type="text/plain")


urlpatterns = [
    re_path(r"^$", okay_view),
    re_path(r"^slow$", slow_view),
]
