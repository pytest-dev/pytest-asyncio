import asyncio
import pytest


@pytest.mark.asyncio
@asyncio.coroutine
def test_dependent_fixture(dependent_fixture):
    """Test a dependent fixture."""
    yield from asyncio.sleep(0.1)


@pytest.fixture
def assert_no_global_loop(event_loop):
    """A dummy fixture, to assert the event loop policy has been set."""
    assert event_loop

    with pytest.raises(NotImplementedError):
        asyncio.get_event_loop()
    yield
    with pytest.raises(NotImplementedError):
        asyncio.get_event_loop()


@pytest.mark.asyncio(forbid_global_loop=True)
@asyncio.coroutine
def test_fixture_no_global_loop(assert_no_global_loop):
    """The fixture will assert the correct policy has been set."""
    pass