from __future__ import annotations

import asyncio
import contextvars
import functools
import inspect
import signal
import sys
from collections.abc import Callable
from textwrap import dedent
from types import CoroutineType
from typing import Literal

import pytest
from pytest import Pytester

from pytest_asyncio._timeout import pytest_timeout_expired, run
from pytest_asyncio.plugin import _synchronize_coroutine

pytestmark = pytest.mark.skipif(
    not hasattr(signal, "SIGALRM"), reason="requires the signal timeout method"
)


@pytest.fixture
def timeout_plugin(request: pytest.FixtureRequest):
    if not request.config.hook.pytest_timeout_expired.has_spec():
        pytest.skip("requires pytest-timeout's signal-expiry hook")


@pytest.fixture
def cooperative_timeout(timeout_plugin: None):
    if sys.version_info < (3, 11):
        pytest.skip("cooperative timeouts require Python 3.11 or newer")


@pytest.mark.parametrize("event", ["timeout", "interrupt"])
def test_startup(event: str, request: pytest.FixtureRequest, cooperative_timeout: None):
    expired = pytest.fail.Exception("original timeout")
    entered = []
    tasks = []

    async def body():
        entered.append(True)
        return 42

    def task_factory(loop, coro, **kwargs):
        loop.set_task_factory(None)

        async def traced():
            return await coro

        task = loop.create_task(traced(), **kwargs)
        tasks.append(task)
        if event == "interrupt":
            signal.raise_signal(signal.SIGINT)
        pytest_timeout_expired(request.node, expired)
        return task

    with asyncio.Runner() as runner:
        runner.get_loop().set_task_factory(task_factory)
        expected = KeyboardInterrupt if event == "interrupt" else type(expired)
        with pytest.raises(expected) as caught:
            run(runner, body, context=contextvars.copy_context(), config=request.config)
        if event == "interrupt":
            runner.run(asyncio.sleep(0))
            assert tasks[0].result() == 42
        else:
            assert caught.value is expired
            assert not entered


@pytest.mark.parametrize("kind", ["synchronous", "partial_subclass"])
def test_creator_context(
    kind: str, request: pytest.FixtureRequest, cooperative_timeout: None
):
    value = contextvars.ContextVar("value", default="caller")
    events = []

    async def body(argument):
        events.append(("body", value.get(), argument))
        value.set("updated")

    def creator(argument):
        events.append(("creator", value.get()))
        return body(argument)

    if hasattr(inspect, "markcoroutinefunction"):
        inspect.markcoroutinefunction(creator)

    class SyncPartial(functools.partial):
        def __call__(self, *args, **kwargs):
            events.append(("creator", value.get()))
            return super().__call__(*args, **kwargs)

    functions: dict[str, Callable[..., CoroutineType]] = {
        "synchronous": creator,
        "partial_subclass": SyncPartial(body),
    }
    context = contextvars.copy_context()
    context.run(value.set, "task")
    with asyncio.Runner() as runner:
        synchronized = _synchronize_coroutine(
            functions[kind], runner, context, request.config
        )
        synchronized(42)
    assert events == [("creator", "caller"), ("body", "task", 42)]
    assert value.get() == "caller"
    assert context.get(value) == "updated"


@pytest.mark.parametrize(
    ("cleanup", "expected"),
    [
        (None, pytest.fail.Exception),
        (pytest.xfail.Exception("cleanup xfail"), pytest.fail.Exception),
        (ValueError("cleanup error"), pytest.fail.Exception),
        ("interrupt", KeyboardInterrupt),
        (
            pytest.exit.Exception("requested exit", returncode=4),
            pytest.exit.Exception,
        ),
        (SystemExit(7), SystemExit),
        ("cancel", asyncio.CancelledError),
    ],
)
def test_cleanup(
    cleanup: BaseException | Literal["interrupt", "cancel"] | None,
    expected: type[BaseException],
    request: pytest.FixtureRequest,
    cooperative_timeout: None,
):
    expired = pytest.fail.Exception("original timeout")
    cancelled = []

    async def body():
        loop = asyncio.get_running_loop()
        loop.call_soon(pytest_timeout_expired, request.node, expired)
        try:
            # Allow expiry, delivery, and cancellation turns, but never hang if
            # delivery breaks. The assertion below verifies cancellation ran.
            for _ in range(5):
                await asyncio.sleep(0)
        except asyncio.CancelledError as cancellation:
            cancelled.append(True)
            if cleanup == "interrupt":
                signal.raise_signal(signal.SIGINT)
            elif cleanup == "cancel":
                task = asyncio.current_task()
                assert task is not None
                task.cancel()
            elif cleanup is not None:
                raise cleanup from cancellation
            await asyncio.sleep(0)

    with asyncio.Runner() as runner, pytest.raises(expected) as caught:
        run(runner, body, context=contextvars.copy_context(), config=request.config)
    assert cancelled
    if cleanup == "cancel":
        assert caught.value.__cause__ is expired
    elif cleanup != "interrupt":
        assert caught.value is (
            expired if expected is pytest.fail.Exception else cleanup
        )


