import inspect
import logging
import pprint
import sys
import tempfile
import threading
import linecache
import os
import datetime as dt
import time
from functools import partial

from django.conf import settings
from django.core.exceptions import MiddlewareNotUsed
from django.core.mail.message import EmailMessage

class TimerTask(object):

    def __init__(self, callable, *args, **kwargs):
        self._callable = partial(callable, *args, **kwargs)
        self._finished = False

    def is_finished(self):
        return self._finished

    def run(self):
        try:
            self._callable()
        except:
            logging.exception('TimerTask failed')
        finally:
            self._finished = True

class Timer(threading.Thread):
    '''An alternative to threading.Timer. Where threading.Timer spawns a
    dedicated thread for each job, this class uses a single, long-lived thread
    to process multiple jobs.

    Jobs are scheduled with a delay value in seconds.
    '''

    def __init__(self, group=None, target=None, name=None, args=(), kwargs=None, verbose=None):
        super(Timer, self).__init__(group, target, name, args, kwargs, verbose)

        self.lock = threading.Condition()
        self._jobs = []
        self.die = False

    def run_later(self, callable, timeout, *args, **kwargs):
        '''Schedules the specified callable for delayed execution.
        Returns a TimerTask instance that can be used to cancel pending
        execution.'''

        self.lock.acquire()
        try:
            if self.die:
                raise RuntimeError('This timer has been shut down and does accept new jobs.')

            job = TimerTask(callable, *args, **kwargs)
            self._jobs.append((job, time.time() + timeout))
            self._jobs.sort(key=lambda job: job[1])  # sort on time
            self.lock.notify()

            return job
        finally:
            self.lock.release()

    def cancel(self, timer_task):
        self.lock.acquire()
        try:
            self._jobs = filter(lambda job: job[0] is not timer_task,
                                       self._jobs)
            self.lock.notify()
        finally:
            self.lock.release()

    def shutdown(self, cancel_jobs=False):
        self.lock.acquire()
        try:
            self.die = True
            if cancel_jobs:
                self.jobs = []
            self.lock.notify()
        finally:
            self.lock.release()

    def _get_sleep_time(self):
        if not self._jobs:
            return 0
        else:
            job, scheduled_at = self._jobs[0]
            return scheduled_at - time.time()

    def run(self):
        self.lock.acquire()
        try:
            while True:
                if not self._jobs:
                    if self.die:
                        break
                    else:
                        self.lock.wait()
                elif self._get_sleep_time() > 0:
                    self.lock.wait(self._get_sleep_time())
                else:
                    job, timeout= self._jobs.pop(0)
                    job.run()
        finally:
            self.lock.release()

class SafePrettyPrinter(pprint.PrettyPrinter, object):
    def format(self, obj, context, maxlevels, level):
        try:
            return super(SafePrettyPrinter, self).format(
                obj, context, maxlevels, level)
        except Exception:
            return object.__repr__(obj)[:-1] + ' (bad repr)>'

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
            args = inspect.formatargvalues(*args, formatvalue=formatvalue)
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
        if not getattr(settings, 'DJANGO_WATCHDOG', False):
            raise MiddlewareNotUsed
        else:
            self.interval = int(getattr(settings, 'DJANGO_WATCHDOG_TIMER', 25))
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
                'Parent PID: %d\n' \
                'Started:    %s\n\n' % \
                    (dt.datetime.utcnow().strftime("%d-%m-%Y %H:%M:%S UTC"),
                     req_string,
                     thread_id,
                     os.getpid(),
                     os.getppid(),
                     started.strftime("%d-%m-%Y %H:%M:%S UTC"),)

            output += stack(frame, with_locals=False)
            output += '\n\n'
            output += 'Full backtrace with local variables:'
            output += '\n\n'
            output += stack(frame, with_locals=True)

            # dump to file:
            fd, fn = tempfile.mkstemp(prefix='slow_request_', suffix='.log',
                                      dir=getattr(settings, 'DJANGO_WATCHDOG_OUTPUT',
                                              tempfile.gettempdir()))
            try:
                os.write(fd, output)
            finally:
                os.close(fd)

            # and email?
            if hasattr(settings, 'DJANGO_WATCHDOG_EMAIL_TO')\
                    and hasattr(settings, 'DJANGO_WATCHDOG_EMAIL_FROM'):
                em = EmailMessage('Slow Request Watchdog: %s' % str(req_string),
                                  output,
                                  getattr(settings, 'DJANGO_WATCHDOG_EMAIL_FROM'),
                                  (getattr(settings, 'DJANGO_WATCHDOG_EMAIL_TO'),))
                em.send(fail_silently=True)

        except Exception:
            logging.exception('Request watchdog failed')


    def process_request(self, request):
        request.django_watchdog = self.timer.run_later(
            WatchdogMiddleware.peek,
            self.interval,
            request,
            threading.currentThread().ident,
            dt.datetime.utcnow())

    def _cancel(self, request):
        try:
            if hasattr(request, 'django_watchdog'):
                self.timer.cancel(request.django_watchdog)
                del request.django_watchdog
        except:
            logging.exception('Failed to cancel request watchdog')

    def process_response(self, request, response):
        self._cancel(request)
        return response

    def process_exception(self, request, exception):
        self._cancel(request)
