"""Shared fixtures for the test suite."""

from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    """Directory holding the sample OpenAPI documents."""
    return Path(__file__).parent / "fixtures"
