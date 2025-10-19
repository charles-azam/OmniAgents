"""
Pytest configuration and fixtures for the tools tests.
"""
import os
import shutil

import pytest


@pytest.fixture(scope="session")
def test_dir() -> str:
    """Return the absolute path to the test directory."""
    return os.path.dirname(os.path.abspath(__file__))


@pytest.fixture(scope="session")
def test_data_dir(test_dir: str) -> str:
    """Return the absolute path to the test data directory."""
    return os.path.join(test_dir, "testdata")


@pytest.fixture(scope="session")
def temp_dir(test_dir: str) -> str:
    """
    Create and return a temporary directory for test files.
    This directory will be deleted after all tests are completed.
    """
    # Create the temp directory
    temp_path = os.path.join(test_dir, "temp")
    os.makedirs(temp_path, exist_ok=True)

    yield temp_path

    # Cleanup after all tests
    if os.path.exists(temp_path):
        shutil.rmtree(temp_path)
