==========================================================
How to change the default event loop scope of all fixtures
==========================================================
The :ref:`configuration/asyncio_default_fixture_loop_scope` configuration option sets the default event loop scope for asynchronous fixtures. The following code snippets configure all fixtures to run in a session-scoped loop by default:

.. tabs::

   .. tab:: pytest.ini

      .. code-block:: ini

         [pytest]
         asyncio_default_fixture_loop_scope = session

   .. tab:: pyproject.toml

      .. code-block:: toml

         [tool.pytest.ini_options]
         asyncio_default_fixture_loop_scope = "session"

   .. tab:: setup.cfg

      .. code-block:: ini

         [tool:pytest]
         asyncio_default_fixture_loop_scope = session

Please refer to :ref:`configuration/asyncio_default_fixture_loop_scope` for other valid scopes.
