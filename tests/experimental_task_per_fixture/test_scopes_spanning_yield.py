"""
Task groups, cancel scopes and timeouts that span a fixture's yield.

With asyncio_experimental_task_per_fixture, a fixture exits such a scope
in the task that entered it (issues #1083 and #1191). If the scope
cancels the fixture while pytest holds it, the running test is
cancelled, and the scope's error is reported at the fixture's teardown.
"""

from __future__ import annotations

import sys
from textwrap import dedent

import pytest
from pytest import Pytester

pytestmark = pytest.mark.skipif(
    sys.version_info < (3, 11),
    reason="asyncio_experimental_task_per_fixture requires Python 3.11",
)

_EAGER_TASK_LOOP = """\
import asyncio

def eager_task_loop():
    loop = asyncio.new_event_loop()
    loop.set_task_factory(asyncio.eager_task_factory)
    return loop

def pytest_asyncio_loop_factories(config, item):
    return {"eager_task_loop": eager_task_loop}
"""


@pytest.mark.parametrize(
    "conftest",
    [
        pytest.param("", id="default loop"),
        pytest.param(
            _EAGER_TASK_LOOP,
            id="eager tasks",
            marks=pytest.mark.skipif(
                sys.version_info < (3, 12),
                reason="asyncio.eager_task_factory requires Python 3.12",
            ),
        ),
    ],
)
def test_a_task_group_child_failing_during_the_test_cancels_the_test(
    pytester: Pytester, conftest: str
):
    """Issue #1083: the child's error is reported at teardown."""
    pytester.makeini(
        "[pytest]\n"
        "asyncio_experimental_task_per_fixture = true\n"
        "asyncio_default_fixture_loop_scope = function\n"
        "asyncio_debug = true"
    )
    pytester.makeconftest(conftest)
    pytester.makepyfile(dedent("""\
        import asyncio

        import pytest
        import pytest_asyncio

        @pytest_asyncio.fixture
        async def service():
            failure = asyncio.Event()

            async def fail():
                await failure.wait()
                raise RuntimeError("background service failed")

            async with asyncio.TaskGroup() as group:
                group.create_task(fail())
                yield failure

        @pytest.mark.asyncio
        async def test_uses_service(service):
            service.set()
            await asyncio.Event().wait()
        """))

    result = pytester.runpytest_subprocess(
        "--asyncio-mode=strict", "-W", "error", timeout=30
    )

    result.assert_outcomes(failed=1, errors=1)
    result.stdout.fnmatch_lines(
        [
            "*ERROR at teardown of test_uses_service*",
            "*RuntimeError: background service failed*",
            "*_ test_uses_service _*",
            "*CancelledError*",
            "*Async fixture 'service' was cancelled*",
        ]
    )
    output = result.stdout.str() + result.stderr.str()
    for noise in ("Task was destroyed", "never retrieved", "never awaited"):
        assert noise not in output


def test_a_task_group_child_failing_during_a_dependent_setup_cancels_that_setup(
    pytester: Pytester,
):
    pytester.makeini(
        "[pytest]\n"
        "asyncio_experimental_task_per_fixture = true\n"
        "asyncio_default_fixture_loop_scope = function"
    )
    pytester.makepyfile(dedent("""\
        import asyncio

        import pytest
        import pytest_asyncio

        @pytest_asyncio.fixture
        async def service():
            failure = asyncio.Event()

            async def fail():
                await failure.wait()
                raise RuntimeError("background service failed")

            async with asyncio.TaskGroup() as group:
                group.create_task(fail())
                yield failure

        @pytest_asyncio.fixture
        async def dependent(service):
            service.set()
            await asyncio.Event().wait()
            yield

        @pytest.mark.asyncio
        async def test_uses_dependent(dependent):
            pass
        """))

    result = pytester.runpytest_subprocess("--asyncio-mode=strict", timeout=30)

    result.assert_outcomes(errors=2)
    result.stdout.fnmatch_lines(
        [
            "*ERROR at setup of test_uses_dependent*",
            "*PytestAsyncioError: *'dependent' was cancelled*",
            "*ERROR at teardown of test_uses_dependent*",
            "*RuntimeError: background service failed*",
        ]
    )


def test_an_anyio_task_group_spanning_the_yield_is_exited_in_its_own_task(
    pytester: Pytester,
):
    """Issue #1191: teardown exits the group's cancel scope."""
    pytester.makeini(
        "[pytest]\n"
        "asyncio_experimental_task_per_fixture = true\n"
        "asyncio_default_fixture_loop_scope = function"
    )
    pytester.makepyfile(dedent("""\
        import asyncio

        import anyio
        import pytest
        import pytest_asyncio

        @pytest_asyncio.fixture
        async def service():
            async with anyio.create_task_group() as group:
                group.start_soon(asyncio.Event().wait)
                yield
                group.cancel_scope.cancel()

        @pytest.mark.asyncio
        async def test_uses_service(service):
            await asyncio.sleep(0)
        """))

    result = pytester.runpytest_subprocess("--asyncio-mode=strict", timeout=30)

    result.assert_outcomes(passed=1)


