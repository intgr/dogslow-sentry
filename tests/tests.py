import sys
import datetime
from collections import namedtuple
try:
    import _thread as thread
except ImportError:
    import thread

import dogslow


def test_stack():
    my_variable = "aaaabbbbccccdddd"
    frame = sys._current_frames()[thread.get_ident()]
    stack_rendered = dogslow.stack(frame, with_locals=True)
    assert my_variable in stack_rendered


def test_surrogates(settings):
    frame = sys._current_frames()[thread.get_ident()]
    settings.DOGSLOW_STACK_VARS=False
    # If the bug is present, this will cause a UnicodeEncodeError:
    stack_rendered = dogslow.WatchdogMiddleware._compose_output(
        frame,
        req_string=u'GET \udcee hahaha',
        started=datetime.datetime.now(),
        thread_id=thread.get_ident())
    assert b'\xed\xb3\xae' in stack_rendered


def test_middleware_for_fast_request(settings, client, tmpdir):
    settings.DOGSLOW_TIMER = 5
    settings.DOGSLOW_OUTPUT = str(tmpdir)
    resp = client.get('/')
    assert resp.status_code == 200

    assert len(tmpdir.listdir()) == 0


def test_middleware_for_slow_request(settings, client, tmpdir):
    settings.DOGSLOW_TIMER = 0
    settings.DOGSLOW_OUTPUT = str(tmpdir)
    resp = client.get('/slow')
    assert resp.status_code == 200

    assert len(tmpdir.listdir()) == 1
    logfile, = tmpdir.listdir()
    content = logfile.read()
    assert content.startswith('Undead request intercepted')
