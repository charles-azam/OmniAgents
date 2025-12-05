"""
State management for execution backends.

This module defines abstract and concrete state managers for persisting
backend state to different storage backends (GCS, GitHub, or none).
"""
from abc import ABC, abstractmethod
from pathlib import Path
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from enum import Enum
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

from prompttodraft.common import GCP_DATA_PATH
from prompttodraft import storage_utils

if TYPE_CHECKING:
    from prompttodraft.backends.execution_backend import ExecutionBackend


class StorageType(Enum):
    """Storage backend types for state persistence."""
    GIT = 'git'      # GitHub branches (default)
    GCS = 'gcs'      # Google Cloud Storage buckets
    NONE = None      # No state persistence




class StateManager(ABC):
    """Abstract interface for project state persistence."""

    @abstractmethod
    def save_snapshot(self, backend: "ExecutionBackend", message: str = "") -> str:
        """
        Save current backend working directory state.

        Args:
            backend: ExecutionBackend instance to save state from
            message: Optional message describing this snapshot

        Returns:
            snapshot_id: Identifier for this snapshot (commit SHA, timestamp, etc.)
        """
        pass

    @abstractmethod
    def load_latest(self, backend: "ExecutionBackend") -> bool:
        """
        Load latest snapshot into backend working directory.

        Args:
            backend: ExecutionBackend instance to load state into

        Returns:
            True if snapshot was loaded, False if no snapshots exist
        """
        pass

    @abstractmethod
    def cleanup(self, project_id: str) -> None:
        """
        Delete all state for this project.

        Args:
            project_id: Project identifier to clean up
        """
        pass

    @abstractmethod
    def list_snapshots(self, project_id: str) -> list[dict]:
        """
        List all available snapshots with metadata.

        Args:
            project_id: Project identifier

        Returns:
            List of snapshot metadata dicts
        """
        pass


