from __future__ import annotations

from textwrap import dedent

import pytest
from pytest import Pytester


def test_hook_factories_apply_to_async_tests(pytester: Pytester) -> None:
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makeconftest(dedent("""\
        import asyncio

        class CustomEventLoop(asyncio.SelectorEventLoop):
            pass

        def pytest_asyncio_loop_factories(config, item):
            return [CustomEventLoop]
        """))
    pytester.makepyfile(dedent("""\
        import asyncio
        import pytest

        pytest_plugins = "pytest_asyncio"

        @pytest.mark.asyncio
        async def test_uses_custom_loop():
            assert type(asyncio.get_running_loop()).__name__ == "CustomEventLoop"
        """))
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=1)


def test_hook_factories_parametrize_async_tests(pytester: Pytester) -> None:
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makeconftest(dedent("""\
        import asyncio

        class CustomEventLoopA(asyncio.SelectorEventLoop):
            pass

        class CustomEventLoopB(asyncio.SelectorEventLoop):
            pass

        def pytest_asyncio_loop_factories(config, item):
            return [CustomEventLoopA, CustomEventLoopB]
        """))
    pytester.makepyfile(dedent("""\
        import asyncio
        import pytest

        pytest_plugins = "pytest_asyncio"

        @pytest.mark.asyncio
        async def test_runs_once_per_factory():
            loop_name = type(asyncio.get_running_loop()).__name__
            assert loop_name in ("CustomEventLoopA", "CustomEventLoopB")
        """))
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=2)


def test_hook_factories_apply_to_async_fixtures(pytester: Pytester) -> None:
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makeconftest(dedent("""\
        import asyncio

        class CustomEventLoop(asyncio.SelectorEventLoop):
            pass

        def pytest_asyncio_loop_factories(config, item):
            return [CustomEventLoop]
        """))
    pytester.makepyfile(dedent("""\
        import asyncio
        import pytest
        import pytest_asyncio

        pytest_plugins = "pytest_asyncio"

        @pytest_asyncio.fixture
        async def loop_fixture():
            return asyncio.get_running_loop()

        @pytest.mark.asyncio
        async def test_fixture_uses_custom_loop(loop_fixture):
            assert type(loop_fixture).__name__ == "CustomEventLoop"
            assert type(asyncio.get_running_loop()).__name__ == "CustomEventLoop"
        """))
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=1)


def test_sync_tests_are_not_parametrized(pytester: Pytester) -> None:
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makeconftest(dedent("""\
        import asyncio

        class CustomEventLoopA(asyncio.SelectorEventLoop):
            pass

        class CustomEventLoopB(asyncio.SelectorEventLoop):
            pass

        def pytest_asyncio_loop_factories(config, item):
            return [CustomEventLoopA, CustomEventLoopB]
        """))
    pytester.makepyfile(dedent("""\
        import asyncio
        import pytest

        pytest_plugins = "pytest_asyncio"

        def test_sync(request):
            assert "_asyncio_loop_factory" not in request.fixturenames

        @pytest.mark.asyncio
        async def test_async(request):
            assert "_asyncio_loop_factory" in request.fixturenames
            loop_name = type(asyncio.get_running_loop()).__name__
            assert loop_name in ("CustomEventLoopA", "CustomEventLoopB")
        """))
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=3)


@pytest.mark.parametrize(
    "hook_body",
    (
        "return []",
        "return (factory for factory in [CustomEventLoop])",
        "return [CustomEventLoop, 1]",
        "return None",
    ),
)
def test_hook_requires_non_empty_sequence_of_callables(
    pytester: Pytester,
    hook_body: str,
) -> None:
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makeconftest(dedent(f"""\
        import asyncio

        class CustomEventLoop(asyncio.SelectorEventLoop):
            pass

        def pytest_asyncio_loop_factories(config, item):
            {hook_body}
        """))
    pytester.makepyfile(dedent("""\
        import pytest

        pytest_plugins = "pytest_asyncio"

        @pytest.mark.asyncio
        async def test_async():
            assert True
        """))
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(errors=1)
    result.stdout.fnmatch_lines(
        ["*pytest_asyncio_loop_factories must return a non-empty sequence*"]
    )


def test_nested_conftest_multiple_hook_implementations_are_allowed(
    pytester: Pytester,
) -> None:
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makeconftest(dedent("""\
        import asyncio

        class RootCustomEventLoop(asyncio.SelectorEventLoop):
            pass

        def pytest_asyncio_loop_factories(config, item):
            return [RootCustomEventLoop]
        """))
    subdir = pytester.mkdir("subtests")
    subdir.joinpath("conftest.py").write_text(
        dedent("""\
        import asyncio

        class SubCustomEventLoop(asyncio.SelectorEventLoop):
            pass

        def pytest_asyncio_loop_factories(config, item):
            return [SubCustomEventLoop]
        """),
    )
    pytester.makepyfile(
        test_root=dedent("""\
            import asyncio
            import pytest

            pytest_plugins = "pytest_asyncio"

            @pytest.mark.asyncio
            async def test_uses_root_loop():
                loop_name = type(asyncio.get_running_loop()).__name__
                assert loop_name in ("RootCustomEventLoop", "SubCustomEventLoop")
            """),
    )
    subdir.joinpath("test_sub.py").write_text(
        dedent("""\
        import asyncio
        import pytest

        pytest_plugins = "pytest_asyncio"

        @pytest.mark.asyncio
        async def test_uses_sub_loop():
            loop_name = type(asyncio.get_running_loop()).__name__
            assert loop_name in ("RootCustomEventLoop", "SubCustomEventLoop")
        """),
    )
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=2)


