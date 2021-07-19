import pytest
import sentry_sdk
from django.conf import settings


def pytest_configure():
    settings.configure(
        SECRET_KEY="...",
        ROOT_URLCONF="tests.urls",
        MIDDLEWARE=[
            "dogslow_sentry.WatchdogMiddleware",
        ],
        TEMPLATES=[
            {
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                "DIRS": [],
                "APP_DIRS": True,
            }
        ],
    )


@pytest.fixture
def capture_events(monkeypatch):
    """
    Inspired by `capture_exceptions()` from
    https://github.com/getsentry/sentry-python/blob/master/tests/conftest.py
    SPDX License: BSD-2-Clause
    """

    def inner():
        events = []
        old_capture_event = sentry_sdk.Hub.capture_event

        def capture_event(self, event, hint=None, *args, **kwargs):
            events.append(event)
            return old_capture_event(self, event, hint=hint, *args, **kwargs)

        monkeypatch.setattr(sentry_sdk.Hub, "capture_event", capture_event)
        return events

    return inner
