=======================================
Dogslow -- Django Slow Request Watchdog
=======================================


Overview
--------

Dogslow is a Django watchdog middleware class that logs tracebacks of slow
requests.

It started as an `internal project inside Bitbucket`_ to help trace
operational problems.

.. _internal project inside Bitbucket: http://blog.bitbucket.org/2011/05/17/tracking-slow-requests-with-dogslow/


Installation
------------

Install dogslow::

    $ pip install dogslow

Then add ``dogslow.WatchdogMiddleware`` to your list of middleware classes in
your Django settings.py file::

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

    # By default, Watchdog will create log files with the backtraces.
    # You can also set the location of where it stores them:
    DOGSLOW_LOG_TO_FILE = True
    DOGSLOW_OUTPUT = '/tmp'

    # Log requests taking longer than 25 seconds:
    DOGSLOW_TIMER = 25

    # When both specified, emails backtraces:
    DOGSLOW_EMAIL_TO = 'errors@atlassian.com'
    DOGSLOW_EMAIL_FROM = 'no-reply@atlassian.com'

    # Also log to this logger (defaults to none):
    DOGSLOW_LOGGER = 'syslog_logger'
    DOGSLOW_LOG_LEVEL = 'WARNING'

    # Tuple of url pattern names that should not be monitored:
    # (defaults to none -- everything monitored)
    # Note: this option is not compatible with Django < 1.3
    DOGSLOW_IGNORE_URLS = ('some_view', 'other_view')

    # Print (potentially huge!) local stack variables (off by default, use
    # True for more detailed, but less manageable reports)
    DOGSLOW_STACK_VARS = True


Usage
-----

Every incoming HTTP request gets a 25 second timeout in the watchdog. If a
request does not return within that time, the watchdog activates and takes a
peek at the request thread's stack and writes the backtrace (including all
local stack variables -- Django style) to a log file.

Each slow request is logged in a separate file that looks like this::

    Undead request intercepted at: 16-05-2011 02:10:12 UTC

    GET http://localhost:8000/?delay=2
    Thread ID:  140539485042432
    Process ID: 18010
    Started:    16-05-2011 02:10:10 UTC

      File "/home/erik/work/virtualenv/bit/lib/python2.7/site-packages/django/core/management/commands/runserver.py", line 107, in inner_run
        run(self.addr, int(self.port), handler, ipv6=self.use_ipv6)
      File "/home/erik/work/virtualenv/bit/lib/python2.7/site-packages/django/core/servers/basehttp.py", line 696, in run
        httpd.serve_forever()
      File "/usr/lib/python2.7/SocketServer.py", line 227, in serve_forever
        self._handle_request_noblock()
      File "/usr/lib/python2.7/SocketServer.py", line 284, in _handle_request_noblock
        self.process_request(request, client_address)
      File "/usr/lib/python2.7/SocketServer.py", line 310, in process_request
        self.finish_request(request, client_address)
      File "/usr/lib/python2.7/SocketServer.py", line 323, in finish_request
        self.RequestHandlerClass(request, client_address, self)
      File "/home/erik/work/virtualenv/bit/lib/python2.7/site-packages/django/core/servers/basehttp.py", line 570, in __init__
        BaseHTTPRequestHandler.__init__(self, *args, **kwargs)
      File "/usr/lib/python2.7/SocketServer.py", line 639, in __init__
        self.handle()
      File "/home/erik/work/virtualenv/bit/lib/python2.7/site-packages/django/core/servers/basehttp.py", line 615, in handle
        handler.run(self.server.get_app())
      File "/home/erik/work/virtualenv/bit/lib/python2.7/site-packages/django/core/servers/basehttp.py", line 283, in run
        self.result = application(self.environ, self.start_response)
      File "/home/erik/work/virtualenv/bit/lib/python2.7/site-packages/django/contrib/staticfiles/handlers.py", line 68, in __call__
        return self.application(environ, start_response)
      File "/home/erik/work/virtualenv/bit/lib/python2.7/site-packages/django/core/handlers/wsgi.py", line 273, in __call__
        response = self.get_response(request)
      File "/home/erik/work/virtualenv/bit/lib/python2.7/site-packages/django/core/handlers/base.py", line 111, in get_response
        response = callback(request, *callback_args, **callback_kwargs)
      File "/home/erik/work/middleware/middleware/sleep/views.py", line 6, in sleep
        time.sleep(float(request.GET.get('delay', 1)))

    Full backtrace with local variables:

      File "/home/erik/work/virtualenv/bit/lib/python2.7/site-packages/django/core/management/commands/runserver.py", line 107, in inner_run
        run(self.addr, int(self.port), handler, ipv6=self.use_ipv6)

      ...loads more...

The example above shows that the request thread was blocked in
``time.sleep()`` at the time ``dogslow`` took its snapshot.

Requests that return before ``dogslow``'s timeout expires do not get logged.

Note that ``dogslow`` only takes a peek at the thread's stack. It does not
interrupt the request, or influence it in any other way. Using ``dogslow`` is
therefore safe to use in production.


Sentry Integration
------------------

Dogslow natively integrates with Sentry. You can set it up by configuring
Dogslow to use ``DOGSLOW_LOGGER`` and ``DOGSLOW_LOG_TO_SENTRY`` and by
`configuring Raven`_ to collect Dogslow's reports. ::

    DOGSLOW_LOGGER = 'dogslow' # can be anything, but must match `logger` below
    DOGSLOW_LOG_TO_SENTRY = True
    
    DOGSLOW_LOG_LEVEL = 'WARNING' # optional, defaults to 'WARNING'
    
    # Add a new sentry handler to handle WARNINGs. It's not recommended to
    # modify the existing sentry handler, as you'll probably start seeing
    # other warnings unnecessarily sent to Sentry.
    LOGGING = {
        ...
        'handlers': {
            ...
            'dogslow': {
                'level': 'WARNING',
                'class': 'raven.contrib.django.handlers.SentryHandler',
            }
            ...
        }
        'loggers': {
            ...
            'dogslow': {
                'level': 'WARNING',
                'handlers': ['dogslow'], # or whatever you named your handler
            }
            ...
        }
        ...
    }
    

.. _configuring Raven: http://raven.readthedocs.org/en/latest/config/django.html#integration-with-logging


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
