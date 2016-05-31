import asyncio
import pytest
import pytest_asyncio

pytest_plugins = "pytester"


@pytest_asyncio.async_fixture
@asyncio.coroutine
def hello(loop):
    yield from asyncio.sleep(0, loop=loop)
    return 'hello'


def test_async_fixture(hello):
    assert hello == 'hello'


def test_forbidden_global_loop_raises(testdir):
    testdir.makepyfile("""
        import asyncio
        import pytest_asyncio

        @pytest_asyncio.async_fixture
        @asyncio.coroutine
        def should_raise():
            yield from asyncio.sleep(0)

        def test_should_raise(should_raise):
            pass
    """)
    result = testdir.runpytest()
    result.stdout.fnmatch_lines(["*pytest_asyncio.exceptions.MissingLoopFixture*"])



@pytest_asyncio.async_fixture(accept_global_loop=True)
@asyncio.coroutine
def using_global_loop():
    yield from asyncio.sleep(0)
    return 'ok'


def test_accepted_global_loop(using_global_loop):
    assert using_global_loop == 'ok'
