import pytest


class TestCommandLine(object):
    def test_execute_plugin_with_default_options(self, testdir):
        config = testdir.parseconfigure()
        assert config.pluginmanager.hasplugin("never_sleep")
        assert not config.getoption("--disable-sleep")
        assert not config.getoption("--whitelist")

    def test_execute_plugin_with_disable_sleep(self, testdir):
        config = testdir.parseconfigure("--disable-sleep")
        assert config.pluginmanager.hasplugin("never_sleep")
        assert config.getoption("--disable-sleep")
        assert not config.getoption("--whitelist")

    def test_execute_plugin_with_whitelist(self, testdir):
        module_name = "my.awesome.module"
        config = testdir.parseconfigure("--whitelist", module_name)
        assert config.pluginmanager.hasplugin("never_sleep")
        assert not config.getoption("--disable-sleep")
        assert config.getoption("--whitelist")
        assert len(config.getoption("--whitelist")) == 1
        assert module_name in config.getoption("--whitelist")

    def test_execute_plugin_with_all_params(self, testdir):
        module_name = "my.awesome.module"
        config = testdir.parseconfigure("--disable-sleep", "--whitelist", module_name)
        assert config.pluginmanager.hasplugin("never_sleep")
        assert config.getoption("--disable-sleep")
        assert config.getoption("--whitelist")
        assert len(config.getoption("--whitelist")) == 1
        assert module_name in config.getoption("--whitelist")


class TestHooks(object):
    @pytest.fixture
    def create_green_tests(self, testdir):
        testdir.makepyfile(
            """
            def test_a(): pass
            def test_b(): pass
            def test_c(): pass
        """
        )

    @pytest.fixture
    def create_wrong_tests(self, testdir):
        testdir.makepyfile(
            """
            import time
            
            def test_a(): pass
            def test_b(): time.sleep(0.01)
            def test_c(): pass
        """
        )

    @pytest.fixture
    def create_message_format_hook(self, testdir):
        testdir.makeconftest(
            """
            def pytest_never_sleep_message_format(frame):
                print("HOOK CALLED")
        """
        )

    @pytest.fixture
    def create_whitelist_hook(self, testdir):
        testdir.makeconftest(
            """
            def pytest_never_sleep_whitelist():
                print("HOOK CALLED")
        """
        )

    @pytest.mark.usefixtures("create_green_tests", "create_message_format_hook")
    def test_not_call_hook_pytest_never_sleep_message_format_on_green_tests(
        self, testdir
    ):
        res = testdir.runpytest("--disable-sleep", "-vs")
        res.stdout.fnmatch_lines(["*3 passed*"])
        # res.stdout.no_fnmatch_line("*HOOK CALLED*")

    @pytest.mark.usefixtures("create_wrong_tests", "create_message_format_hook")
    def test_call_hook_pytest_never_sleep_message_format_on_unstable_tests(
        self, testdir
    ):
        res = testdir.runpytest("--disable-sleep", "-vs")
        res.stdout.fnmatch_lines(["*HOOK CALLED*", "*1 failed, 2 passed*"])

    @pytest.mark.usefixtures("create_green_tests", "create_whitelist_hook")
    def test_call_hook_pytest_never_sleep_whitelist_on_green_tests(self, testdir):
        res = testdir.runpytest("--disable-sleep", "-vs")
        res.stdout.fnmatch_lines(["*HOOK CALLED*", "*3 passed*"])

    @pytest.mark.usefixtures("create_wrong_tests", "create_whitelist_hook")
    def test_call_hook_pytest_never_sleep_whitelist_on_unstable_tests(self, testdir):
        res = testdir.runpytest("--disable-sleep", "-vs")
        res.stdout.fnmatch_lines(["*HOOK CALLED*", "*1 failed, 2 passed*"])


class TestAcceptance(object):
    def test_flag_disable_sleep(self, testdir):
        testdir.makepyfile(
            """
            import time

            def test_a(): pass
            def test_b(): time.sleep(0.01)
            def test_c(): pass
        """
        )
        res = testdir.runpytest("--disable-sleep", "-vs")
        res.stdout.fnmatch_lines(["*1 failed, 2 passed*"])

    def test_with_whitelist(self, testdir):
        testdir.makepyfile(
            test_a="""
            import time

            def test_a_1(): pass
            def test_a_2(): time.sleep(0.01)
            def test_a_3(): time.sleep(0.01)
        """,
            test_b="""
            import time

            def test_b_1(): pass
            def test_b_2(): time.sleep(0.001)
            def test_b_3(): pass
        """,
        )

        res = testdir.runpytest("--disable-sleep", "-vs", "--whitelist", "test_a")
        res.stdout.fnmatch_lines(["*1 failed, 5 passed*"])

    def test_with_allow_time_sleep_marker(self, testdir):
        testdir.makepyfile(
            """
            import time
            import pytest

            def test_a(): pass
            
            @pytest.mark.enable_time_sleep
            def test_b(): time.sleep(0.01)
            
            def test_c(): pass
        """
        )
        res = testdir.runpytest("--disable-sleep", "-vs")
        res.stdout.fnmatch_lines(["*3 passed*"])

    def test_with_not_allow_marker(self, testdir):
        testdir.makepyfile(
            """
            import time
            import pytest

            def test_a(): pass
            
            @pytest.mark.disable_time_sleep
            def test_b(): time.sleep(0.01)
            
            def test_c(): pass
        """
        )
        res = testdir.runpytest("-vs")
        res.stdout.fnmatch_lines(["*1 failed, 2 passed*"])

    def test_with_enabled_time_sleep_fixture(self, testdir):
        testdir.makepyfile(
            """
            import time
            import pytest

            def test_a(): pass

            @pytest.mark.usefixtures("enable_time_sleep")
            def test_b(): time.sleep(0.01)

            def test_c(): pass
        """
        )
        res = testdir.runpytest("--disable-sleep")
        res.stdout.fnmatch_lines(["*3 passed*"])

    def test_with_disabled_time_sleep_fixture(self, testdir):
        testdir.makepyfile(
            """
            import time
            import pytest

            def test_a(): pass

            @pytest.mark.usefixtures("disable_time_sleep")
            def test_b(): time.sleep(0.01)

            def test_c(): pass
        """
        )
        res = testdir.runpytest()
        res.stdout.fnmatch_lines(["*1 failed, 2 passed*"])
