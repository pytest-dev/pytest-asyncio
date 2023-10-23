==========
Decorators
==========
Asynchronous fixtures are defined just like ordinary pytest fixtures, except they should be decorated with ``@pytest_asyncio.fixture``.

.. include:: fixture_strict_mode_example.py
    :code: python

All scopes are supported, but if you use a non-function scope you will need
to redefine the ``event_loop`` fixture to have the same or broader scope.
Async fixtures need the event loop, and so must have the same or narrower scope
than the ``event_loop`` fixture.

*auto* mode automatically converts async fixtures declared with the
standard ``@pytest.fixture`` decorator to *asyncio-driven* versions.
