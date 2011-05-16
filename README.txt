=======================================
Dogslow -- Django Slow Request Watchdog
=======================================


Overview
--------

Dogslow is Django watchdog middleware class that logs tracebacks of slow
requests.


Installation
------------

Install dogslow::

    $ pip install dogslow

Then add if to your list of middleware classes in your Django settings.py file::

    MIDDLEWARE_CLASSES = (
        'dogslow.WatchdogMiddleware',
        ...
    )

For best results, make it one of the first middlewares that is run.


Configuration
-------------

You can use the following configuration properties in your ``settings.py``
file to tune the watchdog::

    # Watchdog is enabled by default, to temporarily disable, set to False:
    DOGSLOW = True

    # Location where Watchdog stores its log files:
    DOGSLOW_OUTPUT = '/tmp'

    # Log requests taking longer than 25 seconds:
    DOGSLOW_TIMER = 25

    # When both specified, emails backtraces:
    DOGSLOW_EMAIL_TO = 'errors@atlassian.com'
    DOGSLOW_EMAIL_FROM = 'no-reply@atlassian.com'
