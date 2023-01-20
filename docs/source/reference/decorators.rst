==========
Decorators
==========
Asynchronous fixtures are defined just like ordinary pytest fixtures, except they should be decorated with ``@pytest_asyncio.fixture``.

.. code-block:: python3

    import pytest_asyncio


    @pytest_asyncio.fixture
    async def async_gen_fixture():
        await asyncio.sleep(0.1)
        yield "a value"


    @pytest_asyncio.fixture(scope="module")
    async def async_fixture():
        return await asyncio.sleep(0.1)

All scopes are supported, but if you use a non-function scope you will need
to redefine the ``event_loop`` fixture to have the same or broader scope.
Async fixtures need the event loop, and so must have the same or narrower scope
than the ``event_loop`` fixture.

*auto* mode automatically converts async fixtures declared with the
standard ``@pytest.fixture`` decorator to *asyncio-driven* versions.