def test_hook_accepts_tuple_return(pytester: Pytester) -> None:
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makeconftest(dedent("""\
        import asyncio

        class CustomEventLoop(asyncio.SelectorEventLoop):
            pass

        def pytest_asyncio_loop_factories(config, item):
            return (CustomEventLoop,)
        """))
    pytester.makepyfile(dedent("""\
        import asyncio
        import pytest

        pytest_plugins = "pytest_asyncio"

        @pytest.mark.asyncio
        async def test_uses_custom_loop():
            assert type(asyncio.get_running_loop()).__name__ == "CustomEventLoop"
        """))
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=1)


@pytest.mark.parametrize("default_test_loop_scope", ("function", "module"))
def test_hook_factories_can_vary_per_test_with_default_loop_scope(
    pytester: Pytester,
    default_test_loop_scope: str,
) -> None:
    pytester.makeini(
        "[pytest]\nasyncio_default_fixture_loop_scope = function\n"
        f"asyncio_default_test_loop_scope = {default_test_loop_scope}"
    )
    pytester.makeconftest(dedent("""\
        import asyncio

        class CustomEventLoopA(asyncio.SelectorEventLoop):
            pass

        class CustomEventLoopB(asyncio.SelectorEventLoop):
            pass

        def pytest_asyncio_loop_factories(config, item):
            if item.name.endswith("a"):
                return [CustomEventLoopA]
            else:
                return [CustomEventLoopB]
        """))
    pytester.makepyfile(dedent("""\
        import asyncio
        import pytest

        pytest_plugins = "pytest_asyncio"

        @pytest.mark.asyncio
        async def test_a():
            assert type(asyncio.get_running_loop()).__name__ == "CustomEventLoopA"

        @pytest.mark.asyncio
        async def test_b():
            assert type(asyncio.get_running_loop()).__name__ == "CustomEventLoopB"
        """))
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=2)


def test_hook_factories_can_vary_per_test_with_session_scope_across_modules(
    pytester: Pytester,
) -> None:
    pytester.makeini(
        "[pytest]\nasyncio_default_fixture_loop_scope = function\n"
        "asyncio_default_test_loop_scope = session"
    )
    pytester.makeconftest(dedent("""\
        import asyncio

        class CustomEventLoopA(asyncio.SelectorEventLoop):
            pass

        class CustomEventLoopB(asyncio.SelectorEventLoop):
            pass

        def pytest_asyncio_loop_factories(config, item):
            if "test_a.py::" in item.nodeid:
                return [CustomEventLoopA]
            return [CustomEventLoopB]
        """))
    pytester.makepyfile(
        test_a=dedent("""\
            import asyncio
            import pytest

            pytest_plugins = "pytest_asyncio"

            @pytest.mark.asyncio
            async def test_a():
                assert type(asyncio.get_running_loop()).__name__ == "CustomEventLoopA"
            """),
        test_b=dedent("""\
            import asyncio
            import pytest

            pytest_plugins = "pytest_asyncio"

            @pytest.mark.asyncio
            async def test_b():
                assert type(asyncio.get_running_loop()).__name__ == "CustomEventLoopB"
            """),
    )
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=2)


def test_hook_factories_work_in_auto_mode(pytester: Pytester) -> None:
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makeconftest(dedent("""\
        import asyncio

        class CustomEventLoop(asyncio.SelectorEventLoop):
            pass

        def pytest_asyncio_loop_factories(config, item):
            return [CustomEventLoop]
        """))
    pytester.makepyfile(dedent("""\
        import asyncio

        pytest_plugins = "pytest_asyncio"

        async def test_uses_custom_loop():
            assert type(asyncio.get_running_loop()).__name__ == "CustomEventLoop"
        """))
    result = pytester.runpytest("--asyncio-mode=auto")
    result.assert_outcomes(passed=1)


def test_function_loop_scope_allows_per_test_factories_with_session_default(
    pytester: Pytester,
) -> None:
    pytester.makeini(
        "[pytest]\nasyncio_default_fixture_loop_scope = function\n"
        "asyncio_default_test_loop_scope = session"
    )
    pytester.makeconftest(dedent("""\
        import asyncio

        class CustomEventLoopA(asyncio.SelectorEventLoop):
            pass

        class CustomEventLoopB(asyncio.SelectorEventLoop):
            pass

        def pytest_asyncio_loop_factories(config, item):
            if item.name.endswith("a"):
                return [CustomEventLoopA]
            else:
                return [CustomEventLoopB]
        """))
    pytester.makepyfile(dedent("""\
        import asyncio
        import pytest

        pytest_plugins = "pytest_asyncio"

        @pytest.mark.asyncio(loop_scope="function")
        async def test_a():
            assert type(asyncio.get_running_loop()).__name__ == "CustomEventLoopA"

        @pytest.mark.asyncio(loop_scope="function")
        async def test_b():
            assert type(asyncio.get_running_loop()).__name__ == "CustomEventLoopB"
        """))
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=2)
