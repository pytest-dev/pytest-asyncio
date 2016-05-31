class MissingLoopFixture(Exception):
    """Raised if a test coroutine function does not request a loop fixture."""
    pass
