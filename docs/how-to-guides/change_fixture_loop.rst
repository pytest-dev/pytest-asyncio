===============================================
How to change the event loop scope of a fixture
===============================================
The event loop scope of an asynchronous fixture is specified via the *loop_scope* keyword argument to :ref:`pytest_asyncio.fixture <decorators/pytest_asyncio_fixture>`. The following fixture runs in the module-scoped event loop:

.. include:: change_fixture_loop_example.py
    :code: python
