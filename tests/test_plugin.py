def test_execute_plugin_with_default_options(testdir):
    config = testdir.parseconfigure("--disable-sleep")
    assert config.pluginmanager.hasplugin("pytest_never_sleep")
