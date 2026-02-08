=======================
How to test with uvloop
=======================

Replace the default event loop policy in your *conftest.py* to run all async
tests with `uvloop <https://github.com/MagicStack/uvloop>`_.

.. note::

    ``uvloop.EventLoopPolicy`` is deprecated since uvloop 0.21 and will be
    removed in Python 3.16 (see `uvloop#637
    <https://github.com/MagicStack/uvloop/issues/637>`_). The
    ``event_loop_policy`` fixture relies on event loop policies, which are
    themselves deprecated as of Python 3.14. A future version of
    pytest-asyncio will provide a non-policy-based mechanism for configuring
    custom event loops (see `#1164
    <https://github.com/pytest-dev/pytest-asyncio/issues/1164>`_).

    The pattern below works with current versions of uvloop (< 1.0) and
    Python (< 3.16) by wrapping ``uvloop.new_event_loop`` in a minimal
    custom policy, avoiding the deprecated ``uvloop.EventLoopPolicy``.

.. code-block:: python

    import asyncio
    import warnings

    import pytest
    import uvloop

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        from asyncio import DefaultEventLoopPolicy


    class UvloopPolicy(DefaultEventLoopPolicy):
        """Minimal policy that uses uvloop's event loop factory."""

        def new_event_loop(self):
            return uvloop.new_event_loop()


    @pytest.fixture(scope="session")
    def event_loop_policy():
        return UvloopPolicy()

You may choose to limit the scope of the fixture to *package,* *module,* or
*class,* if you only want a subset of your tests to run with uvloop.
