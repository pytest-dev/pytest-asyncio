=============
Configuration
=============

.. _configuration/asyncio_default_fixture_loop_scope:

asyncio_default_fixture_loop_scope
==================================
Determines the default event loop scope of asynchronous fixtures. When this configuration option is unset, it defaults to the fixture scope. In future versions of pytest-asyncio, the value will default to ``function`` when unset. Possible values are: ``function``, ``class``, ``module``, ``package``, ``session``

.. _configuration/asyncio_default_test_loop_scope:

asyncio_default_test_loop_scope
===============================
Determines the default event loop scope of asynchronous tests. When this configuration option is unset, it default to function scope. Possible values are: ``function``, ``class``, ``module``, ``package``, ``session``

.. _configuration/asyncio_debug:

asyncio_debug
=============
Enables `asyncio debug mode <https://docs.python.org/3/library/asyncio-dev.html#debug-mode>`_ for the default event loop used by asynchronous tests and fixtures.

The debug mode can be set by the ``asyncio_debug`` configuration option in the `configuration file
<https://docs.pytest.org/en/latest/reference/customize.html>`_:

.. code-block:: ini

   # pytest.ini
   [pytest]
   asyncio_debug = true

The value can also be set via the ``--asyncio-debug`` command-line option:

.. code-block:: bash

   $ pytest tests --asyncio-debug

By default, asyncio debug mode is disabled.

asyncio_mode
============
The pytest-asyncio mode can be set by the ``asyncio_mode`` configuration option in the `configuration file
<https://docs.pytest.org/en/latest/reference/customize.html>`_:

.. code-block:: ini

   # pytest.ini
   [pytest]
   asyncio_mode = auto

The value can also be set via the ``--asyncio-mode`` command-line option:

.. code-block:: bash

   $ pytest tests --asyncio-mode=strict


If the asyncio mode is set in both the pytest configuration file and the command-line option, the command-line option takes precedence. If no asyncio mode is specified, the mode defaults to `strict`.
