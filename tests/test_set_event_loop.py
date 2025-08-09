from __future__ import annotations

import sys
from textwrap import dedent

import pytest
from pytest import Pytester


@pytest.mark.parametrize(
    "test_loop_scope",
    ("function", "module", "package", "session"),
)
@pytest.mark.parametrize(
    "loop_breaking_action",
    [
        "asyncio.set_event_loop(None)",
        "asyncio.run(asyncio.sleep(0))",
        pytest.param(
            "with asyncio.Runner(): pass",
            marks=pytest.mark.skipif(
                sys.version_info < (3, 11),
                reason="asyncio.Runner requires Python 3.11+",
            ),
        ),
    ],
)
def test_set_event_loop_none(
    pytester: Pytester,
    test_loop_scope: str,
    loop_breaking_action: str,
):
    pytester.makeini(
        dedent(
            f"""\
            [pytest]
            asyncio_default_test_loop_scope = {test_loop_scope}
            asyncio_default_fixture_loop_scope = function
            """
        )
    )
    pytester.makepyfile(
        dedent(
            f"""\
            import asyncio
            import pytest

            pytest_plugins = "pytest_asyncio"

            @pytest.mark.asyncio
            async def test_before():
                pass

            def test_set_event_loop_none():
                {loop_breaking_action}

            @pytest.mark.asyncio
            async def test_after():
                pass
            """
        )
    )
    result = pytester.runpytest_subprocess()
    result.assert_outcomes(passed=3)


@pytest.mark.parametrize(
    "loop_breaking_action",
    [
        "asyncio.set_event_loop(None)",
        "asyncio.run(asyncio.sleep(0))",
        pytest.param(
            "with asyncio.Runner(): pass",
            marks=pytest.mark.skipif(
                sys.version_info < (3, 11),
                reason="asyncio.Runner requires Python 3.11+",
            ),
        ),
    ],
)
def test_set_event_loop_none_class(pytester: Pytester, loop_breaking_action: str):
    pytester.makeini(
        dedent(
            """\
            [pytest]
            asyncio_default_test_loop_scope = class
            asyncio_default_fixture_loop_scope = function
            """
        )
    )
    pytester.makepyfile(
        dedent(
            f"""\
            import asyncio
            import pytest

            pytest_plugins = "pytest_asyncio"


            class TestClass:
                @pytest.mark.asyncio
                async def test_before(self):
                    pass

                def test_set_event_loop_none(self):
                    {loop_breaking_action}

                @pytest.mark.asyncio
                async def test_after(self):
                    pass
            """
        )
    )
    result = pytester.runpytest_subprocess()
    result.assert_outcomes(passed=3)


@pytest.mark.parametrize("test_loop_scope", ("module", "package", "session"))
@pytest.mark.parametrize(
    "loop_breaking_action",
    [
        "asyncio.set_event_loop(None)",
        "asyncio.run(asyncio.sleep(0))",
        pytest.param(
            "with asyncio.Runner(): pass",
            marks=pytest.mark.skipif(
                sys.version_info < (3, 11),
                reason="asyncio.Runner requires Python 3.11+",
            ),
        ),
    ],
)
def test_original_shared_loop_is_reinstated_not_fresh_loop(
    pytester: Pytester,
    test_loop_scope: str,
    loop_breaking_action: str,
):
    pytester.makeini(
        dedent(
            f"""\
            [pytest]
            asyncio_default_test_loop_scope = {test_loop_scope}
            asyncio_default_fixture_loop_scope = function
            """
        )
    )
    pytester.makepyfile(
        dedent(
            f"""\
            import asyncio
            import pytest

            pytest_plugins = "pytest_asyncio"

            original_shared_loop: asyncio.AbstractEventLoop = None

            @pytest.mark.asyncio
            async def test_store_original_shared_loop():
                global original_shared_loop
                original_shared_loop = asyncio.get_running_loop()
                original_shared_loop._custom_marker = "original_loop_marker"

            def test_unset_event_loop():
                {loop_breaking_action}

            @pytest.mark.asyncio
            async def test_verify_original_loop_reinstated():
                global original_shared_loop
                current_loop = asyncio.get_running_loop()
                assert current_loop is original_shared_loop
                assert hasattr(current_loop, '_custom_marker')
                assert current_loop._custom_marker == "original_loop_marker"
            """
        )
    )
    result = pytester.runpytest_subprocess("--asyncio-mode=strict")
    result.assert_outcomes(passed=3)


