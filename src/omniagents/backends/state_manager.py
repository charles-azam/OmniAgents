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
from functools import cached_property
import os
import tarfile
import io

from anyagents.common import GCP_DATA_PATH
from anyagents import storage_utils

if TYPE_CHECKING:
    from anyagents.backends.execution_backend import ExecutionBackend


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
        Create a tar.gz archive of all files and upload to bucket.

        Archive is saved as project_id/timestamp.tar.gz for immutable snapshots.
        """
        working_dir = backend.get_working_directory()
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")

        # Create tar.gz archive in memory
        tar_buffer = io.BytesIO()
        with tarfile.open(fileobj=tar_buffer, mode='w:gz') as tar:
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
                content_bytes = content.encode('utf-8')

                # Add to tar archive
                tarinfo = tarfile.TarInfo(name=str(relative_path))
                tarinfo.size = len(content_bytes)
                tar.addfile(tarinfo=tarinfo, fileobj=io.BytesIO(content_bytes))

        # Upload single archive to bucket
        archive_path = GCP_DATA_PATH / backend.project_id / f"{timestamp}.tar.gz"
        storage_utils.write_to_storage(file_path=archive_path, content=tar_buffer.getvalue())

        return timestamp

    def load_latest(self, backend: "ExecutionBackend") -> bool:
        """
        Download and extract the latest tar.gz archive into the working directory.
        """
        working_dir = backend.get_working_directory()
        bucket = storage_utils.get_bucket()

        # List only tar.gz archives for this project
        prefix = f"{backend.project_id}/"
        archives = [blob for blob in bucket.list_blobs(prefix=prefix) if blob.name.endswith('.tar.gz')]

        if not archives:
            return False

        # Get latest archive (max by filename due to timestamp format)
        latest_archive = max(archives, key=lambda b: b.name)

        # Download archive as bytes
        archive_path = GCP_DATA_PATH / latest_archive.name
        archive_bytes = storage_utils.read_from_storage(file_path=archive_path, as_bytes=True)

        # Extract archive to working directory
        tar_buffer = io.BytesIO(archive_bytes)
        with tarfile.open(fileobj=tar_buffer, mode='r:gz') as tar:
            for member in tar.getmembers():
                if member.isfile():
                    file_content = tar.extractfile(member).read().decode('utf-8')
                    dest_path = working_dir / member.name
                    backend.write_file(file_path=dest_path, content=file_content)

        return True

    def cleanup(self, project_id: str) -> None:
        """Delete all archive files for this project."""
        bucket = storage_utils.get_bucket()
        prefix = f"{project_id}/"

        # List and delete all archives
        archives = [blob for blob in bucket.list_blobs(prefix=prefix) if blob.name.endswith('.tar.gz')]

        if not archives:
            return

        # Delete archives individually
        for blob in archives:
            try:
                blob.delete()
            except Exception:
                pass

    def list_snapshots(self, project_id: str) -> list[dict]:
        """List all archive snapshots for this project."""
        bucket = storage_utils.get_bucket()
        prefix = f"{project_id}/"

        # List all archives and extract timestamps from filenames
        archives = [blob for blob in bucket.list_blobs(prefix=prefix) if blob.name.endswith('.tar.gz')]

        snapshots = []
        for archive in archives:
            # Extract timestamp from filename: project_id/timestamp.tar.gz
            # archive.name is like "project_id/20251205_165713_634291.tar.gz"
            filename = archive.name.split('/')[-1]  # Get "20251205_165713_634291.tar.gz"
            timestamp_str = filename.replace('.tar.gz', '')  # Get "20251205_165713_634291"

            try:
                dt = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S_%f")
                snapshots.append({
                    "id": timestamp_str,
                    "timestamp": int(dt.timestamp()),
                    "message": f"Snapshot at {dt.strftime('%Y-%m-%d %H:%M:%S UTC')}"
                })
            except ValueError:
                # Skip malformed timestamps
                continue

        # Sort by timestamp, most recent first
        return sorted(snapshots, key=lambda s: s["timestamp"], reverse=True)


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
            repo_url: GitHub repo URL (defaults to env ANYAGENTS_GITHUB_STATE_REPO or 'charlesazam/anyagents-states')
            branch_prefix: Prefix for state branches (default: "state/")
            github_token: GitHub personal access token (defaults to env GITHUB_TOKEN)
        """
        self.repo_url = repo_url or os.getenv("ANYAGENTS_GITHUB_STATE_REPO", "charlesazam/anyagents-states")

        # Normalize repo URL to full format
        if not self.repo_url.startswith("http"):
            # Convert owner/repo to full URL
            self.repo_url = f"https://github.com/{self.repo_url}.git"
        if not self.repo_url.endswith(".git"):
            self.repo_url += ".git"

        self.branch_prefix = branch_prefix
        self.github_token = github_token or os.getenv("ANYAGENTS_GITHUB_API_KEY")

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
            # Combine git init commands into single execution to reduce overhead
            init_commands = (
                f"git init && "
                f"git remote add origin {auth_url} && "
                f'git config user.name "Anyagents" && '
                f'git config user.email "noreply@anyagents.ai"'
            )
            backend.execute_command(command=init_commands)

        # Combine branch check and checkout into fewer commands
        # Try to fetch and checkout in one operation
        fetch_result = backend.execute_command(command=f"git fetch origin {branch_name} 2>/dev/null || true")

        # Check if we're already on the branch
        current_branch_result = backend.execute_command(command="git rev-parse --abbrev-ref HEAD 2>/dev/null || echo ''")
        current_branch = current_branch_result.output.strip()

        if current_branch == branch_name:
            # Already on correct branch, check if remote tracking exists
            return fetch_result.exit_code == 0

        # Try to checkout branch (will succeed if exists locally or remotely)
        checkout_result = backend.execute_command(
            command=f"git checkout {branch_name} 2>/dev/null || git checkout -b {branch_name} origin/{branch_name} 2>/dev/null || git checkout -b {branch_name}"
        )

        # Return True if remote branch existed (fetch succeeded)
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

        # Combine add, status check, and commit into fewer commands
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        commit_msg = message or f"Snapshot at {timestamp}"

        # Try to add and commit in one go, get SHA if successful
        # If nothing to commit, git commit will fail and we'll get the current SHA
        commit_command = (
            f"git add . && "
            f"git diff-index --quiet HEAD || git commit -m '{commit_msg}'"
        )
        commit_result = backend.execute_command(command=commit_command)

        # Get current SHA (whether we just committed or not)
        sha_result = backend.execute_command(command="git rev-parse HEAD 2>/dev/null || echo 'no-changes'")
        current_sha = sha_result.output.strip()

        # Only push if we actually made a commit (commit_result succeeded)
        if commit_result.exit_code == 0:
            backend.execute_command(command=f"git push origin {branch_name} --force")

        return current_sha

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

    @cached_property
    def _github_client(self):
        """Get cached GitHub client."""
        from github import Github, Auth
        return Github(auth=Auth.Token(token=self.github_token))

    @cached_property
    def _github_repo(self):
        """Get cached GitHub repository."""
        return self._github_client.get_repo(full_name_or_id=self.repo_path)

    def cleanup(self, project_id: str) -> None:
        """Delete the branch for this project."""
        if not self.github_token:
            # No token, cannot delete branch
            return

        from github import GithubException

        branch_name = self._get_branch_name(project_id=project_id)

        repo = self._github_repo

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

        from github import GithubException

        branch_name = self._get_branch_name(project_id=project_id)

        repo = self._github_repo

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
