import pytest

from pytest_never_sleep import hooks
from pytest_never_sleep.never_sleep import (
    TARGET_METHOD_NAME,
    TARGET_MODULE_NAME,
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
    reporter = NeverSleepPlugin(config)
    config.pluginmanager.register(reporter, name="pytest_never_sleep")
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


@pytest.fixture
def disable_time_sleep():
    """
    This fixture disabled using `time.sleep` for particular tests
    """
    _fake_time_sleep.patch_time_sleep()
    with using_fake_time_sleep(_fake_time_sleep):
        yield


@pytest.fixture
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


class NeverSleepPlugin(object):
    """
    This plugin adds ability to find unexpected `time.sleep` in codebase
    just pass `--disable-sleep` to pytest CLI
    It will raise `TimeSleepUsageError` every time when faces with `time.sleep` which absent
    in whitelist

    The whitelist could be overwritten by hook `pytest_never_sleep_whitelist`
    Default error message also can be overwritten via hook `pytest_never_sleep_message_format`

    The fixture `enable_time_sleep` adds ability to allow `time.sleep` in particular tests
    """

    TARGET_NAME = "{}.{}".format(TARGET_MODULE_NAME, TARGET_METHOD_NAME)

    def __init__(self, config):
        self.config = config
        self.root = str(config.rootdir)
        self.whitelist = tuple(self.get_whitelist())

    def pytest_sessionstart(self):
        """
        Disabled `time.sleep` on whole pytest session only in case when `--disable-sleep` was passed
        """
        _fake_time_sleep.allow_time_sleep = not bool(
            self.config.getoption("--disable-sleep")
        )
        _fake_time_sleep.whitelist = self.whitelist
        _fake_time_sleep.get_message = (
            self.config.hook.pytest_never_sleep_message_format
        )
        _fake_time_sleep.patch_time_sleep()

    def pytest_sessionfinish(self):
        """
        After all tests return back `time.sleep`
        """
        _fake_time_sleep.unpatch_time_sleep()

    @pytest.hookimpl(trylast=True)
    def pytest_never_sleep_message_format(self, frame):
        """
        Parameters
        ----------
        frame: frame

        Returns
        -------
        str
        """
        method = frame.f_code.co_name
        line_number = frame.f_code.co_firstlineno
        path = frame.f_code.co_filename
        if self.root in path:
            path = path.replace(self.root, "").strip("/")
        msg = (
            "Method `{method}` uses `{target}`.\nIt can lead to degradation of test runtime, "
            "please check '{path}' line {number} "
            "and use `mock` for that peace of code."
        ).format(
            target=self.TARGET_NAME,
            method=method,
            path=path,
            number=line_number,
        )
        return msg

    def get_whitelist(self):
        """
        Combine all whitelists which could be passed via hook and CLI

        Returns
        -------
        List[str]
        """
        values = []
        other = self.config.hook.pytest_never_sleep_whitelist()
        if other:
            values.extend(other)
        values.extend(self.config.option.whitelist)
        return values
