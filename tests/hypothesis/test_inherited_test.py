import hypothesis.strategies as st
from hypothesis import given
import pytest


class BaseClass:
    @pytest.mark.asyncio
    @given(value=st.integers())
    async def test_hypothesis(self, value: int) -> None:
        assert True


class TestOne(BaseClass):
    """During the first execution the Hypothesis test is wrapped in a synchronous function."""

    pass


class TestTwo(BaseClass):
    """Execute the test a second time to ensure that the test receives a fresh event loop."""

    pass
