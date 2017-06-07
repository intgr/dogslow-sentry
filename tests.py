import sys
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
