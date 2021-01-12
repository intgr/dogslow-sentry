import codecs
import datetime as dt
import inspect
import logging
import threading
import os
import pprint
import socket
import sys
import tempfile
from types import FrameType, TracebackType
from typing import Optional

try:
    import sentry_sdk
except ImportError:
    entry_sdk = None

try:
    import _thread as thread
except ImportError:
    import thread
import linecache

from django.conf import settings
from django.core.exceptions import MiddlewareNotUsed
from django.core.mail.message import EmailMessage
from django.http import HttpRequest

try:
    from django.core.urlresolvers import resolve, Resolver404
except ImportError:
    # Django 2.0
    from django.urls import resolve, Resolver404

from dogslow_sentry.timer import Timer

# The errors= parameter of str.encode() in _compose_output:
#
# 'surrogatepass' was added in 3.1.
encoding_error_handler = "surrogatepass"
try:
    codecs.lookup_error(encoding_error_handler)
except LookupError:
    # In python 2.7, surrogates don't seem to trigger the error handler.
    # I'm going with 'replace' for consistency with the `stack` function,
    # although I'm not clear on whether this will ever get triggered.
    encoding_error_handler = "replace"

_sentinel = object()


def safehasattr(obj, name):
    return getattr(obj, name, _sentinel) is not _sentinel


class SafePrettyPrinter(pprint.PrettyPrinter, object):
    def format(self, obj, context, maxlevels, level):
        try:
            return super(SafePrettyPrinter, self).format(obj, context, maxlevels, level)
        except Exception:
            return object.__repr__(obj)[:-1] + " (bad repr)>", True, False


def spformat(obj, depth=None):
    return SafePrettyPrinter(indent=1, width=76, depth=depth).pformat(obj)


def formatvalue(v):
    s = spformat(v, depth=1).replace("\n", "")
    if len(s) > 250:
        s = object.__repr__(v)[:-1] + " (really long repr)>"
    return "=" + s


def stack(f, with_locals=False):
    limit = getattr(sys, "tracebacklimit", None)

    frames = []
    n = 0
    while f is not None and (limit is None or n < limit):
        lineno, co = f.f_lineno, f.f_code
        name, filename = co.co_name, co.co_filename
        args = inspect.getargvalues(f)

        linecache.checkcache(filename)
        line = linecache.getline(filename, lineno, f.f_globals)
        if line:
            line = line.strip()
        else:
            line = None

        frames.append((filename, lineno, name, line, f.f_locals, args))
        f = f.f_back
        n += 1
    frames.reverse()

    out = []
    for filename, lineno, name, line, localvars, args in frames:
        out.append('  File "%s", line %d, in %s' % (filename, lineno, name))
        if line:
            out.append("    %s" % line.strip())

        if with_locals:
            args = inspect.formatargvalues(formatvalue=formatvalue, *args)
            out.append("\n      Arguments: %s%s" % (name, args))

        if with_locals and localvars:
            out.append("      Local variables:\n")
            try:
                reprs = spformat(localvars)
            except Exception:
                reprs = "failed to format local variables"
            out += ["      " + l for l in reprs.splitlines()]
            out.append("")
    res = "\n".join(out)
    if isinstance(res, bytes):
        res = res.decode("utf-8", "replace")
    return res


class DogslowLog(BaseException):
    """Fake exception class for the reporting the stack trace to Sentry."""


def frames_to_traceback(
    frame: Optional[FrameType], until_file: str, until_func: str
) -> Optional[TracebackType]:
    """Convert stack frames into traceback, which can be handled by Sentry."""
    tb = None
    while frame is not None:
        # No point to trace further than the middleware itself
        # XXX TracebackType() constructor requires Python >= 3.7
        tb = TracebackType(tb, frame, frame.f_lasti, frame.f_lineno)
        if (
            frame.f_code.co_filename == until_file
            and frame.f_code.co_name == until_func
        ):
            break
        frame = frame.f_back
    return tb


