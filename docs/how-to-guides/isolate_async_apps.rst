===============================================
How to isolate async applications in your tests
===============================================

Async web frameworks (FastAPI, Quart, aiohttp) are typically tested by importing an ``app`` object and overriding its dependencies.  Two subtle isolation traps can cause tests to pass in isolation but fail in a suite, or leak state across tests.

This guide shows how to use ``pytest-asyncio`` fixtures to avoid both.


Trap 1: Stale module-level imports after reload
-----------------------------------------------

If your test module imports the application at the top level:

.. code-block:: python

    # test_a.py
    from api.main import app  # module-level import

    @pytest.mark.asyncio
    async def test_a():
        ...

and another test reloads the module to pick up configuration changes:

.. code-block:: python

    # test_b.py
    import importlib
    import api.main
    importlib.reload(api.main)  # creates a NEW app object

then ``test_a`` still holds a reference to the *old* ``app`` object, while ``test_b`` sees the *new* one.  Dependency overrides and state diverge silently.

**Fix:** Import ``app`` inside the fixture or test function so you always get the current module state:

.. include:: isolate_async_apps_example.py
    :code: python
    :start-after: # -- FIX 1: fixture-scoped import
    :end-before: # -- FIX 2: temporary directories

Trap 2: Default file-system paths in constructors
-------------------------------------------------

An async service that accepts an optional path:

.. code-block:: python

    class UploadService:
        def __init__(self, upload_dir: Path = UPLOAD_DIR):
            self.upload_dir = upload_dir

will reuse the same default directory across every test that forgets to override it.  Files written by one test are visible to the next.

**Fix:** Always inject a temporary directory via a fixture, even when the parameter is "optional":

.. include:: isolate_async_apps_example.py
    :code: python
    :start-after: # -- FIX 2: temporary directories
    :end-before: # -- end of example
