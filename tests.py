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


MockSettings = namedtuple('MockSettings',
                          ['DOGSLOW_STACK_VARS'])


def test_surrogates(monkeypatch):
    frame = sys._current_frames()[thread.get_ident()]
    # Avoid really setting up django :)
    monkeypatch.setattr(dogslow,
                        'settings',
                        MockSettings(DOGSLOW_STACK_VARS=False))
    # If the bug is present, this will cause a UnicodeEncodeError:
    stack_rendered = dogslow.WatchdogMiddleware._compose_output(
        frame,
        req_string=u'GET \udcee hahaha',
        started=datetime.datetime.now(),
        thread_id=thread.get_ident())
    assert b'\xed\xb3\xae' in stack_rendered
