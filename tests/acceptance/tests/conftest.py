import os
import sys
import pytest


sys.path.append(os.path.dirname(__file__))


@pytest.fixture
def do():
    from tests.acceptance.diff_imports.import_from_function import do
    return do()
