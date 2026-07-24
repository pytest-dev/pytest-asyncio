"""Example patterns for isolating async applications in tests.

Run with:  pytest isolate_async_apps_example.py -v
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Demo application (pretend this is api/main.py in your project)
# ---------------------------------------------------------------------------

class FakeUploadService:
    """Async service with a mutable default path."""

    def __init__(self, upload_dir: Path | None = None) -> None:
        self.upload_dir = upload_dir or Path("/tmp/uploads")
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    async def save(self, name: str, data: bytes) -> Path:
        dest = self.upload_dir / name
        dest.write_bytes(data)
        return dest


class FakeApp:
    """Minimal async app that owns a service."""

    def __init__(self, upload_dir: Path | None = None) -> None:
        self.upload_service = FakeUploadService(upload_dir=upload_dir)


# Global singleton-like app (common in FastAPI patterns)
app = FakeApp()


# -- FIX 1: fixture-scoped import


@pytest.fixture
async def fresh_app():
    """Import app inside the fixture so reloads are visible.

    If another test calls ``importlib.reload(api.main)``, this fixture
    will see the new ``app`` object on its next invocation.
    """
    # In a real project:  from api.main import app
    import __main__ as _api_main  # stand-in for the real module

    # If you need to mutate the app (dependency overrides, etc.),
    # do it here and yield, then clean up in teardown.
    _api_main.app.upload_service = FakeUploadService()
    yield _api_main.app
    # Teardown: reset any overrides so the next test starts clean
    _api_main.app.upload_service = FakeUploadService()


@pytest.mark.asyncio
async def test_upload_with_fresh_app(fresh_app: FakeApp):
    """Uses the fixture-scoped app import."""
    path = await fresh_app.upload_service.save("a.txt", b"hello")
    assert path.read_bytes() == b"hello"


@pytest.mark.asyncio
async def test_app_is_reloaded(fresh_app: FakeApp):
    """After a reload, the fixture still sees the current app."""
    import importlib

    import __main__ as _api_main

    # Simulate another test mutating the module
    old_app = _api_main.app
    _api_main.app = FakeApp()  # new instance
    importlib.reload(_api_main)  # or reload(api.main) in real code

    # The fixture should now serve the new app
    current = fresh_app
    assert current is not old_app


# -- FIX 2: temporary directories


@pytest.fixture
async def upload_service(tmp_path: Path):
    """Service backed by a unique temp dir per test."""
    service = FakeUploadService(upload_dir=tmp_path / "uploads")
    yield service
    # tmp_path is automatically cleaned up by pytest


@pytest.mark.asyncio
async def test_upload_isolated(upload_service: FakeUploadService):
    path = await upload_service.save("b.txt", b"world")
    assert path.read_bytes() == b"world"


@pytest.mark.asyncio
async def test_upload_does_not_bleed(upload_service: FakeUploadService):
    """The previous test's file should not exist here."""
    files = list(upload_service.upload_dir.iterdir())
    assert files == []  # passes because each test gets its own tmp_path


# ---------------------------------------------------------------------------
# Combined pattern: async app + temp dir in one fixture
# ---------------------------------------------------------------------------


@pytest.fixture
async def isolated_app(tmp_path: Path):
    """Full isolation: fresh import + fresh filesystem."""
    import __main__ as _api_main

    app = _api_main.app
    app.upload_service = FakeUploadService(upload_dir=tmp_path / "uploads")
    yield app
    app.upload_service = FakeUploadService()


@pytest.mark.asyncio
async def test_end_to_end(isolated_app: FakeApp):
    path = await isolated_app.upload_service.save("c.txt", b"combined")
    assert path.read_bytes() == b"combined"


# -- end of example
