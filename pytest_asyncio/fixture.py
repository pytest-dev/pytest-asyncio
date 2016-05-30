import asyncio
import itertools
import functools

import pytest  # noqa
import _pytest.python

from .utils import find_loop, maybe_accept_global_loop


class AsyncFixtureFunctionMarker(_pytest.python.FixtureFunctionMarker):

    def __init__(self, *args, accept_global_loop, **kwargs):
        super().__init__(*args, **kwargs)
        self.accept_global_loop = accept_global_loop

    def __call__(self, coroutine):
        if not asyncio.iscoroutinefunction(coroutine):
            raise ValueError('Only coroutine functions supported')

        @functools.wraps(coroutine)
        def inner(*args, **kwargs):
            event_loop = find_loop(itertools.chain(args, kwargs.values()))
            with maybe_accept_global_loop(
                    event_loop, self.accept_global_loop) as loop:
                return loop.run_until_complete(coroutine(*args, **kwargs))

        inner._pytestfixturefunction = self
        return inner


def async_fixture(scope='function', params=None, autouse=False, ids=None,
                  accept_global_loop=False):
    if callable(scope) and params is None and not autouse:
        # direct invocation
        marker = AsyncFixtureFunctionMarker(
            'function', params, autouse, accept_global_loop=accept_global_loop,
        )
        return marker(scope)
    if params is not None and not isinstance(params, (list, tuple)):
        params = list(params)
    return AsyncFixtureFunctionMarker(
        scope, params, autouse, ids=ids, accept_global_loop=accept_global_loop,
    )
