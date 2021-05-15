
def test_execute_plugin_with_default_options(testdir):
    config = testdir.parseconfigure()
    assert config.pluginmanager.hasplugin("pytest_never_sleep")
    assert not config.getoption("--disable-sleep")
    assert not config.getoption("--whitelist")


def test_execute_plugin_with_disable_sleep(testdir):
    config = testdir.parseconfigure("--disable-sleep")
    assert config.pluginmanager.hasplugin("pytest_never_sleep")
    assert config.getoption("--disable-sleep")
    assert not config.getoption("--whitelist")


def test_execute_plugin_with_whitelist(testdir):
    module_name = "my.awesome.module"
    config = testdir.parseconfigure("--whitelist", module_name)
    assert config.pluginmanager.hasplugin("pytest_never_sleep")
    assert not config.getoption("--disable-sleep")
    assert config.getoption("--whitelist")
    assert len(config.getoption("--whitelist")) == 1
    assert module_name in config.getoption("--whitelist")


def test_execute_plugin_with_all_params(testdir):
    module_name = "my.awesome.module"
    config = testdir.parseconfigure("--disable-sleep", "--whitelist", module_name)
    assert config.pluginmanager.hasplugin("pytest_never_sleep")
    assert config.getoption("--disable-sleep")
    assert config.getoption("--whitelist")
    assert len(config.getoption("--whitelist")) == 1
    assert module_name in config.getoption("--whitelist")
