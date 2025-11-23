"""Utilities for managing benchmark task fixtures."""
import shutil
from pathlib import Path
from typing import Optional


def get_fixtures_dir() -> Path:
    """Get the path to the fixtures directory."""
    return Path(__file__).parent / "fixtures"


def copy_fixture_dir(fixture_name: str, dest_dir: Path) -> None:
    """
    Copy an entire fixture directory to a destination.

    Args:
        fixture_name: Name of the fixture subdirectory
        dest_dir: Destination directory (workspace)

    Example:
        copy_fixture_dir("search_replace", workspace_dir)
        # Copies fixtures/search_replace/* to workspace_dir/*
    """
    fixtures_dir = get_fixtures_dir()
    fixture_path = fixtures_dir / fixture_name

    if not fixture_path.exists():
        raise FileNotFoundError(f"Fixture directory not found: {fixture_path}")

    # Create destination if it doesn't exist
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Copy all contents from fixture to destination
    for item in fixture_path.iterdir():
        if item.is_file():
            shutil.copy2(item, dest_dir / item.name)
        elif item.is_dir():
            shutil.copytree(item, dest_dir / item.name, dirs_exist_ok=True)


def copy_fixture_file(fixture_name: str, file_path: str, dest_dir: Path, dest_name: Optional[str] = None) -> None:
    """
    Copy a single file from a fixture directory to a destination.

    Args:
        fixture_name: Name of the fixture subdirectory
        file_path: Path to the file within the fixture directory
        dest_dir: Destination directory
        dest_name: Optional different name for the destination file

    Example:
        copy_fixture_file("bug_fix", "calculator.py", workspace_dir)
        # Copies fixtures/bug_fix/calculator.py to workspace_dir/calculator.py
    """
    fixtures_dir = get_fixtures_dir()
    source_file = fixtures_dir / fixture_name / file_path

    if not source_file.exists():
        raise FileNotFoundError(f"Fixture file not found: {source_file}")

    # Create destination directory if needed
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Determine destination filename
    if dest_name is None:
        dest_name = source_file.name

    dest_file = dest_dir / dest_name
    shutil.copy2(source_file, dest_file)


def get_fixture_content(fixture_name: str, file_path: str) -> str:
    """
    Read the content of a fixture file.

    Args:
        fixture_name: Name of the fixture subdirectory
        file_path: Path to the file within the fixture directory

    Returns:
        Content of the file as a string

    Example:
        content = get_fixture_content("bug_fix", "calculator.py")
    """
    fixtures_dir = get_fixtures_dir()
    file_full_path = fixtures_dir / fixture_name / file_path

    if not file_full_path.exists():
        raise FileNotFoundError(f"Fixture file not found: {file_full_path}")

    return file_full_path.read_text()


def list_fixture_files(fixture_name: str) -> list[Path]:
    """
    List all files in a fixture directory recursively.

    Args:
        fixture_name: Name of the fixture subdirectory

    Returns:
        List of Path objects for all files in the fixture

    Example:
        files = list_fixture_files("search_replace")
    """
    fixtures_dir = get_fixtures_dir()
    fixture_path = fixtures_dir / fixture_name

    if not fixture_path.exists():
        raise FileNotFoundError(f"Fixture directory not found: {fixture_path}")

    return list(fixture_path.rglob("*"))