@pytest.mark.parametrize("test_loop_scope", ("module", "package", "session"))
@pytest.mark.parametrize(
    "loop_breaking_action",
    [
        "asyncio.set_event_loop(None)",
        "asyncio.run(asyncio.sleep(0))",
        pytest.param(
            "with asyncio.Runner(): pass",
            marks=pytest.mark.skipif(
                sys.version_info < (3, 11),
                reason="asyncio.Runner requires Python 3.11+",
            ),
        ),
    ],
)
def test_shared_loop_with_fixture_preservation(
    pytester: Pytester,
    test_loop_scope: str,
    loop_breaking_action: str,
):
    pytester.makeini(
        dedent(
            f"""\
            [pytest]
            asyncio_default_test_loop_scope = {test_loop_scope}
            asyncio_default_fixture_loop_scope = {test_loop_scope}
            """
        )
    )
    pytester.makepyfile(
        dedent(
            f"""\
            import asyncio
            import pytest
            import pytest_asyncio

            pytest_plugins = "pytest_asyncio"

            fixture_loop: asyncio.AbstractEventLoop = None
            long_running_task = None

            @pytest_asyncio.fixture
            async def webserver():
                global fixture_loop, long_running_task
                fixture_loop = asyncio.get_running_loop()

                async def background_task():
                    while True:
                        await asyncio.sleep(1)

                long_running_task = asyncio.create_task(background_task())
                yield
                long_running_task.cancel()


            @pytest.mark.asyncio
            async def test_before(webserver):
                global fixture_loop, long_running_task
                assert asyncio.get_running_loop() is fixture_loop
                assert not long_running_task.done()


            def test_set_event_loop_none():
                {loop_breaking_action}


            @pytest.mark.asyncio
            async def test_after(webserver):
                global fixture_loop, long_running_task
                current_loop = asyncio.get_running_loop()
                assert current_loop is fixture_loop
                assert not long_running_task.done()
            """
        )
    )
    result = pytester.runpytest_subprocess("--asyncio-mode=strict")
    result.assert_outcomes(passed=3)


@pytest.mark.parametrize(
    "first_scope,second_scope",
    [
        ("module", "session"),
        ("session", "module"),
        ("package", "session"),
        ("session", "package"),
        ("package", "module"),
        ("module", "package"),
    ],
)
@pytest.mark.parametrize(
    "loop_breaking_action",
    [
        "asyncio.set_event_loop(None)",
        "asyncio.run(asyncio.sleep(0))",
        pytest.param(
            "with asyncio.Runner(): pass",
            marks=pytest.mark.skipif(
                sys.version_info < (3, 11),
                reason="asyncio.Runner requires Python 3.11+",
            ),
        ),
    ],
)
def test_shared_loop_with_multiple_fixtures_preservation(
    pytester: Pytester,
    first_scope: str,
    second_scope: str,
    loop_breaking_action: str,
):
    pytester.makeini(
        dedent(
            """\
            [pytest]
            asyncio_default_test_loop_scope = session
            asyncio_default_fixture_loop_scope = session
            """
        )
    )
    pytester.makepyfile(
        dedent(
            f"""\
            import asyncio
            import pytest
            import pytest_asyncio

            pytest_plugins = "pytest_asyncio"

            first_fixture_loop: asyncio.AbstractEventLoop = None
            second_fixture_loop: asyncio.AbstractEventLoop = None
            first_long_running_task = None
            second_long_running_task = None

            @pytest_asyncio.fixture(scope="{first_scope}", loop_scope="{first_scope}")
            async def first_webserver():
                global first_fixture_loop, first_long_running_task
                first_fixture_loop = asyncio.get_running_loop()

                async def background_task():
                    while True:
                        await asyncio.sleep(0.1)

                first_long_running_task = asyncio.create_task(background_task())
                yield
                first_long_running_task.cancel()

            @pytest_asyncio.fixture(scope="{second_scope}", loop_scope="{second_scope}")
            async def second_webserver():
                global second_fixture_loop, second_long_running_task
                second_fixture_loop = asyncio.get_running_loop()

                async def background_task():
                    while True:
                        await asyncio.sleep(0.1)

                second_long_running_task = asyncio.create_task(background_task())
                yield
                second_long_running_task.cancel()

            @pytest.mark.asyncio(loop_scope="{first_scope}")
            async def test_before_first(first_webserver):
                global first_fixture_loop, first_long_running_task
                assert asyncio.get_running_loop() is first_fixture_loop
                assert not first_long_running_task.done()

            @pytest.mark.asyncio(loop_scope="{second_scope}")
            async def test_before_second(second_webserver):
                global second_fixture_loop, second_long_running_task
                assert asyncio.get_running_loop() is second_fixture_loop
                assert not second_long_running_task.done()

            def test_set_event_loop_none():
                {loop_breaking_action}

            @pytest.mark.asyncio(loop_scope="{first_scope}")
            async def test_after_first(first_webserver):
                global first_fixture_loop, first_long_running_task
                current_loop = asyncio.get_running_loop()
                assert current_loop is first_fixture_loop
                assert not first_long_running_task.done()

            @pytest.mark.asyncio(loop_scope="{second_scope}")
            async def test_after_second(second_webserver):
                global second_fixture_loop, second_long_running_task
                current_loop = asyncio.get_running_loop()
                assert current_loop is second_fixture_loop
                assert not second_long_running_task.done()
            """
        )
    )
    result = pytester.runpytest_subprocess("--asyncio-mode=strict")
    result.assert_outcomes(passed=5)
