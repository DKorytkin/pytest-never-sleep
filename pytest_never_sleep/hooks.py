import pytest


@pytest.hookspec(firstresult=True)
def pytest_never_sleep_whitelist():
    pass


@pytest.hookspec(firstresult=True)
def pytest_never_sleep_message_format(frame):
    pass
