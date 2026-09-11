"""
Run each async fixture in one asyncio task, from setup to teardown.

pytest-asyncio uses this module when
asyncio_experimental_task_per_fixture is enabled.

pytest calls a fixture's setup, the test and the fixture's teardown as
separate synchronous calls. A fixture's task stays alive between those
calls, so the context managers around its yield are entered and exited
in the same task.
"""

from __future__ import annotations

import asyncio
import contextlib
import contextvars
import dataclasses
import functools
from collections.abc import AsyncGenerator, Callable, Coroutine, Generator
from typing import Any, Generic, NoReturn, TypeVar

_T = TypeVar("_T")


@dataclasses.dataclass(frozen=True)
class FixtureSetup(Generic[_T]):
    value: _T
    context: contextvars.Context


class FixtureTask(Generic[_T]):
    """
    Run setup and teardown in one task, waiting for pytest between them.

    Constructing it starts the task. Between setup and teardown the
    fixture is held: suspended at its yield while pytest uses its value.
    A fixture cancelled while held (e.g., by its task group or timeout)
    stays held until pytest has torn down its dependents.
    """

    def __init__(
        self,
        gen: AsyncGenerator[_T],
        create_task: Callable[[Coroutine[object, object, None]], asyncio.Task[None]],
        *,
        name: str,
        loop: asyncio.AbstractEventLoop,
        on_cancelled_while_held: Callable[[], None],
    ) -> None:
        __tracebackhide__ = True
        self._gen = gen
        self.name = name
        self._on_cancelled_while_held = on_cancelled_while_held
        self.cancelled_while_held = False
        self.setup: asyncio.Future[FixtureSetup[_T]] = loop.create_future()
        self._teardown_requested = asyncio.Event()
        self.task = create_task(self._run())

    def setup_result(self) -> FixtureSetup[_T]:
        __tracebackhide__ = True
        if not self.setup.done():
            self.task.result()
        return self.setup.result()

    def cancel_setup(self) -> None:
        # A fixture that has yielded is torn down, not cancelled.
        if not self.setup.done():
            self.task.cancel()

    def request_teardown(self) -> None:
        self._teardown_requested.set()

    async def _run(self) -> None:
        try:
            value = await anext(self._gen)
        except StopAsyncIteration:
            if self._teardown_requested.is_set():
                # The setup was interrupted: pytest expects no value.
                return
            raise
        self.setup.set_result(FixtureSetup(value, contextvars.copy_context()))
        cancellation = await self._wait_for_teardown_request()
        try:
            if cancellation is None:
                await anext(self._gen)
            else:
                await self._gen.athrow(cancellation)
        except StopAsyncIteration:
            return
        try:
            raise ValueError(
                f"Async generator fixture {self.name!r} didn't stop. Yield only once."
            )
        finally:
            # Exit the generator's context managers in this task.
            await self._gen.aclose()

    async def _wait_for_teardown_request(self) -> asyncio.CancelledError | None:
        cancellation: asyncio.CancelledError | None = None
        while not self._teardown_requested.is_set():
            try:
                await self._teardown_requested.wait()
            except asyncio.CancelledError as exc:
                # Raise the first cancellation at the yield later, as
                # asyncio.TaskGroup does, because the fixture's
                # dependents still use the fixture. Do not call
                # uncancel(): contexts that exit at the yield read the
                # cancellation count.
                if cancellation is None:
                    # Hide this wait from the traceback at the yield.
                    cancellation = exc.with_traceback(None)
                    if not self._teardown_requested.is_set():
                        self.cancelled_while_held = True
                        self._on_cancelled_while_held()
        return cancellation


