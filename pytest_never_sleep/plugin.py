import pytest

from pytest_never_sleep import hooks
from pytest_never_sleep.never_sleep import (
    TARGET_NAME,
    FakeSleep,
    get_marker,
    using_fake_time_sleep,
    using_real_time_sleep,
)

_fake_time_sleep = FakeSleep()

MARK_ALLOW_TIME_SLEEP = "enable_time_sleep"
MARK_NOT_ALLOW_TIME_SLEEP = "disable_time_sleep"
MARKERS = {
    MARK_ALLOW_TIME_SLEEP: "Allow using `time.sleep` in test",
    MARK_NOT_ALLOW_TIME_SLEEP: "Not allow using `time.sleep` in test",
}


def pytest_configure(config):
    """
    Register plugin

    Parameters
    ----------
    config: _pytest.config.Config
    """
    for marker, message in MARKERS.items():
        config.addinivalue_line("markers", "{}: {}".format(marker, message))


def pytest_addhooks(pluginmanager):
    """
    Parameters
    ----------
    pluginmanager:
    """
    pluginmanager.add_hookspecs(hooks)


def pytest_addoption(parser):
    """
    Command line options for our plugin

    Parameters
    ----------
    parser: _pytest.config.Parser
    """
    group = parser.getgroup("never_sleep")
    group.addoption(
        "--disable-sleep",
        action="store_true",
        dest="disable_sleep",
        help="Disable time.sleep by default.",
    )
    group.addoption(
        "--whitelist",
        action="append",
        default=[],
        dest="whitelist",
        help="Allow time.sleep to these modules.",
    )


@pytest.fixture(name=MARK_NOT_ALLOW_TIME_SLEEP)
def disable_time_sleep():
    """
    This fixture disabled using `time.sleep` for particular tests
    """
    _fake_time_sleep.patch_time_sleep()
    with using_fake_time_sleep(_fake_time_sleep):
        yield


@pytest.fixture(name=MARK_ALLOW_TIME_SLEEP)
def enable_time_sleep():
    """
    This fixture enable using `time.sleep` for particular tests
    """
    with using_real_time_sleep(_fake_time_sleep):
        yield


@pytest.fixture(autouse=True)
def never_sleep(request):
    """
    Parameters
    ----------
    request: _pytest.fixtures.SubRequest
    """
    if get_marker(request, MARK_ALLOW_TIME_SLEEP):
        request.getfixturevalue("enable_time_sleep")
    elif request.config.getoption("--disable-sleep"):
        request.getfixturevalue("disable_time_sleep")
    elif get_marker(request, MARK_NOT_ALLOW_TIME_SLEEP):
        request.getfixturevalue("disable_time_sleep")


def pytest_sessionstart(session):
    """
    Disabled `time.sleep` on whole pytest session only in case when `--disable-sleep` was passed
    """
    whitelist = []
    other = session.config.hook.pytest_never_sleep_whitelist()
    if other:
        whitelist.extend(other)
    whitelist.extend(session.config.option.whitelist)

    # configuration for FakeSleep
    _fake_time_sleep.pytest_config = session.config
    _fake_time_sleep.is_allow_time_sleep_by_default = not bool(
        session.config.getoption("--disable-sleep")
    )
    _fake_time_sleep.whitelist = tuple(whitelist)
    _fake_time_sleep.get_message = session.config.hook.pytest_never_sleep_message_format
    _fake_time_sleep.patch_time_sleep()


def pytest_sessionfinish():
    """
    After all tests return back `time.sleep`
    """
    _fake_time_sleep.unpatch_time_sleep()


@pytest.hookimpl(trylast=True)
def pytest_never_sleep_message_format(config, frame):
    """
    Parameters
    ----------
    config: _pytest.config.Config
    frame: frame

    Returns
    -------
    str
    """
    root_dir = str(config.rootdir)
    path = frame.f_code.co_filename
    if root_dir in path:
        path = path.replace(root_dir, "").strip("/")
    msg = (
        "Method `{method}` uses `{target}`.\nIt can lead to degradation of test runtime, "
        "please check '{path}' line {number} "
        "and use `mock` for that peace of code."
    ).format(
        target=TARGET_NAME,
        method=frame.f_code.co_name,
        path=path,
        number=frame.f_code.co_firstlineno,
    )
    return msg
