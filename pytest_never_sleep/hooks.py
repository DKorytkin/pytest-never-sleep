import pytest

# These are specifications, so no implementation:
# pylint: disable=unused-argument


@pytest.hookspec(firstresult=True)
def pytest_never_sleep_whitelist():
    """
    This hook adds ability to adding own paths where `time.sleep` allowed
    and plugin will skip raising errors

    Returns
    -------
    Tuple[str]

    Usage in conftest:
    >>> def pytest_never_sleep_whitelist():
    >>>     return "root_dir.folder.module", "root_dir.folder_two."
    """


@pytest.hookspec(firstresult=True)
def pytest_never_sleep_message_format(frame):
    """
    In this hook you can overwrite default message format on your own

    Allowed methods:
        f_back - next outer frame object
        f_builtins - builtins namespace seen by this frame
        f_code - code object being executed in this frame
        f_globals - global namespace seen by this frame
        f_lasti - index of last attempted instruction in bytecode
        f_lineno - current line number in Python source code
        f_locals - local namespace seen by this frame
        f_trace - tracing function for this frame, or None

    https://docs.python.org/3/library/inspect.html

    Parameters
    ----------
    frame: frame

    Returns
    -------
    str

    Usage in conftest:
    >>> def pytest_never_sleep_message_format(frame):
    >>>     return "{}:{}".format(frame.f_code.co_filename, frame.f_code.co_firstlineno)
    """
