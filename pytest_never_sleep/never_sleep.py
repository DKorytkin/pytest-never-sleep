import contextlib
import inspect
import sys
import time

import pytest

_true_time = time
_true_time_sleep = time.sleep
_real_time_sleep_ids = (id(_true_time_sleep), id(_true_time))
TARGET_MODULE_NAME = "time"
TARGET_METHOD_NAME = "sleep"
LIMIT_STACK_INSPECTION = 5
DEFAULT_IGNORE_LIST = [
    "py",
    "pytest",
    "_pytest",
    "nose.plugins",
    "threading",
    "Queue",
]


class TimeSleepUsageError(RuntimeError):
    """
    The error which raises when `time.sleep` unexpectedly uses
    """


def get_target_attributes(module):
    """
    Parameters
    ----------
    module

    Returns
    -------
    Generator
        ("attribute_name", <object function or module>)
    """
    for attribute_name in dir(module):
        if attribute_name not in (TARGET_MODULE_NAME, TARGET_METHOD_NAME):
            continue
        try:
            attribute_value = getattr(module, attribute_name)
        except (ImportError, AttributeError, TypeError):
            continue
        yield attribute_name, attribute_value


class Cache(object):
    """
    Cache needs to avoid processing all modules in every call of fixture

    Example of data:
        {
            'test_imports': ('4514533200--7022640807274930827', []),
            'tests': ('4514140240--8879947260191160972', []),
            'tests.acceptance': ('4514742544--2037579862527527209', []),
            'tests.acceptance.diff_imports': ('4514742448--5005491873314787699', []),
            'tests.acceptance.diff_imports.import_from_module': (
                '4514742352--4263818908760398017',
                [
                    ('time', <module 'time' (built-in)>)
                ]
            ),
        }
    """
    def __init__(self):
        self.data = {}

    @staticmethod
    def _get_module_attributes_hash(module):
        try:
            attributes = dir(module)
        except (ImportError, TypeError):
            attributes = []
        return "{}-{}".format(id(module), hash(frozenset(attributes)))

    def _setup_module_cache(self, module):
        date_attrs = []
        for attribute_name, attribute_value in get_target_attributes(module):
            if id(attribute_value) in _real_time_sleep_ids:
                date_attrs.append((attribute_name, attribute_value))
        return self._get_module_attributes_hash(module), date_attrs

    def add(self, module):
        """
        Parameters
        ----------
        module

        Returns
        -------
        List[Tuple[str, Callable]]
            [
                ("sleep", <built-in function sleep>),
                ("time", <module 'time' from 'time.so'>),
            ]
        """
        module_hash, module_attrs = self._setup_module_cache(module)
        self.data[module.__name__] = (module_hash, module_attrs)
        return module_attrs

    def get(self, module):
        """
        Parameters
        ----------
        module

        Returns
        -------
        Target attributes of module: Optional[List[Tuple[str, Callable]]]
            [
                ("sleep", <built-in function sleep>),
                ("time", <module 'time' from 'time.so'>),
            ]
        """
        module_hash, module_attrs = self.data.get(module.__name__) or ("", [])
        if self._get_module_attributes_hash(module) == module_hash:
            return module_attrs
        return None


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

    TARGET_NAME = "{}.{}".format(TARGET_MODULE_NAME, TARGET_METHOD_NAME)
    MARK_ALLOW_TIME_SLEEP = "allow_time_sleep"
    MARK_NOT_ALLOW_TIME_SLEEP = "not_allow_time_sleep"
    MARKERS = {
        MARK_ALLOW_TIME_SLEEP: "Allow using `time.sleep` in test",
        MARK_NOT_ALLOW_TIME_SLEEP: "Not allow using `time.sleep` in test",
    }

    def __init__(self, config):
        self.config = config
        self.root = str(config.rootdir)
        self.cache = Cache()
        self.whitelist = tuple(self.get_whitelist() or DEFAULT_IGNORE_LIST)
        self._allow_time_sleep = False

    @pytest.fixture
    def disable_time_sleep(self):
        """
        This fixture disabled using `time.sleep` for particular tests
        """
        self._disable_time_sleep()

    @pytest.fixture
    def enable_time_sleep(self):
        """
        This fixture enable using `time.sleep` for particular tests
        """
        with self.allow_time_sleep():
            yield

    @pytest.fixture(autouse=True)
    def never_sleep(self, request):
        """
        Parameters
        ----------
        request: _pytest.fixtures.SubRequest
        """
        if self.get_marker(request, "allow_time_sleep"):
            request.getfixturevalue("enable_time_sleep")
        elif self.get_marker(request, "not_allow_time_sleep"):
            request.getfixturevalue("disable_time_sleep")
        elif self.config.getoption("--disable-sleep"):
            request.getfixturevalue("disable_time_sleep")

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
        frame: frame

        Returns
        -------
        str
        """
        method = frame.f_code.co_name
        line_number = frame.f_code.co_firstlineno
        path = frame.f_code.co_filename
        if self.root in path:
            path = path.replace(self.root, "").strip("/")
        msg = (
            "Method `{method}` uses `{target}`.\nIt can lead to degradation of test runtime, "
            "please check '{path}' line {number} "
            "and use mock for that peace of code."
        ).format(
            target=self.TARGET_NAME,
            method=method,
            path=path,
            number=line_number,
        )
        return msg

    @staticmethod
    def get_marker(request, name):
        """
        Needs to keep compatible between different pytest versions

        Parameters
        ----------
        request: _pytest.fixtures.SubRequest
        name: str

        Returns
        -------
        Optional[_pytest.mark.structures.MarkInfo | _pytest.mark.structures.Mark]
        """
        try:
            marker = request.node.get_marker(name)
        except AttributeError:
            marker = request.node.get_closest_marker(name)
        return marker

    @contextlib.contextmanager
    def allow_time_sleep(self):
        """
        Needs for temporary allow `time.sleep` using
        """
        old_value = self._allow_time_sleep
        self._allow_time_sleep = True
        try:
            yield
        finally:
            self._allow_time_sleep = old_value

    def fake_sleep(self, seconds):
        """
        Own implementation of `time.sleep` which track where it was called and raises an error if
        this path not in the whitelist

        Parameters
        ----------
        seconds: int | float
        """
        if not self._allow_time_sleep:
            frame = self.get_current_frame()
            msg = self.config.hook.pytest_never_sleep_message_format(frame=frame)
            raise TimeSleepUsageError(msg)
        _true_time_sleep(seconds)

    def _sys_modules(self):
        ignore = (TARGET_MODULE_NAME, "datetime", "_datetime")
        for mod_name, module in dict(sys.modules).items():
            if mod_name is None or module is None or mod_name == __name__:
                continue
            if mod_name.startswith(ignore) or mod_name.startswith(self.whitelist):
                continue
            yield module

    def _enable_time_sleep(self):
        for module in self._sys_modules():
            for attribute_name, attribute_value in get_target_attributes(module):
                if id(attribute_value) in _real_time_sleep_ids:
                    continue
                real = _true_time_sleep
                if attribute_name == TARGET_MODULE_NAME:
                    setattr(attribute_value, TARGET_METHOD_NAME, real)
                    real = attribute_value
                setattr(module, attribute_name, real)

    def _disable_time_sleep(self):
        for module in self._sys_modules():
            if self.cache.get(module):
                continue

            module_time_sleep_attrs = self.cache.add(module)
            for attribute_name, attribute_value in module_time_sleep_attrs:
                fake = self.fake_sleep
                if attribute_name == TARGET_MODULE_NAME:
                    setattr(attribute_value, TARGET_METHOD_NAME, fake)
                    fake = attribute_value
                setattr(module, attribute_name, fake)

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

    @staticmethod
    def get_current_frame():
        """
        Returns
        -------
        frame of call
        """
        frame = inspect.currentframe().f_back.f_back
        for _ in range(LIMIT_STACK_INSPECTION):
            if frame.f_globals.get("__name__") == __name__:
                frame = frame.f_back
                continue
            return frame
