from pytest_asyncio import is_async_test


def pytest_collection_modifyitems(items):
    for item in items:
        if is_async_test(item):
            pass
