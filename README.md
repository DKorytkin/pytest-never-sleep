# pytest-never-sleep
This plugin helps to avoid adding tests without mock time.sleep. That potentially will save wasted time on test execution and money as well if they run in the cloud

## Installation

```shell
pip install pytest-never-sleep
```

## Usage

Run tests with flag `--disable-sleep`

```shell
pytest --disable-sleep tests/acceptance/tests/test_imports.py
```
As result, if some tests use `time.sleep` somewhere it will rise `TimeSleepUsageError`

Like in this example:

```python
====================== FAILURES ======================
_____________________ test_first _____________________

    @pytest.fixture
    def do():
        from diff_imports.import_from_function import do

>       return do()

do         = <function do at 0x10748ec20>

example/tests/conftest.py:13:
______________________________________________________
example/diff_imports/import_from_function.py:5: in do
    sleep(1)
pytest_never_sleep/never_sleep.py:221: in __call__
    self.sleep(seconds)
______________________________________________________
    def sleep(self, seconds):
        """
        Own implementation of `time.sleep` which track where it was called and raises an error if
        this path not in the whitelist

        Parameters
        ----------
        seconds: int | float
        """
        if not self._allow_time_sleep:
            frame = self.get_current_frame()
            msg = self.get_message(frame=frame)
>           raise TimeSleepUsageError(msg)
E           pytest_never_sleep.never_sleep.TimeSleepUsageError: Method `do` uses `time.sleep`.
E           It can lead to degradation of test runtime, 
E           check 'example/diff_imports/import_from_function.py' line 4 and use mock for that peace of code.
```

### Flags

- `--disable-sleep` - Disable `time.sleep` by default for all tests.
- `--whitelist` - Allow `time.sleep` to these modules.

### Fixtures

#### - `disable_time_sleep`

This fixture turns off `time.sleep` just for particular test

```python
import pytest


@pytest.mark.usefixtures("disable_time_sleep")
def test_first():
    ...
```

#### - `enable_time_sleep`

This fixture turns on `time.sleep` just for a particular test, could be useful if you use flag `--disable-sleep`

```python
import pytest


@pytest.mark.usefixtures("enable_time_sleep")
def test_second():
    ...
```


### Markers

#### - `enable_time_sleep`

This marker has the same behavior with `enable_time_sleep` fixture

```python
import pytest


@pytest.mark.enable_time_sleep
def test_one():
    ...
```

#### - `disable_time_sleep`

This marker has the same behavior with `disable_time_sleep` fixture

```python
import pytest


@pytest.mark.disable_time_sleep
def test_second():
    ...
```

### Hooks

#### `pytest_never_sleep_message_format`

In this hook, you can overwrite the default message format on your own

```python
def pytest_never_sleep_message_format(config, frame):
    return "{}:{}".format(frame.f_code.co_filename, frame.f_code.co_firstlineno)
```

#### `pytest_never_sleep_whitelist`

This hook adds the ability to adding own paths where `time.sleep` allowed, 
and the plugin will skip raising errors

```python
def pytest_never_sleep_whitelist():
    return "root_dir.folder.one", "root_dir.folder.two.file"
```
