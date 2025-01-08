=======================================================
How to change the default event loop scope of all tests
=======================================================
The :ref:`configuration/asyncio_default_test_loop_scope` configuration option sets the default event loop scope for asynchronous tests. The following code snippets configure all tests to run in a session-scoped loop by default:

.. code-block:: ini
    :caption: pytest.ini

    [pytest]
    asyncio_default_test_loop_scope = session

.. code-block:: toml
    :caption: pyproject.toml

    [tool.pytest.ini_options]
    asyncio_default_test_loop_scope = "session"

.. code-block:: ini
    :caption: setup.cfg

    [tool:pytest]
    asyncio_default_test_loop_scope = session

Please refer to :ref:`configuration/asyncio_default_test_loop_scope` for other valid scopes.