_ASYNCIO_TASK_GROUP_PARENT = """\
import asyncio

import pytest_asyncio

@pytest_asyncio.fixture
async def parent():
    failure = asyncio.Event()

    async def fail():
        await failure.wait()
        raise RuntimeError("background task failed")

    try:
        async with asyncio.TaskGroup() as group:
            group.create_task(fail())
            yield failure
            print("parent continued after the yield")
    finally:
        print("parent torn down")
"""

_ANYIO_TASK_GROUP_PARENT = """\
import anyio
import pytest_asyncio

@pytest_asyncio.fixture
async def parent():
    failure = anyio.Event()

    async def fail():
        await failure.wait()
        raise RuntimeError("background task failed")

    try:
        async with anyio.create_task_group() as group:
            group.start_soon(fail)
            yield failure
            print("parent continued after the yield")
    finally:
        print("parent torn down")
"""


@pytest.mark.parametrize(
    "conftest",
    [
        pytest.param(_ASYNCIO_TASK_GROUP_PARENT, id="asyncio task group"),
        pytest.param(_ANYIO_TASK_GROUP_PARENT, id="anyio task group"),
    ],
)
def test_a_cancelled_fixture_stays_set_up_until_its_dependents_are_torn_down(
    pytester: Pytester, conftest: str
):
    pytester.makeini(
        "[pytest]\n"
        "asyncio_experimental_task_per_fixture = true\n"
        "asyncio_default_fixture_loop_scope = function"
    )
    pytester.makeconftest(conftest)
    pytester.makepyfile(dedent("""\
        import asyncio

        import pytest
        import pytest_asyncio

        @pytest_asyncio.fixture
        async def dependent(parent):
            yield
            await asyncio.sleep(0)
            print("dependent torn down")

        @pytest.mark.asyncio
        async def test_uses_dependent(parent, dependent):
            parent.set()
            try:
                await asyncio.Event().wait()
            finally:
                await asyncio.sleep(0)
                print("test cleaned up")
        """))

    result = pytester.runpytest_subprocess("--asyncio-mode=strict", "-s", timeout=30)

    result.assert_outcomes(failed=1, errors=1)
    result.stdout.fnmatch_lines(
        ["*test cleaned up", "*dependent torn down", "*parent torn down"]
    )
    result.stdout.no_fnmatch_line("*parent continued after the yield")
    result.stdout.fnmatch_lines(
        [
            "*ERROR at teardown of test_uses_dependent*",
            "*RuntimeError: background task failed*",
        ]
    )


_ASYNCIO_TIMEOUT = """\
import asyncio

import pytest_asyncio

@pytest_asyncio.fixture
async def expire():
    async with asyncio.timeout(None) as timeout:
        yield lambda: timeout.reschedule(asyncio.get_running_loop().time())
"""

_ANYIO_TIMEOUT = """\
import anyio
import pytest_asyncio

@pytest_asyncio.fixture
async def expire():
    with anyio.fail_after(None) as scope:

        def expire_now():
            scope.deadline = anyio.current_time()

        yield expire_now
"""


@pytest.mark.parametrize(
    "conftest",
    [
        pytest.param(_ASYNCIO_TIMEOUT, id="asyncio.timeout"),
        pytest.param(_ANYIO_TIMEOUT, id="anyio.fail_after"),
    ],
)
def test_a_timeout_spanning_the_yield_expiring_during_the_test_cancels_it(
    pytester: Pytester, conftest: str
):
    pytester.makeini(
        "[pytest]\n"
        "asyncio_experimental_task_per_fixture = true\n"
        "asyncio_default_fixture_loop_scope = function"
    )
    pytester.makeconftest(conftest)
    pytester.makepyfile(dedent("""\
        import asyncio

        import pytest

        @pytest.mark.asyncio
        async def test_times_out(expire):
            expire()
            await asyncio.Event().wait()
        """))

    result = pytester.runpytest_subprocess("--asyncio-mode=strict", timeout=30)

    result.assert_outcomes(failed=1, errors=1)
    result.stdout.fnmatch_lines(
        [
            "*ERROR at teardown of test_times_out*",
            "*TimeoutError*",
            "*_ test_times_out _*",
            "*CancelledError*",
        ]
    )


def test_a_fixture_timeout_is_reported_when_the_test_catches_its_cancellation(
    pytester: Pytester,
):
    pytester.makeini(
        "[pytest]\n"
        "asyncio_experimental_task_per_fixture = true\n"
        "asyncio_default_fixture_loop_scope = function"
    )
    pytester.makepyfile(dedent("""\
        import asyncio

        import pytest
        import pytest_asyncio

        @pytest_asyncio.fixture
        async def deadline():
            async with asyncio.timeout(None) as timeout:
                yield timeout

        @pytest.mark.asyncio
        async def test_catches_cancellation(deadline):
            deadline.reschedule(asyncio.get_running_loop().time())
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                pass
        """))

    result = pytester.runpytest_subprocess("--asyncio-mode=strict", timeout=30)

    result.assert_outcomes(passed=1, errors=1)
    result.stdout.fnmatch_lines(
        ["*ERROR at teardown of test_catches_cancellation*", "*TimeoutError*"]
    )


