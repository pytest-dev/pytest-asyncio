from __future__ import annotations

from textwrap import dedent

from pytest import Pytester


def test_returns_false_for_sync_item(pytester: Pytester):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(
        dedent(
            """\
            import pytest
            import pytest_asyncio

            def test_sync():
                pass

            def pytest_collection_modifyitems(items):
                async_tests = [
                    item
                    for item in items
                    if pytest_asyncio.is_async_test(item)
                ]
                assert len(async_tests) == 0
            """
        )
    )
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=1)


def test_returns_true_for_marked_coroutine_item_in_strict_mode(pytester: Pytester):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(
        dedent(
            """\
            import pytest
            import pytest_asyncio

            @pytest.mark.asyncio
            async def test_coro():
                pass

            def pytest_collection_modifyitems(items):
                async_tests = [
                    item
                    for item in items
                    if pytest_asyncio.is_async_test(item)
                ]
                assert len(async_tests) == 1
            """
        )
    )
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(passed=1)


def test_returns_false_for_unmarked_coroutine_item_in_strict_mode(pytester: Pytester):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(
        dedent(
            """\
            import pytest
            import pytest_asyncio

            async def test_coro():
                pass

            def pytest_collection_modifyitems(items):
                async_tests = [
                    item
                    for item in items
                    if pytest_asyncio.is_async_test(item)
                ]
                assert len(async_tests) == 0
            """
        )
    )
    result = pytester.runpytest("--asyncio-mode=strict")
    result.assert_outcomes(failed=1)


def test_returns_true_for_unmarked_coroutine_item_in_auto_mode(pytester: Pytester):
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function")
    pytester.makepyfile(
        dedent(
            """\
            import pytest
            import pytest_asyncio

            async def test_coro():
                pass

            def pytest_collection_modifyitems(items):
                async_tests = [
                    item
                    for item in items
                    if pytest_asyncio.is_async_test(item)
                ]
                assert len(async_tests) == 1
            """
        )
    )
    result = pytester.runpytest("--asyncio-mode=auto")
    result.assert_outcomes(passed=1)
