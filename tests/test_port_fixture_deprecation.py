from __future__ import annotations

from textwrap import dedent

import pytest
from pytest import Pytester


@pytest.mark.parametrize(
    "fixture_name",
    [
        "unused_tcp_port",
        "unused_udp_port",
        "unused_tcp_port_factory",
        "unused_udp_port_factory",
    ],
)
def test_port_fixtures_are_deprecated(pytester: Pytester, fixture_name: str) -> None:
    pytester.makepyfile(dedent(f"""\
            import pytest

            def test_deprecated(request):
                with pytest.warns(
                    DeprecationWarning,
                    match="The {fixture_name} fixture is deprecated",
                ):
                    request.getfixturevalue("{fixture_name}")
            """))

    result = pytester.runpytest()

    result.assert_outcomes(passed=1)
