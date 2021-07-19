==============================================
Dogslow-Sentry -- Django Slow Request Watchdog
==============================================

|PyPI version badge|

.. |PyPI version badge| image:: https://badge.fury.io/py/dogslow-sentry.svg
   :target: https://pypi.org/project/dogslow-sentry/

Overview
--------

Dogslow is a Django watchdog middleware that logs tracebacks of slow
requests. Dogslow-sentry requires Python 3.7+, Django 2.2+.

It started as an `internal project inside Bitbucket`_ to help trace
operational problems.

In 2021, the dogslow-sentry fork was created to add Sentry-specific information
to reports, like full stack trace, request information, fingerprint for issue
grouping, breadcrumbs, etc.

.. _internal project inside Bitbucket: http://blog.bitbucket.org/2011/05/17/tracking-slow-requests-with-dogslow/


Installation
------------

Install dogslow-sentry::

    $ pip install dogslow-sentry

Then add ``dogslow_sentry.WatchdogMiddleware`` to your Django settings file::

    MIDDLEWARE = [
        'dogslow_sentry.WatchdogMiddleware',
        ...
    ]

For best results, make it one of the first middlewares that is run.


Configuration
-------------

Naturally, dogslow-sentry expects a `working Sentry configuration for Django`_.

.. _working Sentry configuration for Django: https://docs.sentry.io/platforms/python/guides/django/

You can use the following configuration in your ``settings.py``
file to tune the watchdog::

    # Watchdog is enabled by default, to temporarily disable, set to False:
    DOGSLOW = True

    # Log requests taking longer than 25 seconds:
    DOGSLOW_TIMER = 25

    # Enable logging to Sentry
    DOGSLOW_SENTRY = True

    # Also log slow request tracebacks to Python logger
    DOGSLOW_LOGGER = 'dogslow_sentry'
    DOGSLOW_LOG_LEVEL = 'WARNING'

    # Tuple of url pattern names that should not be monitored:
    # (defaults to none -- everything monitored)
    DOGSLOW_IGNORE_URLS = ('some_view', 'other_view')


Usage
-----

Every incoming HTTP request gets a 25 second timeout in the watchdog. If a
request does not return within that time, the watchdog activates and takes a
peek at the request thread's stack and writes the backtrace (including all
local stack variables -- Django style) to a log file.

Note that ``dogslow`` only takes a peek at the thread's stack. It does not
interrupt the request, or influence it in any other way. Using ``dogslow`` is
therefore safe to use in production.


Caveats
-------

Dogslow uses multithreading. It has a single background thread that handles the
watchdog timeouts and takes the tracebacks, so that the original request
threads are not interrupted. This has some consequences.


Multithreading and the GIL
~~~~~~~~~~~~~~~~~~~~~~~~~~

In CPython, the GIL (Global Interpreter Lock) prevents multiple threads from
executing Python code simultaneously. Only when a thread explicitly releases
its lock on the GIL, can a second thread run.

Releasing the GIL is done automatically whenever a Python program makes
blocking calls outside of the interpreter, for example when doing IO.

For ``dogslow`` this means that it can only reliably intercept requests that
are slow because they are doing IO, calling sleep or busy waiting to acquire
locks themselves.

In most cases this is fine. An important cause of slow Django requests is an
expensive database query. Since this is IO, ``dogslow`` can intercept those
fine. A scenario where CPython's GIL is problematic is when the request's
thread hits an infinite loop in Python code (or legitimate Python that is
extremely expensive and takes a long time to execute), never releasing the
GIL. Even though ``dogslow``'s watchdog timer thread does become runnable, it
cannot log the stack.


Co-routines and Greenlets
~~~~~~~~~~~~~~~~~~~~~~~~~

``Dogslow`` is intended for use in a synchronous worker configuration. A
webserver that uses dedicated threads (or single-threaded, dedicated worker
processes) to serve requests. Django's built-in wsgi server does this, as
does ``Gunicorn`` in its default sync-worker mode.

When running with a "co-routines framework" where multiple requests are served
concurrently by one thread, backtraces might become nonsensical.