class GCSStateManager(StateManager):
    """Persist state to Google Cloud Storage buckets (original implementation)."""

    def save_snapshot(self, backend: "ExecutionBackend", message: str = "") -> str:
        """
        Sync all files from working directory to bucket with timestamp.

        Files are saved under project_id/timestamp/ to create immutable snapshots.
        This prevents deleted files from being restored on reload.
        """
        working_dir = backend.get_working_directory()

        # Create timestamp snapshot
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        project_data_path = GCP_DATA_PATH / backend.project_id / timestamp

        # List all files recursively
        files = backend.list_directory(path=working_dir, recursive=True)

        for file_info in files:
            if file_info.is_dir:
                continue

            # Get relative path from working directory
            file_path = Path(file_info.path)
            relative_path = file_path.relative_to(working_dir)

            # Skip hidden files and common build artifacts
            if any(part.startswith('.') for part in relative_path.parts):
                continue
            if any(part in ('__pycache__', 'node_modules') for part in relative_path.parts):
                continue

            # Read file content
            content = backend.read_file(file_path=file_path)

            # Write to bucket with timestamp (storage_utils expects path relative to GCP_DATA_PATH)
            bucket_path = project_data_path / relative_path
            storage_utils.write_to_storage(file_path=bucket_path, content=content)

        return timestamp

    def load_latest(self, backend: "ExecutionBackend") -> bool:
        """
        Load all files from the latest snapshot in bucket into the working directory.

        Finds the most recent timestamp snapshot under project_id/ and loads all files
        from that snapshot. This ensures deleted files are not restored.
        """
        working_dir = backend.get_working_directory()
        bucket = storage_utils.get_bucket()

        # Single list_blobs call - collect all blobs at once
        prefix = f"{backend.project_id}/"
        all_blobs = list(bucket.list_blobs(prefix=prefix))

        if not all_blobs:
            # No snapshots exist yet
            return False

        # Find all timestamp directories from collected blobs
        timestamps = set()
        for blob in all_blobs:
            # Extract timestamp from blob path: project_id/timestamp/file/path
            blob_path = Path(blob.name)
            parts = blob_path.parts

            if len(parts) >= 2 and parts[0] == backend.project_id:
                timestamps.add(parts[1])

        # Get the latest timestamp (lexicographically sorted due to timestamp format)
        latest_timestamp = max(timestamps)

        # Load files from latest snapshot using already-collected blobs
        snapshot_prefix = f"{backend.project_id}/{latest_timestamp}/"
        project_data_path = GCP_DATA_PATH / backend.project_id / latest_timestamp

        # Filter blobs for latest snapshot
        snapshot_blobs = [blob for blob in all_blobs if blob.name.startswith(snapshot_prefix)]

        def download_and_write_blob(blob):
            # Get relative path from snapshot directory
            blob_path = Path(blob.name)
            # Remove project_id/timestamp/ prefix to get file relative path
            relative_path = blob_path.relative_to(backend.project_id).relative_to(latest_timestamp)

            # Read from bucket
            bucket_file_path = project_data_path / relative_path
            content = storage_utils.read_from_storage(file_path=bucket_file_path)

            # Write to working directory
            dest_path = working_dir / relative_path
            backend.write_file(file_path=dest_path, content=content)

        # Download files in parallel
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(download_and_write_blob, blob) for blob in snapshot_blobs]
            for future in as_completed(futures):
                future.result()  # Raise any exceptions that occurred

        return True

    def cleanup(self, project_id: str) -> None:
        """Delete all bucket files for this project."""
        bucket = storage_utils.get_bucket()
        prefix = f"{project_id}/"

        # Collect all blobs first, then batch delete
        blobs_to_delete = list(bucket.list_blobs(prefix=prefix))

        if not blobs_to_delete:
            return

        # Use batch API for faster deletion
        with bucket.client.batch():
            for blob in blobs_to_delete:
                try:
                    blob.delete()
                except Exception:
                    # Ignore errors if blob already deleted (eventual consistency)
                    pass

    def list_snapshots(self, project_id: str) -> list[dict]:
        """List all timestamp snapshots for this project."""
        bucket = storage_utils.get_bucket()
        prefix = f"{project_id}/"
        timestamps = set()

        for blob in bucket.list_blobs(prefix=prefix):
            blob_path = Path(blob.name)
            parts = blob_path.parts

            if len(parts) >= 2 and parts[0] == project_id:
                timestamps.add(parts[1])

        # Convert timestamps to metadata format
        snapshots = []
        for ts in sorted(timestamps, reverse=True):
            # Parse timestamp: YYYYMMDD_HHMMSS_ffffff
            try:
                dt = datetime.strptime(ts, "%Y%m%d_%H%M%S_%f")
                snapshots.append({
                    "id": ts,
                    "timestamp": int(dt.timestamp()),
                    "message": f"Snapshot at {dt.strftime('%Y-%m-%d %H:%M:%S UTC')}"
                })
            except ValueError:
                # Skip malformed timestamps
                continue

        return snapshots


