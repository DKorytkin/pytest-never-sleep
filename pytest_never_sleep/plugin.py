from pytest_never_sleep.never_sleep import NeverSleepPlugin
from pytest_never_sleep import hooks


def pytest_configure(config):
    if config.getoption("--disable-sleep"):
        reporter = NeverSleepPlugin(config)
        config.pluginmanager.register(reporter, name="pytest_never_sleep")


def pytest_addhooks(pluginmanager):
    pluginmanager.add_hookspecs(hooks)


def pytest_addoption(parser):
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
        help="Allow time.sleep to these modules",
    )
