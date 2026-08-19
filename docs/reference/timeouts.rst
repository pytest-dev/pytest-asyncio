========
Timeouts
========

Enable ``--asyncio-cooperative-timeouts`` or set
``asyncio_cooperative_timeouts = true`` to deliver pytest-timeout signal
failures by cancelling the active asynchronous test or fixture. This requires
a pytest-timeout version providing ``pytest_timeout_expired``. Cooperative
cleanup can then run before pytest reports the original timeout.
pytest-timeout still controls the configured duration, covered test phases,
debugger detection, and timeout diagnostics.

Cancellation waits for the event loop and coroutine to cooperate. It cannot
stop a callback that blocks indefinitely or a task that refuses cancellation.
Use pytest-timeout's ``thread`` method or an independent process watchdog when
the process must be terminated. A timeout during final event-loop shutdown
stops that shutdown and closes the loop; remaining resource cleanup may be
incomplete.

Custom Python 3.10 task factories may return tasks without cancellation
counters. For those tasks, an escaping ``CancelledError`` is preserved and
the timeout is chained to it, because the runner cannot reliably distinguish
timeout cancellation from another cancellation request.

Cooperative timeouts are disabled by default. Enabling them without a
compatible pytest-timeout plugin is a configuration error. The integration
does not take over runners managed by other async plugins or synchronous tests
that call ``asyncio.run()`` themselves.