class WatchdogMiddleware(object):
    def __init__(self, get_response=None):
        if not getattr(settings, "DOGSLOW", True):
            raise MiddlewareNotUsed
        else:
            self.get_response = get_response
            self.interval = int(getattr(settings, "DOGSLOW_TIMER", 25))
            # Django 1.10+ inits middleware when application starts
            # (it used to do this only when the first request is served).
            # uWSGI pre-forking prevents the timer from working properly
            # so we have to postpone the actual thread initialization
            self.timer = None
            self.timer_init_lock = threading.Lock()

    @staticmethod
    def _log_to_custom_logger(logger_name, exc_info, req_string):
        log_level = getattr(settings, "DOGSLOW_LOG_LEVEL", "WARNING")
        log_level = logging.getLevelName(log_level)
        logger = logging.getLogger(logger_name)

        msg = "Slow request: %s" % (req_string,)
        logger.log(log_level, msg, exc_info=exc_info)

    @staticmethod
    def _log_to_sentry_sdk(exc_info, request: HttpRequest, hub: sentry_sdk.Hub):
        # Copy Sentry Hub from original request thread
        with sentry_sdk.Hub(hub) as hub:
            # 'fingerprint' determines the behavior for grouping events.
            # Stack trace is not useful, as Dogslow will likely hit different
            # code every time.
            # {{ transaction }} is URL with placeholders, e.g. "/blog/{post_id}"
            hub.capture_exception(
                exc_info,
                level="warning",
                fingerprint=["{{ transaction }}", request.method],
            )

    @staticmethod
    def _log_to_email(email_to, email_from, output, req_string):
        if hasattr(email_to, "split"):
            # Looks like a string, but EmailMessage expects a sequence.
            email_to = (email_to,)
        em = EmailMessage(
            "Slow Request Watchdog: %s" % req_string,
            output.decode("utf-8", "replace"),
            email_from,
            email_to,
        )
        em.send(fail_silently=True)

    @staticmethod
    def _log_to_file(output):
        fd, fn = tempfile.mkstemp(
            prefix="slow_request_",
            suffix=".log",
            dir=getattr(settings, "DOGSLOW_OUTPUT", tempfile.gettempdir()),
        )
        try:
            os.write(fd, output)
        finally:
            os.close(fd)

    @staticmethod
    def _compose_output(frame, req_string, started, thread_id):
        output = (
            "Undead request intercepted at: %s\n\n"
            "%s\n"
            "Hostname:   %s\n"
            "Thread ID:  %d\n"
            "Process ID: %d\n"
            "Started:    %s\n\n"
            % (
                dt.datetime.utcnow().strftime("%d-%m-%Y %H:%M:%S UTC"),
                req_string,
                socket.gethostname(),
                thread_id,
                os.getpid(),
                started.strftime("%d-%m-%Y %H:%M:%S UTC"),
            )
        )
        output += stack(frame, with_locals=False)
        output += "\n\n"
        stack_vars = getattr(settings, "DOGSLOW_STACK_VARS", False)
        if not stack_vars:
            # no local stack variables
            output += (
                "This report does not contain the local stack "
                "variables.\n"
                "To enable this (very verbose) information, add "
                "this to your Django settings:\n"
                "  DOGSLOW_STACK_VARS = True\n"
            )
        else:
            output += "Full backtrace with local variables:"
            output += "\n\n"
            output += stack(frame, with_locals=True)
        return output.encode("utf-8", errors=encoding_error_handler)

    @staticmethod
    def peek(request, thread_id, started, sentry_hub):
        try:
            frame = sys._current_frames()[thread_id]

            req_string = "%s %s://%s%s" % (
                request.META.get("REQUEST_METHOD"),
                request.META.get("wsgi.url_scheme", "http"),
                request.META.get("HTTP_HOST"),
                request.META.get("PATH_INFO"),
            )
            if request.META.get("QUERY_STRING", ""):
                req_string += "?" + request.META.get("QUERY_STRING")

            output = WatchdogMiddleware._compose_output(
                frame, req_string, started, thread_id
            )

            # dump to file:
            log_to_file = getattr(settings, "DOGSLOW_LOG_TO_FILE", True)
            if log_to_file:
                WatchdogMiddleware._log_to_file(output)

            # and email?
            email_to = getattr(settings, "DOGSLOW_EMAIL_TO", None)
            email_from = getattr(settings, "DOGSLOW_EMAIL_FROM", None)

            if email_to is not None and email_from is not None:
                WatchdogMiddleware._log_to_email(
                    email_to, email_from, output, req_string
                )

            # Construct fake exception for attaching the traceback to
            exc = DogslowLog(f"Slow request: {request.method} {request.path_info}")
            # Reconstruct traceback for Sentry
            tb = frames_to_traceback(frame, __file__, "__call__")
            # exc_info is Tuple[Type[BaseException], BaseException, TracebackType]
            exc_info = (type(exc), exc, tb)

            # and a custom logger:
            logger_name = getattr(settings, "DOGSLOW_LOGGER", None)
            if logger_name is not None:
                WatchdogMiddleware._log_to_custom_logger(
                    logger_name, exc_info, req_string
                )

            # This is passed only if DOGSLOW_SENTRY was enabled
            if sentry_hub is not None:
                WatchdogMiddleware._log_to_sentry_sdk(exc_info, request, sentry_hub)

        except Exception:
            logging.exception("Dogslow failed")

    def _is_exempt(self, request):
        """
        Returns True if this request's URL resolves to a url pattern whose
        name is listed in settings.DOGSLOW_IGNORE_URLS.
        """
        exemptions = getattr(settings, "DOGSLOW_IGNORE_URLS", ())
        if exemptions:
            try:
                match = resolve(request.META.get("PATH_INFO"))
            except Resolver404:
                return False
            return match and (match.url_name in exemptions)
        else:
            return False

    def process_request(self, request):
        if not self._is_exempt(request):
            self._ensure_timer_initialized()

            sentry_hub: Optional[sentry_sdk.Hub] = None
            if getattr(settings, "DOGSLOW_SENTRY", False):
                # To inherit Sentry context from the original request thread,
                # we pass along Hub.current. See:
                # https://forum.sentry.io/t/scopes-and-multithreading-in-python/5180
                if sentry_sdk:
                    sentry_hub = sentry_sdk.Hub.current
                else:
                    logging.error("Cannot import sentry_sdk")

            request.dogslow = self.timer.run_later(
                WatchdogMiddleware.peek,
                self.interval,
                request,
                thread.get_ident(),
                dt.datetime.utcnow(),
                sentry_hub,
            )

    def _ensure_timer_initialized(self):
        if not self.timer:
            with self.timer_init_lock:
                # Double-checked locking reduces lock acquisition overhead
                if not self.timer:
                    self.timer = Timer()
                    self.timer.setDaemon(True)
                    self.timer.start()

    def _cancel(self, request):
        try:
            if safehasattr(request, "dogslow"):
                self.timer.cancel(request.dogslow)
                del request.dogslow
        except Exception:
            logging.exception("Failed to cancel Dogslow timer")

    def process_response(self, request, response):
        self._cancel(request)
        return response

    def process_exception(self, request, exception):
        self._cancel(request)

    def __call__(self, request):
        self.process_request(request)

        response = self.get_response(request)

        return self.process_response(request, response)
