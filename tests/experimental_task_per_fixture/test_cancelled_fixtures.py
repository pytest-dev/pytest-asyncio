"""
Async fixtures cancelled in setup, while held, or in teardown.

With asyncio_experimental_task_per_fixture, a fixture cancelled while
pytest holds it makes its event loop refuse new async tests and fixture
setups until pytest has torn it down.
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

_COROUTINE_CANCELLED_IN_SETUP = """\
import asyncio

import pytest_asyncio

@pytest_asyncio.fixture(loop_scope="module")
async def resource():
    asyncio.current_task().cancel("setup cancelled")
    await asyncio.sleep(0)
"""

_GENERATOR_CANCELLED_IN_SETUP = """\
import asyncio

import pytest_asyncio

@pytest_asyncio.fixture(loop_scope="module")
async def resource():
    asyncio.current_task().cancel("setup cancelled")
    await asyncio.sleep(0)
    yield
"""


@pytest.mark.parametrize(
    "conftest",
    [
        pytest.param(_COROUTINE_CANCELLED_IN_SETUP, id="coroutine"),
        pytest.param(_GENERATOR_CANCELLED_IN_SETUP, id="generator"),
    ],
)
def test_a_fixture_cancelled_during_setup_is_a_setup_error_of_its_test_only(
    pytester: Pytester, conftest: str
):
    pytester.makeini(
        "[pytest]\n"
        "asyncio_experimental_task_per_fixture = true\n"
        "asyncio_default_fixture_loop_scope = function"
    )
    pytester.makeconftest(conftest)
    pytester.makepyfile(dedent("""\
        import pytest

        @pytest.mark.asyncio(loop_scope="module")
        async def test_uses_resource(resource):
            pass

        @pytest.mark.asyncio(loop_scope="module")
        async def test_next():
            pass
        """))

    result = pytester.runpytest_subprocess("--asyncio-mode=strict", timeout=30)

    result.assert_outcomes(errors=1, passed=1)
    result.stdout.fnmatch_lines(
        [
            "*ERROR at setup of test_uses_resource*",
            "*CancelledError: setup cancelled",
            "*PytestAsyncioError: *'resource' was cancelled*",
        ]
    )


def test_a_module_fixture_cancelled_during_setup_is_a_setup_error_of_each_test(
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

        @pytest_asyncio.fixture(scope="module", loop_scope="module")
        async def resource():
            asyncio.current_task().cancel()
            await asyncio.sleep(0)
            yield

        @pytest.mark.asyncio(loop_scope="module")
        async def test_first(resource):
            pass

        @pytest.mark.asyncio(loop_scope="module")
        async def test_second(resource):
            pass
        """))

    result = pytester.runpytest_subprocess("--asyncio-mode=strict", timeout=30)

    result.assert_outcomes(errors=2)
    result.stdout.fnmatch_lines(
        [
            "*ERROR at setup of test_first*",
            "*PytestAsyncioError: *'resource' was cancelled*",
            "*ERROR at setup of test_second*",
            "*PytestAsyncioError: *'resource' was cancelled*",
        ]
    )


def test_new_async_work_on_the_loop_of_a_cancelled_held_fixture_is_refused(
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

        @pytest_asyncio.fixture(scope="module", loop_scope="module")
        async def service():
            yield asyncio.current_task()

        @pytest_asyncio.fixture(loop_scope="module")
        async def new_fixture():
            pytest.fail("the loop should have refused this setup")

        @pytest.mark.asyncio(loop_scope="module")
        async def test_cancels_the_service(service):
            service.cancel()
            await asyncio.Event().wait()

        @pytest.mark.asyncio(loop_scope="module")
        async def test_refused():
            pytest.fail("the loop should have refused this test")

        @pytest.mark.asyncio(loop_scope="module")
        async def test_refused_setup(new_fixture):
            pass
        """))

    result = pytester.runpytest_subprocess("--asyncio-mode=strict", timeout=30)

    result.assert_outcomes(failed=2, errors=2)
    result.stdout.fnmatch_lines(
        [
            "*ERROR at setup of test_refused_setup*",
            "*RuntimeError: *'service' was cancelled while waiting for teardown*",
            "*_ test_refused _*",
            "*RuntimeError: *'service' was cancelled while waiting for teardown*",
        ]
    )


def test_tests_on_other_loops_run_while_a_cancelled_fixture_is_held(
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

        @pytest_asyncio.fixture(scope="module", loop_scope="module")
        async def service():
            yield asyncio.current_task()

        @pytest.mark.asyncio(loop_scope="module")
        async def test_cancels_the_service(service):
            service.cancel()
            await asyncio.Event().wait()

        @pytest.mark.asyncio(loop_scope="function")
        async def test_on_its_own_loop():
            pass
        """))

    result = pytester.runpytest_subprocess("--asyncio-mode=strict", "-v", timeout=30)

    result.assert_outcomes(failed=1, passed=1, errors=1)
    result.stdout.fnmatch_lines(["*::test_on_its_own_loop PASSED*"])


def test_a_loop_accepts_new_tests_once_its_cancelled_fixture_is_torn_down(
    pytester: Pytester,
):
    pytester.makeini(
        "[pytest]\n"
        "asyncio_experimental_task_per_fixture = true\n"
        "asyncio_default_fixture_loop_scope = session\n"
        "asyncio_default_test_loop_scope = session"
    )
    pytester.makepyfile(dedent("""\
        import asyncio

        import pytest
        import pytest_asyncio

        @pytest_asyncio.fixture
        async def service():
            yield asyncio.current_task()

        @pytest.mark.asyncio
        async def test_cancels_the_service(service):
            service.cancel()
            await asyncio.Event().wait()

        @pytest.mark.asyncio
        async def test_after_teardown():
            pass
        """))

    result = pytester.runpytest_subprocess("--asyncio-mode=strict", "-v", timeout=30)

    result.assert_outcomes(failed=1, passed=1, errors=1)
    result.stdout.fnmatch_lines(["*::test_after_teardown PASSED*"])


def test_a_cancelled_dependent_teardown_does_not_prevent_its_parent_teardown(
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
        async def parent():
            yield
            raise RuntimeError("parent cleanup failed")

        @pytest_asyncio.fixture
        async def dependent(parent):
            yield
            asyncio.current_task().cancel()
            await asyncio.sleep(0)

        @pytest.mark.asyncio
        async def test_uses_dependent(dependent):
            pass
        """))

    result = pytester.runpytest_subprocess("--asyncio-mode=strict", timeout=30)

    result.assert_outcomes(passed=1, errors=1)
    result.stdout.fnmatch_lines(["*PytestAsyncioError: *'dependent' was cancelled*"])
    result.stdout.fnmatch_lines(["*RuntimeError: parent cleanup failed*"])


def test_a_fixture_cancelled_twice_while_held_receives_the_first_cancellation(
    pytester: Pytester,
):
    """asyncio.TaskGroup also keeps the first cancellation."""
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
        async def parent():
            yield asyncio.current_task()

        @pytest_asyncio.fixture
        async def dependent(parent):
            yield
            parent.cancel("first")
            await asyncio.sleep(0)
            parent.cancel("second")
            await asyncio.sleep(0)

        @pytest.mark.asyncio
        async def test_uses_dependent(dependent):
            pass
        """))

    result = pytester.runpytest_subprocess("--asyncio-mode=strict", timeout=30)

    result.assert_outcomes(passed=1, errors=1)
    result.stdout.fnmatch_lines(["*CancelledError: first"])
