import inspect
import time

import pytest


_true_sleep = time.sleep


class TimeSleepUsageError(RuntimeError):
    pass


class NeverSleepPlugin(object):

    TARGET_NAME = "time.sleep"

    def __init__(self, config):
        self.config = config
        self.root = str(config.rootdir)
        self.whitelist = self.get_whitelist()

    @pytest.fixture
    def disable_time_sleep(self):
        self._disable_time_sleep()
        yield
        self._enable_time_sleep()

    @pytest.fixture
    def enable_time_sleep(self):
        self._enable_time_sleep()
        yield
        self._disable_time_sleep()

    def pytest_sessionstart(self):
        """
        Start reporter before tests will executed
        """
        self._disable_time_sleep()

    def pytest_sessionfinish(self):
        """
        Teardown reporter when all tests were executed
        """
        self._enable_time_sleep()

    @pytest.hookimpl(trylast=True)
    def pytest_never_sleep_message_format(self, frame):
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
        values = []
        other = self.config.hook.pytest_never_sleep_whitelist()
        if other:
            values.extend(other)
        values.extend(self.config.option.whitelist)
        return values

    def sleep(self, seconds):
        frame = self.find_time_sleep_usage()
        if frame:
            msg = self.config.hook.pytest_never_sleep_message_format(frame=frame)
            raise TimeSleepUsageError(msg)
        _true_sleep(seconds)

    def is_necessary_frame(self, frame):
        return all(
            [
                self.root in frame[1],
                self.TARGET_NAME in " ".join(frame[4]),
                all(
                    [
                        white_list_path not in frame[1]
                        for white_list_path in self.whitelist
                    ]
                ),
            ]
        )

    def find_time_sleep_usage(self):
        frame_info = self.get_current_frame()
        for frame in frame_info:
            if self.is_necessary_frame(frame):
                return frame

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