def test_signal_timeout_preserves_shared_loop(
    pytester: Pytester, cooperative_timeout: None, monkeypatch: pytest.MonkeyPatch
):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(dedent("""\
        import asyncio
        import functools
        import signal
        import time
        import pytest

        pytest_plugins = "pytest_timeout"

        cleaned = []

        async def application_wait():
            await asyncio.Future()

        @pytest.mark.timeout(0.1, method="signal", func_only=True)
        @pytest.mark.asyncio(loop_scope="module")
        async def timeout(trigger="timer"):
            loop = asyncio.get_running_loop()
            original = loop.call_soon
            task = asyncio.current_task()

            def reschedule(callback, *args, context=None):
                if getattr(callback, "__self__", None) is task:
                    loop.call_soon = original
                    signal.raise_signal(signal.SIGALRM)
                return original(callback, *args, context=context)

            if trigger == "reschedule":
                loop.call_soon = reschedule
            else:
                loop.call_soon(time.sleep, 0.2)
            try:
                await asyncio.sleep(0)
                await application_wait()
            finally:
                loop.call_soon = original
                cleaned.append(trigger)

        test_timer = functools.wraps(timeout)(functools.partial(timeout))

        class TestTimeout:
            @pytest.mark.timeout(10, method="signal", func_only=True)
            @pytest.mark.asyncio(loop_scope="module")
            async def test_timeout(self):
                await timeout("reschedule")

        @pytest.mark.asyncio(loop_scope="module")
        async def test_later():
            assert cleaned == ["timer", "reschedule"]

        @pytest.mark.timeout(10, method="signal", func_only=True)
        def test_synchronous():
            with pytest.raises(pytest.fail.Exception, match="Timeout"):
                signal.raise_signal(signal.SIGALRM)
        """))
    monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    plugins = ["-p", "pytest_asyncio.plugin"]
    if pytest.version_tuple < (9, 1):
        # Older pytest cannot initialize pytest-timeout's options when loaded late.
        plugins.extend(("-p", "pytest_timeout"))
    result = pytester.runpytest_subprocess(*plugins, "--tb=short", timeout=10)
    result.assert_outcomes(failed=2, passed=2)
    result.stdout.fnmatch_lines(["E *Failed: Timeout*from pytest-timeout.*"] * 2)
    result.stdout.fnmatch_lines(["*in application_wait*", "*CancelledError*"])
    assert "_timeout.py" not in result.stdout.str()


def test_timeout_during_async_cleanup(pytester: Pytester, cooperative_timeout: None):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(dedent("""\
        import asyncio
        import signal
        import threading
        from concurrent.futures import ThreadPoolExecutor
        import pytest
        import pytest_asyncio

        executor = None
        worker = None
        release = threading.Event()

        async def timeout():
            asyncio.get_running_loop().call_soon(signal.raise_signal, signal.SIGALRM)
            await asyncio.Future()

        async def background():
            try:
                await asyncio.Future()
            finally:
                await timeout()

        @pytest_asyncio.fixture
        async def coroutine(phase):
            if phase == "coroutine_setup":
                await timeout()

        @pytest_asyncio.fixture
        async def fixture(phase):
            if phase == "generator_setup":
                await timeout()
            yield
            if phase == "teardown":
                await timeout()

        @pytest.mark.parametrize(
            "phase",
            [
                "coroutine_setup", "generator_setup", "teardown",
                "shutdown", "shutdown_boundary",
            ],
        )
        @pytest.mark.timeout(10, method="signal")
        @pytest.mark.asyncio
        async def test_timeout(phase, coroutine, fixture):
            global executor, worker
            if phase == "shutdown":
                asyncio.create_task(background())
                await asyncio.sleep(0)
            if phase == "shutdown_boundary":
                loop = asyncio.get_running_loop()
                executor = ThreadPoolExecutor()
                loop.set_default_executor(executor)
                worker = executor.submit(release.wait, 5)
                original = loop.shutdown_asyncgens

                async def shutdown_asyncgens():
                    await original()
                    signal.raise_signal(signal.SIGALRM)

                loop.shutdown_asyncgens = shutdown_asyncgens

        def test_later():
            if executor is not None:
                try:
                    assert not worker.done()
                finally:
                    release.set()
                    executor.shutdown(wait=True)
        """))
    result = pytester.runpytest_subprocess(timeout=10)
    result.assert_outcomes(errors=5, passed=4)
    result.stdout.fnmatch_lines(["E *Failed: Timeout*from pytest-timeout.*"] * 5)


@pytest.mark.skipif(sys.version_info >= (3, 11), reason="legacy Python 3.10 behavior")
def test_signal_timeout_on_python310(pytester: Pytester, timeout_plugin: None):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(dedent("""\
        import signal
        import pytest

        @pytest.mark.timeout(10, method="signal", func_only=True)
        @pytest.mark.asyncio
        async def test_signal():
            with pytest.raises(pytest.fail.Exception, match="Timeout"):
                signal.raise_signal(signal.SIGALRM)
        """))
    result = pytester.runpytest_subprocess(timeout=10)
    result.assert_outcomes(passed=1)
