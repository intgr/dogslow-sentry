===============
Django Watchdog
===============


Overview
--------

Django Watchdog is a Django middleware class that logs tracebacks of slow
requests.


Installation
------------

Install django_middleware::

    $ pip install django_middleware

Then add if to your list of middleware classes in your Django settings.py file::

    MIDDLEWARE_CLASSES = (
        'django_watchdog.WatchdogMiddleware',
        ...
    )

For best results, make it one of the first middlewares that is run.


Configuration
-------------

You can use the following configuration properties in your ``settings.py``
file to tune the watchdog::

    # Watchdog is enabled by default, to temporarily disable, set to False:
    DJANGO_WATCHDOG = True

    # Location where Watchdog stores its log files:
    DJANGO_WATCHDOG_OUTPUT = '/tmp'

    # Log requests taking longer than 25 seconds:
    DJANGO_WATCHDOG_TIMER = 25

    # When both specified, emails backtraces:
    DJANGO_WATCHDOG_EMAIL_TO = 'errors@atlassian.com'
    DJANGO_WATCHDOG_EMAIL_FROM = 'no-reply@atlassian.com'
