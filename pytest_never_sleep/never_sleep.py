import inspect
import time

import pytest

_true_sleep = time.sleep


class TimeSleepUsageError(RuntimeError):
    """
    The error which raises when `time.sleep` unexpectedly uses
    """


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

    TARGET_NAME = "time.sleep"

    def __init__(self, config):
        self.config = config
        self.root = str(config.rootdir)
        self.whitelist = self.get_whitelist()

    @pytest.fixture
    def disable_time_sleep(self):
        """
        This fixture disabled using `time.sleep` for particular tests
        """
        self._disable_time_sleep()
        yield
        self._enable_time_sleep()

    @pytest.fixture
    def enable_time_sleep(self):
        """
        This fixture enable using `time.sleep` for particular tests
        """
        self._enable_time_sleep()
        yield
        self._disable_time_sleep()

    def pytest_sessionstart(self):
        """
        Disabled `time.sleep` on whole pytest session only in case when `--disable-sleep` was passed
        """
        if self.config.getoption("--disable-sleep"):
            self._disable_time_sleep()

    def pytest_sessionfinish(self):
        """
        After all tests return back `time.sleep`
        """
        self._enable_time_sleep()

    @pytest.hookimpl(trylast=True)
    def pytest_never_sleep_message_format(self, frame):
        """
        Parameters
        ----------
        frame: tuple

        Returns
        -------
        str
        """
        msg = (
            "Method `{method}` uses `{target}`.\nIt can lead to degradation of test runtime,"
            "please check '{path}' line {number} "
            "and use mock for that peace of code."
        ).format(
            target=self.TARGET_NAME,
            method=frame[3],
            path=frame[1],
            number=frame[2],
        )
        return msg

    @staticmethod
    def _enable_time_sleep():
        time.sleep = _true_sleep

    def _disable_time_sleep(self):
        time.sleep = self.sleep

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

    def sleep(self, seconds):
        """
        Own implementation of `time.sleep` which track where it was called and raises an error if
        this path not in the whitelist

        Parameters
        ----------
        seconds: int | float
        """
        frame = self.find_time_sleep_usage()
        if frame:
            msg = self.config.hook.pytest_never_sleep_message_format(frame=frame)
            raise TimeSleepUsageError(msg)
        _true_sleep(seconds)

    def is_necessary_frame(self, frame):
        """
        Parameters
        ----------
        frame: tuple

        Returns
        -------
        bool
        """
        return all(
            [
                self.root in frame[1],
                self.TARGET_NAME in " ".join(frame[4]),
                all(
                    white_list_path not in frame[1]
                    for white_list_path in self.whitelist
                ),
            ]
        )

    def find_time_sleep_usage(self):
        """
        Uses `inspect` to finding place where `time.sleep` was called

        Returns
        -------
        Optional[tuple]
        """
        frame_info = self.get_current_frame()
        for frame in frame_info:
            if self.is_necessary_frame(frame):
                return frame
        return None

    @staticmethod
    def get_current_frame():
        """
        Returns:
        List[tuple]
            [
                (
                    <frame object>,
                    "path_to_module.py",
                    line_number,
                    function_name,
                    ["stack of calls"]
                ),
            ]
        """
        current_frame = inspect.currentframe()
        return inspect.getouterframes(current_frame, 2)
