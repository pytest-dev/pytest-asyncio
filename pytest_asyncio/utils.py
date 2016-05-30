import asyncio
import contextlib

from .exceptions import MissingLoopFixture


class ForbiddenEventLoopPolicy(asyncio.AbstractEventLoopPolicy):
    """An event loop policy that raises errors on any operation."""
    pass


@contextlib.contextmanager
def maybe_accept_global_loop(event_loop, accept_global_loop):
    if not accept_global_loop and event_loop is None:
        raise MissingLoopFixture('A loop fixture must be provided'
                                 ' when a global loop is forbidden')

    policy = asyncio.get_event_loop_policy()
    try:
        global_event_loop = policy.get_event_loop()
        if accept_global_loop and event_loop is None:
            event_loop = global_event_loop

        if not accept_global_loop:
            asyncio.set_event_loop_policy(ForbiddenEventLoopPolicy())
        else:
            policy.set_event_loop(event_loop)

        yield event_loop

    finally:
        if not accept_global_loop:
            asyncio.set_event_loop_policy(policy)


def find_loop(iterable):
    for item in iterable:
        if isinstance(item, asyncio.AbstractEventLoop):
            return item
