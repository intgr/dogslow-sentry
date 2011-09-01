import inspect
import logging
import pprint
import sys
import tempfile
import thread
import linecache
import os
import datetime as dt

from django.conf import settings
from django.core.exceptions import MiddlewareNotUsed
from django.core.mail.message import EmailMessage
from django.core.urlresolvers import resolve

from dogslow.timer import Timer

class SafePrettyPrinter(pprint.PrettyPrinter, object):
    def format(self, obj, context, maxlevels, level):
        try:
            return super(SafePrettyPrinter, self).format(
                obj, context, maxlevels, level)
        except Exception:
            return object.__repr__(obj)[:-1] + ' (bad repr)>', True, False

def spformat(obj, depth=None):
    return SafePrettyPrinter(indent=1, width=76, depth=depth).pformat(obj)

def formatvalue(v):
    s = spformat(v, depth=1).replace('\n', '')
    if len(s) > 250:
        s = object.__repr__(v)[:-1] + ' (really long repr)>'
    return '=' + s

def stack(f, with_locals=False):
    if hasattr(sys, 'tracebacklimit'):
        limit = sys.tracebacklimit
    else:
        limit = None

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
            out.append('    %s' % line.strip())

        if with_locals:
            args = inspect.formatargvalues(formatvalue=formatvalue, *args)
            out.append('\n      Arguments: %s%s' % (name, args))

        if with_locals and localvars:
            out.append('      Local variables:\n')
            try:
                reprs = spformat(localvars)
            except Exception:
                reprs = "failed to format local variables"
            out += ['      ' + l for l in reprs.splitlines()]
            out.append('')
    return '\n'.join(out)

class WatchdogMiddleware(object):

    def __init__(self):
        if not getattr(settings, 'DOGSLOW', True):
            raise MiddlewareNotUsed
        else:
            self.interval = int(getattr(settings, 'DOGSLOW_TIMER', 25))
            self.timer = Timer()
            self.timer.setDaemon(True)
            self.timer.start()

    @staticmethod
    def peek(request, thread_id, started):
        try:
            frame = sys._current_frames()[thread_id]
            
            req_string = '%s %s://%s%s' % (
                request.META.get('REQUEST_METHOD'),
                request.META.get('wsgi.url_scheme', 'http'),
                request.META.get('HTTP_HOST'),
                request.META.get('PATH_INFO'),
            )
            if request.META.get('QUERY_STRING', ''):
                req_string += ('?' + request.META.get('QUERY_STRING'))

            output = 'Undead request intercepted at: %s\n\n' \
                '%s\n' \
                'Thread ID:  %d\n' \
                'Process ID: %d\n' \
                'Started:    %s\n\n' % \
                    (dt.datetime.utcnow().strftime("%d-%m-%Y %H:%M:%S UTC"),
                     req_string,
                     thread_id,
                     os.getpid(),
                     started.strftime("%d-%m-%Y %H:%M:%S UTC"),)

            output += stack(frame, with_locals=False)
            output += '\n\n'

            if (hasattr(settings, 'DOGSLOW_STACK_VARS')
                    and not bool(settings.DOGSLOW_STACK_VARS)):
                # no local stack variables
                output += ('This report does not contain the local stack '
                           'variables.\n'
                           'To enable this (very verbose) information, add '
                           'this to your Django settings:\n'
                           '  DOGSLOW_STACK_VARS=True\n')
            else:
                output += 'Full backtrace with local variables:'
                output += '\n\n'
                output += stack(frame, with_locals=True)

            output = output.encode('utf-8')

            # dump to file:
            fd, fn = tempfile.mkstemp(prefix='slow_request_', suffix='.log',
                                      dir=getattr(settings, 'DOGSLOW_OUTPUT',
                                              tempfile.gettempdir()))
            try:
                os.write(fd, output)
            finally:
                os.close(fd)

            # and email?
            if hasattr(settings, 'DOGSLOW_EMAIL_TO')\
                    and hasattr(settings, 'DOGSLOW_EMAIL_FROM'):
                em = EmailMessage('Slow Request Watchdog: %s' %
                                  req_string.encode('utf-8'),
                                  output,
                                  getattr(settings, 'DOGSLOW_EMAIL_FROM'),
                                  (getattr(settings, 'DOGSLOW_EMAIL_TO'),))
                em.send(fail_silently=True)

            # and a custom logger:
            if hasattr(settings, 'DOGSLOW_LOGGER'):
                logger = logging.getLogger(getattr(settings, 'DOGSLOW_LOGGER'))
                logger.warn('Slow Request Watchdog: %s, %%s - %%s' %
                            resolve(request.META.get('PATH_INFO')).url_name,
                            req_string.encode('utf-8'), output)

        except Exception:
            logging.exception('Request watchdog failed')


    def _is_exempt(self, request):
        """Returns True if this request's URL resolves to a url pattern whose
        name is listed in settings.DOGSLOW_IGNORE_URLS.
        """
        match = resolve(request.META.get('PATH_INFO'))
        return match and (match.url_name in
                       getattr(settings, 'DOGSLOW_IGNORE_URLS', ()))

    def process_request(self, request):
        if not self._is_exempt(request):
            request.dogslow = self.timer.run_later(
                WatchdogMiddleware.peek,
                self.interval,
                request,
                thread.get_ident(),
                dt.datetime.utcnow())

    def _cancel(self, request):
        try:
            if hasattr(request, 'dogslow'):
                self.timer.cancel(request.dogslow)
                del request.dogslow
        except:
            logging.exception('Failed to cancel request watchdog')

    def process_response(self, request, response):
        self._cancel(request)
        return response

    def process_exception(self, request, exception):
        self._cancel(request)