def test_a_timeout_inside_a_failed_task_group_leaves_the_cancellation_to_the_group(
    pytester: Pytester,
):
    """
    A timeout and its enclosing task group both cancel the held fixture.

    The timeout sees both requests, as it would if both reached a task
    before the task resumed. It therefore raises CancelledError for the
    group, not TimeoutError.
    """
    pytester.makeini(
        "[pytest]\n"
        "asyncio_experimental_task_per_fixture = true\n"
        "asyncio_default_fixture_loop_scope = function"
    )
    pytester.makepyfile(dedent("""\
        import asyncio
        from pathlib import Path

        import pytest
        import pytest_asyncio

        @pytest_asyncio.fixture
        async def service():
            failure = asyncio.Event()

            async def fail():
                await failure.wait()
                raise RuntimeError("service failed")

            async with asyncio.TaskGroup() as group:
                group.create_task(fail())
                try:
                    async with asyncio.timeout(None) as deadline:
                        yield deadline, failure
                except TimeoutError:
                    await asyncio.sleep(0)
                    Path("continued.txt").write_text("group cancellation lost")

        @pytest.mark.asyncio
        async def test_service(service):
            deadline, failure = service
            deadline.reschedule(asyncio.get_running_loop().time())
            failure.set()
            await asyncio.Event().wait()
        """))

    result = pytester.runpytest_subprocess("--asyncio-mode=strict", timeout=30)

    result.assert_outcomes(failed=1, errors=1)
    result.stdout.fnmatch_lines(
        ["*ERROR at teardown of test_service*", "*RuntimeError: service failed*"]
    )
    assert not (pytester.path / "continued.txt").exists()


def test_the_test_cleanup_finishes_while_anyio_keeps_cancelling_its_fixture(
    pytester: Pytester,
):
    """AnyIO cancels the held fixture repeatedly, the test only once."""
    pytester.makeini(
        "[pytest]\n"
        "asyncio_experimental_task_per_fixture = true\n"
        "asyncio_default_fixture_loop_scope = function"
    )
    pytester.makepyfile(dedent("""\
        import asyncio
        from pathlib import Path

        import anyio
        import pytest
        import pytest_asyncio

        @pytest_asyncio.fixture
        async def scope():
            with anyio.CancelScope() as scope:
                yield scope

        @pytest.mark.asyncio
        async def test_cancels_scope(scope):
            scope.cancel()
            try:
                await asyncio.Event().wait()
            finally:
                for _ in range(5):
                    await asyncio.sleep(0)
                Path("cleanup.txt").write_text("finished")
        """))

    result = pytester.runpytest_subprocess("--asyncio-mode=strict", timeout=30)

    result.assert_outcomes(failed=1)
    assert (pytester.path / "cleanup.txt").read_text() == "finished"


def test_a_fixture_that_has_yielded_is_not_cancelled_by_its_parent_failing(
    pytester: Pytester,
):
    pytester.makeini(
        "[pytest]\n"
        "asyncio_experimental_task_per_fixture = true\n"
        "asyncio_default_fixture_loop_scope = function"
    )
    pytester.makepyfile(dedent("""\
        import asyncio

        import pytest
        import pytest_asyncio

        @pytest_asyncio.fixture
        async def service():
            failure = asyncio.Event()

            async def fail():
                await failure.wait()
                raise RuntimeError("service failed")

            with open("report.txt", "w") as report:
                async with asyncio.TaskGroup() as group:
                    group.create_task(fail())
                    yield failure, report

        @pytest_asyncio.fixture
        async def dependent(service):
            failure, report = service
            failure.set()
            yield
            await asyncio.sleep(0)
            report.write("dependent teardown finished")

        @pytest.mark.asyncio
        async def test_uses_dependent(dependent):
            pass
        """))

    result = pytester.runpytest_subprocess("--asyncio-mode=strict", timeout=30)

    result.assert_outcomes(failed=1, errors=1)
    result.stdout.fnmatch_lines(["*RuntimeError: service failed*"])
    assert (pytester.path / "report.txt").read_text() == "dependent teardown finished"


def test_a_fixture_that_yields_twice_exits_its_cancel_scope_in_its_own_task(
    pytester: Pytester,
):
    pytester.makeini(
        "[pytest]\n"
        "asyncio_experimental_task_per_fixture = true\n"
        "asyncio_default_fixture_loop_scope = function"
    )
    pytester.makepyfile(dedent("""\
        import anyio
        import pytest
        import pytest_asyncio

        @pytest_asyncio.fixture
        async def generator():
            with anyio.CancelScope():
                yield
                yield

        @pytest.mark.asyncio
        async def test_uses_generator(generator):
            pass
        """))

    result = pytester.runpytest_subprocess("--asyncio-mode=strict", timeout=30)

    result.assert_outcomes(passed=1, errors=1)
    result.stdout.fnmatch_lines(
        ["*ValueError: Async generator fixture 'generator' didn't stop*"]
    )
    result.stdout.no_fnmatch_line("*cancel scope in a different task*")
