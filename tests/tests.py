import sys
import datetime
import _thread as thread

import sentry_sdk

import dogslow_sentry


def test_stack():
    my_variable = "aaaabbbbccccdddd"
    frame = sys._current_frames()[thread.get_ident()]
    stack_rendered = dogslow_sentry.stack(frame, with_locals=True)
    assert my_variable in stack_rendered


def test_surrogates(settings):
    frame = sys._current_frames()[thread.get_ident()]
    settings.DOGSLOW_STACK_VARS = False
    # If the bug is present, this will cause a UnicodeEncodeError:
    stack_rendered = dogslow_sentry.WatchdogMiddleware._compose_output(
        frame,
        req_string=u"GET \udcee hahaha",
        started=datetime.datetime.now(),
        thread_id=thread.get_ident(),
    )
    assert b"\xed\xb3\xae" in stack_rendered


def test_middleware_for_fast_request(settings, client, tmpdir):
    settings.DOGSLOW_TIMER = 5
    settings.DOGSLOW_OUTPUT = str(tmpdir)
    resp = client.get("/")
    assert resp.status_code == 200

    assert len(tmpdir.listdir()) == 0


def test_middleware_for_slow_request(settings, client, tmpdir):
    settings.DOGSLOW_TIMER = 0
    settings.DOGSLOW_OUTPUT = str(tmpdir)
    resp = client.get("/slow")
    assert resp.status_code == 200

    assert len(tmpdir.listdir()) == 1
    (logfile,) = tmpdir.listdir()
    content = logfile.read()
    assert content.startswith("Undead request intercepted")


def test_email_to_single_address(settings, client, mailoutbox):
    settings.DOGSLOW_TIMER = 0
    settings.DOGSLOW_EMAIL_FROM = "sender@example.com"
    settings.DOGSLOW_EMAIL_TO = "recipient@example.com"

    resp = client.get("/slow")
    assert resp.status_code == 200

    assert len(mailoutbox) == 1
    assert mailoutbox[0].from_email == "sender@example.com"
    assert mailoutbox[0].body.startswith("Undead request")
    assert mailoutbox[0].to == ["recipient@example.com"]


def test_email_to_multiple_addresses(settings, client, mailoutbox):
    settings.DOGSLOW_TIMER = 0
    settings.DOGSLOW_EMAIL_FROM = "sender@example.com"
    settings.DOGSLOW_EMAIL_TO = [
        "recipient1@example.com",
        "recipient2@example.com",
        "recipient3@example.com",
    ]

    resp = client.get("/slow")
    assert resp.status_code == 200

    assert len(mailoutbox) == 1
    assert mailoutbox[0].from_email == "sender@example.com"
    assert mailoutbox[0].body.startswith("Undead request")
    assert mailoutbox[0].to == [
        "recipient1@example.com",
        "recipient2@example.com",
        "recipient3@example.com",
    ]


def test_log_to_custom_logger(settings, client, caplog):
    settings.DOGSLOW_TIMER = 0
    settings.DOGSLOW_LOGGER = "dogslow1234"

    resp = client.get("/slow")
    assert resp.status_code == 200

    assert len(caplog.records) == 1
    rec = caplog.records[0]
    assert rec.name == "dogslow1234"
    assert rec.levelname == "WARNING"
    assert rec.msg.startswith("Slow request: ")


def test_log_to_sentry(settings, client, capture_events):
    settings.DOGSLOW_TIMER = 0.2
    settings.DOGSLOW_SENTRY = True

    sentry_sdk.init()
    events = capture_events()

    resp = client.get("/slow")
    assert resp.status_code == 200
    assert len(events) == 1

    (event,) = events
    assert event["exception"]
    assert len(event["exception"]["values"]) == 1

    (exception,) = event["exception"]["values"]
    assert exception["type"] == "DogslowLog"
    assert exception["value"] == "Slow request: GET /slow"
    # XXX Is checking the stack trace too racy?
    assert exception["stacktrace"]["frames"][-1]["module"] == "tests.urls"
    assert exception["stacktrace"]["frames"][-1]["function"] == "slow_view"
