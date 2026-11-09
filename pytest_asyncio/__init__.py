"""The main point for importing pytest-asyncio items."""

from __future__ import annotations

from importlib.metadata import version

from .plugin import PytestAsyncioUnhandledExceptionWarning, fixture, is_async_test

__version__ = version(__name__)

__all__ = ("PytestAsyncioUnhandledExceptionWarning", "fixture", "is_async_test")
