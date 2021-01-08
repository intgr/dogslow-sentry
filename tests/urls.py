import time

from django.http import HttpResponse
from django.conf.urls import url


def okay_view(request):
    return HttpResponse("OKAY", status=200, content_type="text/plain")


def slow_view(request):
    time.sleep(1)
    return HttpResponse("SLOW", status=200, content_type="text/plain")


urlpatterns = [
    url(r"^$", okay_view),
    url(r"^slow$", slow_view),
]
