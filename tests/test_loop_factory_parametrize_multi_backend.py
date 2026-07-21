"""Multi-backend parametrize + loop factories (#1463 / #1509 residual)."""

from __future__ import annotations

from textwrap import dedent

from pytest import Pytester


def test_asyncio_and_analogous_backend_parametrize_uses_loop_factories(
    pytester: Pytester,
) -> None:
    """
    Regression for #1463 issue shape: asyncio mark on one parameter set and
    an analogous non-asyncio backend mark on another, with loop-type asserts
    in the test body.

    CI does not depend on pytest-trio (removed from test deps historically), so
    the second backend is a tiny inline plugin analogous to a trio-style mark.
    """
    pytester.makeini(
        "[pytest]\n"
        "asyncio_default_fixture_loop_scope = function\n"
        "markers =\n"
        "    other_async: analogous non-asyncio backend for multi-backend params\n"
    )
    pytester.makeconftest(
        dedent(
            """\
        import asyncio
        import inspect

        import pytest


        class CustomEventLoop(asyncio.SelectorEventLoop):
            pass


        class OtherBackendLoop(asyncio.SelectorEventLoop):
            pass


        def pytest_asyncio_loop_factories(config, item):
            return {"custom": CustomEventLoop}


        @pytest.hookimpl(tryfirst=True)
        def pytest_pyfunc_call(pyfuncitem):
            if pyfuncitem.get_closest_marker("other_async") is None:
                return None
            testfunction = pyfuncitem.obj
            if not inspect.iscoroutinefunction(testfunction):
                return None
            funcargs = {
                arg: pyfuncitem.funcargs[arg]
                for arg in pyfuncitem._fixtureinfo.argnames
            }
            loop = OtherBackendLoop()
            try:
                loop.run_until_complete(testfunction(**funcargs))
            finally:
                try:
                    loop.run_until_complete(loop.shutdown_asyncgens())
                except Exception:
                    pass
                loop.close()
            return True
        """
        )
    )
    pytester.makepyfile(
        dedent(
            """\
        import asyncio
        import pytest

        pytest_plugins = "pytest_asyncio"


        @pytest.mark.parametrize(
            "backend",
            [
                pytest.param("asyncio", marks=pytest.mark.asyncio),
                pytest.param("other", marks=pytest.mark.other_async),
            ],
        )
        async def test_async(backend: str) -> None:
            loop_name = type(asyncio.get_running_loop()).__name__
            if backend == "asyncio":
                assert loop_name == "CustomEventLoop"
            else:
                assert backend == "other"
                assert loop_name == "OtherBackendLoop"
        """
        )
    )
    result = pytester.runpytest("--asyncio-mode=strict", "-v")
    result.assert_outcomes(passed=2)
