========
Warnings
========

Unhandled event loop exceptions
===============================

``pytest_asyncio.PytestAsyncioUnhandledExceptionWarning`` reports exceptions that
an event loop would otherwise send to its default exception handler. For example,
an exception raised by a callback scheduled with ``loop.call_soon`` produces a
warning with the loop's message and the exception traceback.

The handler is installed only on loops created by pytest-asyncio that do not
already have a custom exception handler. A handler installed by a loop factory
or by a test continues to receive its own events. Handled task exceptions and
normal task cancellation do not produce warnings.

Warnings are emitted after the pytest setup, call, or teardown phase that runs
the loop, rather than from inside an asyncio callback. This allows pytest warning
filters, including ``error``, to work normally. An exception raised while a
shared runner shuts down is reported during its teardown; it is not necessarily
attributed to the test that originally created the task.

To treat these warnings as errors::

    pytest -W error::pytest_asyncio.PytestAsyncioUnhandledExceptionWarning

The same category can be used with pytest's ``filterwarnings`` configuration or
mark. Warnings are queued until a pytest phase completes, so ``pytest.warns``
inside an async test does not capture them as they occur.