class GitStateManager(StateManager):
    """Persist state to Git branches on GitHub."""

    def __init__(
        self,
        repo_url: str | None = None,
        branch_prefix: str = "state/",
        github_token: str | None = None
    ):
        """
        Args:
            repo_url: GitHub repo URL (defaults to env PROMPTTODRAFT_GITHUB_STATE_REPO or 'charlesazam/prompttodraft-states')
            branch_prefix: Prefix for state branches (default: "state/")
            github_token: GitHub personal access token (defaults to env GITHUB_TOKEN)
        """
        self.repo_url = repo_url or os.getenv("PROMPTTODRAFT_GITHUB_STATE_REPO", "charlesazam/prompttodraft-states")

        # Normalize repo URL to full format
        if not self.repo_url.startswith("http"):
            # Convert owner/repo to full URL
            self.repo_url = f"https://github.com/{self.repo_url}.git"
        if not self.repo_url.endswith(".git"):
            self.repo_url += ".git"

        self.branch_prefix = branch_prefix
        self.github_token = github_token or os.getenv("PROMPTTODRAFT_GITHUB_API_KEY")

        # Extract owner/repo from URL for API calls
        # https://github.com/owner/repo.git -> owner/repo
        self.repo_path = self.repo_url.replace("https://github.com/", "").replace(".git", "")

    def _get_branch_name(self, project_id: str) -> str:
        """Convert project_id to branch name."""
        # Sanitize project_id for Git branch naming
        safe_id = project_id.replace(" ", "-").replace("_", "-")
        return f"{self.branch_prefix}{safe_id}"

    def _get_authenticated_url(self) -> str:
        """Get repo URL with token authentication."""
        if self.github_token:
            # Insert token into URL: https://oauth2:TOKEN@github.com/owner/repo.git
            return self.repo_url.replace("https://", f"https://oauth2:{self.github_token}@")
        return self.repo_url

    def _ensure_gitignore(self, backend: "ExecutionBackend") -> None:
        """Ensure .gitignore exists in working directory."""
        working_dir = backend.get_working_directory()
        gitignore_path = working_dir / ".gitignore"

        if not backend.file_exists(path=gitignore_path):
            backend.write_file(
                file_path=gitignore_path,
                content=".venv/\n__pycache__/\n*.pyc\n.pytest_cache/\n.cache/\nnode_modules/\n.git/\n"
            )

    def _is_git_initialized(self, backend: "ExecutionBackend") -> bool:
        """Check if git is initialized in working directory."""
        result = backend.execute_command(command="git status")
        return result.exit_code == 0

    def _ensure_git_initialized(self, backend: "ExecutionBackend", branch_name: str) -> bool:
        """
        Ensure git is initialized with proper configuration and branch exists locally.

        This method guarantees that:
        1. Git is initialized in the working directory
        2. Remote origin is configured
        3. User name/email are set
        4. The branch exists locally (either from remote or newly created)

        Args:
            backend: ExecutionBackend instance
            branch_name: Name of the branch to ensure exists

        Returns:
            True if branch existed on remote (files available to load)
            False if branch was newly created (no files to load)
        """
        auth_url = self._get_authenticated_url()

        # Initialize git if not already initialized
        if not self._is_git_initialized(backend=backend):
            backend.execute_command(command="git init")
            backend.execute_command(command=f"git remote add origin {auth_url}")
            backend.execute_command(command='git config user.name "PromptToDraft"')
            backend.execute_command(command='git config user.email "noreply@prompttodraft.ai"')

        # Ensure we're on the correct branch
        # Check current branch
        current_branch_result = backend.execute_command(command="git rev-parse --abbrev-ref HEAD")
        current_branch = current_branch_result.output.strip()

        if current_branch != branch_name:
            # Check if branch exists locally
            branch_exists_result = backend.execute_command(command=f"git rev-parse --verify {branch_name}")

            if branch_exists_result.exit_code == 0:
                # Branch exists locally, just checkout
                backend.execute_command(command=f"git checkout {branch_name}")
            else:
                # Branch doesn't exist locally, try to fetch from remote
                fetch_result = backend.execute_command(command=f"git fetch origin {branch_name}")

                if fetch_result.exit_code == 0:
                    # Branch exists on remote, create tracking branch
                    backend.execute_command(command=f"git checkout -b {branch_name} origin/{branch_name}")
                    return True
                else:
                    # Branch doesn't exist on remote, create new local branch
                    backend.execute_command(command=f"git checkout -b {branch_name}")
                    return False

        # Already on correct branch, check if remote exists
        fetch_result = backend.execute_command(command=f"git fetch origin {branch_name}")
        return fetch_result.exit_code == 0

    def save_snapshot(self, backend: "ExecutionBackend", message: str = "") -> str:
        """
        Save working directory to Git branch.

        Assumes git is already initialized (by load_latest during backend start).
        Creates a commit with current files and pushes to remote.

        Args:
            backend: ExecutionBackend instance
            message: Commit message (defaults to timestamped snapshot message)

        Returns:
            Commit SHA or "no-changes" if nothing to commit
        """
        branch_name = self._get_branch_name(project_id=backend.project_id)

        # Ensure .gitignore exists
        self._ensure_gitignore(backend=backend)

        # Stage all files (gitignore handles filtering)
        backend.execute_command(command="git add .")

        # Check if there are changes to commit
        status_result = backend.execute_command(command="git status --porcelain")
        if not status_result.output.strip():
            # No changes, return existing commit SHA or "no-changes"
            sha_result = backend.execute_command(command="git rev-parse HEAD")
            return sha_result.output.strip() if sha_result.exit_code == 0 else "no-changes"

        # Commit changes
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        commit_msg = message or f"Snapshot at {timestamp}"
        # Use single quotes to avoid shell escaping issues
        backend.execute_command(command=f"git commit -m '{commit_msg}'")

        # Push to remote
        backend.execute_command(command=f"git push origin {branch_name} --force")

        # Get commit SHA
        sha_result = backend.execute_command(command="git rev-parse HEAD")
        return sha_result.output.strip()

    def load_latest(self, backend: "ExecutionBackend") -> bool:
        """
        Load latest snapshot from Git branch.

        Ensures git is initialized and branch exists locally.
        If branch exists on remote, loads the latest files.

        Returns:
            True if files were loaded from remote
            False if no remote branch exists (new project)
        """
        branch_name = self._get_branch_name(project_id=backend.project_id)

        # Ensure git is initialized and branch exists locally
        # Returns True if branch existed on remote, False if newly created
        branch_existed_remotely = self._ensure_git_initialized(backend=backend, branch_name=branch_name)

        if branch_existed_remotely:
            # Branch exists on remote, load latest files
            backend.execute_command(command=f"git reset --hard origin/{branch_name}")
            return True
        else:
            # New branch, no files to load
            return False

    def cleanup(self, project_id: str) -> None:
        """Delete the branch for this project."""
        if not self.github_token:
            # No token, cannot delete branch
            return

        from github import Github, GithubException, Auth

        branch_name = self._get_branch_name(project_id=project_id)

        gh = Github(auth=Auth.Token(token=self.github_token))
        repo = gh.get_repo(full_name_or_id=self.repo_path)

        # Try to get and delete the branch
        try:
            ref = repo.get_git_ref(ref=f"heads/{branch_name}")
            ref.delete()
        except GithubException:
            # Branch doesn't exist, nothing to delete
            pass

    def list_snapshots(self, project_id: str) -> list[dict]:
        """List all commits on the project branch."""
        if not self.github_token:
            # No token, cannot list commits
            return []

        from github import Github, GithubException, Auth

        branch_name = self._get_branch_name(project_id=project_id)

        gh = Github(auth=Auth.Token(token=self.github_token))
        repo = gh.get_repo(full_name_or_id=self.repo_path)

        # Try to get the branch and its commits
        try:
            branch = repo.get_branch(branch=branch_name)
            commits = repo.get_commits(sha=branch.commit.sha)

            snapshots = []
            for commit in commits:
                snapshots.append({
                    "id": commit.sha,
                    "author": commit.commit.author.name,
                    "timestamp": int(commit.commit.author.date.timestamp()),
                    "message": commit.commit.message
                })

            return snapshots
        except GithubException:
            # Branch doesn't exist
            return []


class NoOpStateManager(StateManager):
    """State manager that does nothing (for storage=None)."""

    def save_snapshot(self, backend: "ExecutionBackend", message: str = "") -> str:
        """No-op save."""
        return ""

    def load_latest(self, backend: "ExecutionBackend") -> bool:
        """No-op load."""
        return False

    def cleanup(self, project_id: str) -> None:
        """No-op cleanup."""
        pass

    def list_snapshots(self, project_id: str) -> list[dict]:
        """No-op list."""
        return []