class TaskRunner:
    """
    Run async fixtures and tests in tasks on an asyncio.Runner's loop.

    If an exception such as Ctrl-C escapes the loop during a call, the
    call cancels its task. It then waits for the task's cleanup while
    the task's fixtures are still set up. A second interruption ends
    that wait.

    When a held fixture is cancelled, the runner cancels the running
    test or fixture setup. It starts no new one until the fixture is
    torn down.
    """

    def __init__(self, asyncio_runner: asyncio.Runner) -> None:
        self._asyncio_runner = asyncio_runner
        self._loop = asyncio_runner.get_loop()
        # The loop keeps only weak references to its tasks. A task
        # outlives the call that created it if its cleanup is
        # interrupted.
        self._unfinished_tasks: set[asyncio.Task[Any]] = set()
        self._live_fixtures: set[FixtureTask[Any]] = set()
        self._cancel_running_test_or_setup: Callable[[], object] | None = None
        self._last_run_was_interrupted = False

    def run(
        self,
        func: Callable[[], Coroutine[object, object, _T]],
        *,
        context: contextvars.Context,
        name: str,
    ) -> _T:
        __tracebackhide__ = True
        if (refusal_reason := self.refusal_reason) is not None:
            raise RuntimeError(refusal_reason)
        task = self._create_task(func(), context=context, name=name)
        with self._cancellable_by_held_fixtures(task.cancel):
            try:
                self._run_loop_until_any_done(task)
            except BaseException as interruption:
                task.cancel()
                self._join_and_raise(task, interruption)
        return task.result()

    def start_fixture(
        self,
        gen: AsyncGenerator[_T],
        *,
        context: contextvars.Context,
        name: str,
    ) -> tuple[FixtureTask[_T], FixtureSetup[_T]]:
        __tracebackhide__ = True
        if (refusal_reason := self.refusal_reason) is not None:
            raise RuntimeError(refusal_reason)
        fixture = FixtureTask(
            gen,
            functools.partial(self._create_task, context=context, name=name),
            name=name,
            loop=self._loop,
            on_cancelled_while_held=self._on_held_fixture_cancelled,
        )
        self._live_fixtures.add(fixture)
        fixture.task.add_done_callback(lambda _: self._live_fixtures.discard(fixture))
        with self._cancellable_by_held_fixtures(fixture.cancel_setup):
            try:
                self._run_loop_until_any_done(fixture.task, fixture.setup)
            except BaseException as interruption:
                # Pytest never receives this fixture. If it still
                # yields, tear it down now, while its dependencies
                # exist.
                fixture.request_teardown()
                fixture.cancel_setup()
                self._join_and_raise(fixture.task, interruption)
        return fixture, fixture.setup_result()

    def finish_fixture(self, fixture: FixtureTask[_T]) -> None:
        __tracebackhide__ = True
        fixture.request_teardown()
        try:
            self._run_loop_until_any_done(fixture.task)
        except BaseException as interruption:
            fixture.task.cancel()
            self._join_and_raise(fixture.task, interruption)
        fixture.task.result()

    def prepare_loop_close(self) -> None:
        try:
            self._discard_stale_stop()
        finally:
            # A fixture that pytest never finalized would stay held.
            for fixture in self._live_fixtures:
                fixture.request_teardown()

    @property
    def refusal_reason(self) -> str | None:
        """Why new work is refused: a held fixture was cancelled."""
        for fixture in self._live_fixtures:
            if fixture.cancelled_while_held:
                return (
                    f"Async fixture {fixture.name!r} was cancelled while waiting for "
                    "teardown. Until it is torn down, this event loop does not accept "
                    "new async tests or fixture setups."
                )
        return None

    def _create_task(
        self,
        coro: Coroutine[object, object, _T],
        *,
        context: contextvars.Context,
        name: str,
    ) -> asyncio.Task[_T]:
        __tracebackhide__ = True
        try:
            task = self._loop.create_task(coro, context=context)
        except BaseException:
            coro.close()  # A task factory that fails may not close it.
            raise
        task.set_name(name)  # Some task factories do not accept a name.
        self._unfinished_tasks.add(task)
        task.add_done_callback(self._unfinished_tasks.discard)
        return task

    @contextlib.contextmanager
    def _cancellable_by_held_fixtures(
        self,
        cancel: Callable[[], object],
    ) -> Generator[None]:
        self._cancel_running_test_or_setup = cancel
        try:
            yield
        finally:
            self._cancel_running_test_or_setup = None

    def _on_held_fixture_cancelled(self) -> None:
        if self._cancel_running_test_or_setup is not None:
            self._cancel_running_test_or_setup()

    def _join_and_raise(
        self,
        task: asyncio.Task[object],
        interruption: BaseException,
    ) -> NoReturn:
        """
        Join the cancelled task and raise its error or the interruption.

        A second interruption is raised unchanged.
        """
        __tracebackhide__ = True
        try:
            self._run_loop_until_any_done(task)
        except asyncio.CancelledError:
            # Keep the interruption. If a cancelled wait replaced
            # Ctrl-C, pytest would report a test failure and run the
            # next test.
            raise interruption from None
        except BaseException as second_interruption:
            if _error_raised_by(task) is not second_interruption:
                raise
        failure = _error_raised_by(task)
        if failure is None or failure is interruption:
            raise interruption
        failure.add_note(
            f"Raised during cleanup after pytest-asyncio received: {interruption!r}"
        )
        raise failure

    def _run_loop_until_any_done(
        self,
        *futures: asyncio.Future[Any],
    ) -> None:
        """
        Ctrl-C cancels this wait and is raised here.

        It does not cancel the test or fixture.
        """
        __tracebackhide__ = True
        self._discard_stale_stop()
        try:
            self._asyncio_runner.run(
                asyncio.wait(futures, return_when=asyncio.FIRST_COMPLETED)
            )
        except BaseException as interruption:
            self._last_run_was_interrupted = True
            if isinstance(interruption, asyncio.CancelledError):
                # Runner.run raises Ctrl-C as KeyboardInterrupt.
                interruption.add_note(
                    "pytest-asyncio's internal wait was cancelled, e.g. by code "
                    "that cancels every task. Cancel only tasks that your code "
                    "created."
                )
            raise

    def _discard_stale_stop(self) -> None:
        """
        Work around CPython gh-158406.

        An interrupted run can leave a loop stop queued, which would end
        the next run early. Remove this once the oldest supported Python
        has a fix.
        """
        if self._last_run_was_interrupted:
            self._loop.stop()
            self._loop.run_forever()
            self._last_run_was_interrupted = False


def _error_raised_by(task: asyncio.Task[object]) -> BaseException | None:
    """
    Return the exception that ended the task, unless it was cancelled.

    asyncio stores a task's KeyboardInterrupt or SystemExit in the task
    and also raises it out of the loop. The exception that interrupted a
    wait can therefore be this one.
    """
    if not task.done() or task.cancelled():
        return None
    return task.exception()
