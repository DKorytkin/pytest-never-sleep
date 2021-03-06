import time

import pytest
from diff_imports.import_from_module import do_some_stuff


def test_without_mark_and_fixture():
    do_some_stuff()  # pass if without --disable-sleep


@pytest.mark.usefixtures("disable_time_sleep")
def test_disable_time_sleep_fixture(do):
    assert do is None  # error


@pytest.mark.usefixtures("enable_time_sleep")
def test_enable_time_sleep_fixture(do):
    assert do is None  # pass


@pytest.mark.disable_time_sleep
def test_disable_time_sleep_mark():
    time.sleep(1)  # unstable


@pytest.mark.enable_time_sleep
def test_enable_time_sleep_mark():
    time.sleep(1)  # pass


class TestClass(object):
    def test_without_mark_and_fixture(self):
        do_some_stuff()  # pass if without --disable-sleep

    @pytest.mark.usefixtures("disable_time_sleep")
    def test_disable_time_sleep_fixture(self, do):
        assert do is None  # error

    @pytest.mark.usefixtures("enable_time_sleep")
    def test_enable_time_sleep_fixture(self, do):
        assert do is None  # pass

    @pytest.mark.disable_time_sleep
    def test_disable_time_sleep_mark(self):
        time.sleep(1)  # unstable

    @pytest.mark.enable_time_sleep
    def test_enable_time_sleep_mark(self):
        time.sleep(1)  # pass
