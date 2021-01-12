from django.conf import settings


def pytest_configure():
    settings.configure(
        SECRET_KEY="...",
        ROOT_URLCONF="tests.urls",
        # Django < 2.0
        MIDDLEWARE_CLASSES=[
            "dogslow_sentry.WatchdogMiddleware",
        ],
        # Django >= 2.0
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
