import inspect
import time
import sys

import pytest

_true_time = time
_true_time_sleep = time.sleep
TARGET_MODULE = "time"
TARGET_METHOD = "sleep"
LIMIT_STACK_INSPECTION = 5
DEFAULT_IGNORE_LIST = [
    'pytest.',
    '_pytest.',
    'nose.plugins',
    'threading',
    'Queue',
]


class TimeSleepUsageError(RuntimeError):
    """
    The error which raises when `time.sleep` unexpectedly uses
    """
    pass


class Cache(object):
    def __init__(self, ):
        self._real_time_sleep_ids = (id(_true_time_sleep), id(_true_time))
        self.data = {}

    @staticmethod
    def _get_module_attributes_hash(module):
        try:
            attributes = dir(module)
        except (ImportError, TypeError):
            attributes = []
        return '{}-{}'.format(id(module), hash(frozenset(attributes)))

    @staticmethod
    def _get_module_attributes(module):
        result = []
        try:
            module_attributes = dir(module)
            for attribute_name in module_attributes:
                attribute_value = getattr(module, attribute_name)
                result.append((attribute_name, attribute_value))
        except (ImportError, AttributeError, TypeError):
            # For certain libraries
            # this can result in ImportError(_winreg) or AttributeError(celery)
            pass
        return result

    def _setup_module_cache(self, module):
        date_attrs = []
        all_module_attributes = self._get_module_attributes(module)
        for attribute_name, attribute_value in all_module_attributes:
            if attribute_name not in (TARGET_MODULE, TARGET_METHOD):
                continue
            if id(attribute_value) in self._real_time_sleep_ids:
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
        Optional[List[Tuple[str, Callable]]]
            [
                ("sleep", <built-in function sleep>),
                ("time", <module 'time' from 'time.so'>),
            ]
        """
        module_hash, module_attrs = self.data.get(module.__name__) or ("", [])
        if self._get_module_attributes_hash(module) == module_hash:
            return module_attrs


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

    TARGET_NAME = "{}.{}".format(TARGET_MODULE, TARGET_METHOD)

    def __init__(self, config):
        self.config = config
        self.root = str(config.rootdir)
        self.changes = []
        self.cache = Cache()
        self.whitelist = tuple(self.get_whitelist() or DEFAULT_IGNORE_LIST)

    @pytest.fixture
    def disable_time_sleep(self):
        """
        This fixture disabled using `time.sleep` for particular tests
        """
        self._disable_time_sleep()
        yield
        self._enable_time_sleep()

    @pytest.fixture
    def enable_time_sleep(self):
        """
        This fixture enable using `time.sleep` for particular tests
        """
        self._enable_time_sleep()
        yield
        self._disable_time_sleep()

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

    def should_use_real_time_sleep(self):
        if not self.whitelist:
            return False

        frame = inspect.currentframe().f_back.f_back
        for _ in range(LIMIT_STACK_INSPECTION):
            module_name = frame.f_globals.get('__name__')
            if module_name and module_name.startswith(self.whitelist):
                return module_name

            frame = frame.f_back
            if frame is None:
                break

        return False

    def fake_sleep(self, seconds):
        """
        Own implementation of `time.sleep` which track where it was called and raises an error if
        this path not in the whitelist

        Parameters
        ----------
        seconds: int | float
        """
        if not self.should_use_real_time_sleep():
            frame = self.get_current_frame()
            msg = self.config.hook.pytest_never_sleep_message_format(frame=frame)
            raise TimeSleepUsageError(msg)

        _true_time_sleep(seconds)

    def _sys_modules(self):
        for mod_name, module in sys.modules.items():
            if mod_name is None or module is None or mod_name == __name__:
                continue
            elif mod_name.startswith(self.whitelist) or mod_name.endswith('.six.moves'):
                continue
            elif mod_name == TARGET_MODULE:
                continue
            yield module

    def _enable_time_sleep(self):
        for (module, attribute_name, attribute_value) in self.changes:
            real = _true_time_sleep
            if attribute_name == TARGET_MODULE:
                setattr(attribute_value, TARGET_METHOD, real)
                real = attribute_value
            setattr(module, attribute_name, real)

    def _disable_time_sleep(self):
        for module in self._sys_modules():
            if self.cache.get(module):
                continue

            module_time_sleep_attrs = self.cache.add(module)
            for attribute_name, attribute_value in module_time_sleep_attrs:
                fake = self.fake_sleep
                if attribute_name == TARGET_MODULE:
                    setattr(attribute_value, TARGET_METHOD, fake)
                    fake = attribute_value
                setattr(module, attribute_name, fake)
                self.changes.append((module, attribute_name, attribute_value))

    def get_whitelist(self):
        """
        Combine all whitelists which could be passed via hook and CLI

        Returns
        -------
        List[str]
        """
        values = [__name__]
        other = self.config.hook.pytest_never_sleep_whitelist()
        if other:
            values.extend(other)
        values.extend(self.config.option.whitelist)
        return values

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
        frame = inspect.currentframe().f_back.f_back
        for _ in range(LIMIT_STACK_INSPECTION):
            if frame.f_globals.get('__name__') == __name__:
                frame = frame.f_back
                continue
            return frame
