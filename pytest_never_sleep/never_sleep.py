import contextlib
import inspect
import sys
import time

_true_time = time
_true_time_sleep = time.sleep
_real_time_sleep_ids = (id(_true_time), id(_true_time_sleep))


TARGET_MODULE_NAME = "time"
TARGET_METHOD_NAME = "sleep"
TARGET_NAME = "{}.{}".format(TARGET_MODULE_NAME, TARGET_METHOD_NAME)
LIMIT_STACK_INSPECTION = 5
DEFAULT_IGNORE_LIST = (
    TARGET_MODULE_NAME,
    "pytest_never_sleep",
    "py",
    "pytest",
    "_pytest",
    "nose.plugins",
    "datetime",
    "_datetime",
)


class TimeSleepUsageError(RuntimeError):
    """
    The error which raises when `time.sleep` unexpectedly uses
    """


@contextlib.contextmanager
def using_real_time_sleep(fake_sleep):
    """
    Needs for temporary allow `time.sleep` using

    Parameters
    ----------
    fake_sleep: FakeSleep
    """
    old_value = fake_sleep.is_allow_time_sleep_by_default
    fake_sleep.is_allow_time_sleep_by_default = True
    try:
        yield
    finally:
        fake_sleep.is_allow_time_sleep_by_default = old_value


@contextlib.contextmanager
def using_fake_time_sleep(fake_sleep):
    """
    Needs for temporary not allow `time.sleep` using

    Parameters
    ----------
    fake_sleep: FakeSleep
    """
    old_value = fake_sleep.is_allow_time_sleep_by_default
    fake_sleep.is_allow_time_sleep_by_default = False
    try:
        yield
    finally:
        fake_sleep.is_allow_time_sleep_by_default = old_value


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


def get_target_sys_modules(whitelist):
    """
    Parameters
    ----------
    whitelist: tuple[str]

    Returns
    -------
    generator
    """
    for mod_name, module in dict(sys.modules).items():
        if mod_name is None or module is None or mod_name == __name__:
            continue
        if mod_name.startswith(DEFAULT_IGNORE_LIST) or mod_name.startswith(whitelist):
            continue
        yield module


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

    def __contains__(self, module):
        return self.get(module)

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


class FakeSleep(object):
    """
    Fake implementation of `time.sleep`
    """

    def __init__(
        self,
        whitelist=None,
        get_message=None,
        allow_time_sleep=None,
        pytest_config=None,
    ):
        """
        Parameters
        ----------
        whitelist: tuple[str]
        get_message: Callable
            pytest_never_sleep_message_format hook
        allow_time_sleep: bool
        """
        self.whitelist = whitelist
        self.get_message = get_message
        self.is_allow_time_sleep_by_default = allow_time_sleep
        self.pytest_config = pytest_config
        self.cache = Cache()

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

    def should_use_true_sleep(self):
        """
        Returns
        -------
        bool
        """
        if self.is_allow_time_sleep_by_default:
            return True
        frame = self.get_current_frame()
        return frame.f_globals.get("__name__", "").startswith(self.whitelist)

    def sleep(self, seconds):
        """
        Own implementation of `time.sleep` which track where it was called and raises an error if
        this path not in the whitelist

        Parameters
        ----------
        seconds: int | float
        """
        if not self.should_use_true_sleep():
            frame = self.get_current_frame()
            msg = self.get_message(config=self.pytest_config, frame=frame)
            raise TimeSleepUsageError(msg)
        _true_time_sleep(seconds)

    def unpatch_time_sleep(self):
        """
        Checks all sys.modules if it has imported `time.sleep` and it already patched
        Will back origin `time.sleep`
        """
        for module in get_target_sys_modules(self.whitelist):
            for attribute_name, attribute_value in get_target_attributes(module):
                if id(attribute_value) in _real_time_sleep_ids:
                    continue

                current_instance = module  # from time import sleep
                if attribute_name == TARGET_MODULE_NAME and getattr(
                    attribute_value, TARGET_METHOD_NAME, None
                ):
                    current_instance = attribute_value  # import time

                if isinstance(current_instance, FakeSleep):
                    setattr(current_instance, TARGET_METHOD_NAME, _true_time_sleep)

    def patch_time_sleep(self):
        """
        Checks all sys.modules if it has imported `time.sleep`
        Will apply patch for `time.sleep`

        For example:
        my_custome_module.py
        >>> import time
        >>> def foo():
        >>>     time.sleep(1)

        >>> from time import sleep
        >>> def foo():
        >>>     sleep(1)

        In all cases `sleep` will equall <FakeSleep>
        """
        for module in get_target_sys_modules(self.whitelist):
            if module in self.cache:
                continue

            module_time_sleep_attrs = self.cache.add(module)
            for attribute_name, attribute_value in module_time_sleep_attrs:
                fake = self
                if attribute_name == TARGET_MODULE_NAME:
                    setattr(attribute_value, TARGET_METHOD_NAME, fake)
                    fake = attribute_value
                setattr(module, attribute_name, fake)

    def __call__(self, seconds):
        self.sleep(seconds)
