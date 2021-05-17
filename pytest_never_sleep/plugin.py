from pytest_never_sleep import hooks
from pytest_never_sleep.never_sleep import NeverSleepPlugin, MARKERS


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
