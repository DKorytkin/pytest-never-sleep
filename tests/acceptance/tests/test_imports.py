from tests.acceptance.diff_imports.import_from_module import do_some_stuff


def test_first():
    do_some_stuff()


def test_two(do):
    assert do
