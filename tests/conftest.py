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
