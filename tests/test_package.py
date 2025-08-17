import pytest_asyncio


def test_package_exposes_version():
    assert pytest_asyncio.__version__
