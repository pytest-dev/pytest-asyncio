.. _decorators/pytest_asyncio_fixture:

==========
Decorators
==========
The ``@pytest_asyncio.fixture`` decorator allows coroutines and async generator functions to be used as pytest fixtures.

The decorator takes all arguments supported by `@pytest.fixture`.
Additionally, ``@pytest_asyncio.fixture`` supports the *loop_scope* keyword argument, which selects the event loop in which the fixture is run (see :ref:`concepts/event_loops`).
The default event loop scope is *function* scope.
Possible loop scopes are *session,* *package,* *module,* *class,* and *function*.

The *loop_scope* of a fixture can be chosen independently from its caching *scope*.
However, the event loop scope must be larger or the same as the fixture's caching scope.
In other words, it's possible to reevaluate an async fixture multiple times within the same event loop, but it's not possible to switch out the running event loop in an async fixture.

Examples:

.. include:: pytest_asyncio_fixture_example.py
    :code: python

*auto* mode automatically converts coroutines and async generator functions declared with the standard ``@pytest.fixture`` decorator to pytest-asyncio fixtures.
