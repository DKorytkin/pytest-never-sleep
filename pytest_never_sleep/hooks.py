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
    >>>     return "root_dir/folder/one/", "root_dir/folder/two/file.py"
    """


@pytest.hookspec(firstresult=True)
def pytest_never_sleep_message_format(frame):
    """
    In this hook you can overwrite default message format on your own

    Parameters
    ----------
    frame: tuple
        (
            <frame object>,
            "path_to_module.py",
            line_number,
            function_name,
            ["stack", "of", "calls"]
        )

    Returns
    -------
    str
    """
