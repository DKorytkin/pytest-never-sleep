import time

import pytest
from diff_imports.import_from_module import do_some_stuff


def test_first():
    do_some_stuff()


@pytest.mark.usefixtures("disable_time_sleep")
def test_two(do):
    assert do


@pytest.mark.disable_time_sleep
def test_tree():
    time.sleep(1)
