"""Python project initializer using uv package manager."""

from prompttodraft.initializers.base import ProjectInitializer


class PythonInitializer(ProjectInitializer):
    """
    Initializer for Python projects using uv package manager.

    Handles README.md, .gitignore, uv installation, and project setup.
    """

    def initialize(self) -> None:
        """
        Initialize Python project.

        Creates README.md, .gitignore with Python patterns, ensures uv is installed,
        runs uv init if needed, and synchronizes dependencies.

        Raises:
            RuntimeError: If any initialization step fails
        """
        # Ensure README.md exists
        readme_path = f"{self.working_dir}/README.md"
        if self.backend.file_exists(path=readme_path) is None:
            self.backend.write_file(file_path=readme_path, content="")

        # Ensure .gitignore exists with Python patterns
        gitignore_path = f"{self.working_dir}/.gitignore"
        if self.backend.file_exists(path=gitignore_path) is None:
            gitignore_patterns = [
                ".venv/",
                "__pycache__/",
                "*.pyc",
                "*.pyo",
                "*.pyd",
                ".pytest_cache/",
                ".cache/",
                "*.egg-info/",
                "dist/",
                "build/",
                ".mypy_cache/",
                ".ruff_cache/",
            ]
            self.backend.write_file(file_path=gitignore_path, content="\n".join(gitignore_patterns) + "\n")

        # Ensure uv is installed
        self._ensure_uv_installed()

        # Run uv init if pyproject.toml doesn't exist
        pyproject_path = f"{self.working_dir}/pyproject.toml"
        if self.backend.file_exists(path=pyproject_path) is None:
            result = self.backend.execute_command(
                command=f'export PATH="$HOME/.local/bin:$PATH" && cd "{self.working_dir}" && uv init',
                timeout=120000
            )
            if result.exit_code != 0:
                raise RuntimeError(
                    f"'uv init' failed with exit code {result.exit_code}. Output: {result.output}"
                )

        # Run uv sync
        result = self.backend.execute_command(
            command=f'export PATH="$HOME/.local/bin:$PATH" && cd "{self.working_dir}" && uv sync',
            timeout=300000
        )
        if result.exit_code != 0:
            raise RuntimeError(
                f"'uv sync' failed with exit code {result.exit_code}. Output: {result.output}"
            )

    def _ensure_uv_installed(self) -> None:
        """
        Ensure uv package manager is installed.

        Checks if uv is available in PATH, installs it if not found.

        Raises:
            RuntimeError: If uv installation fails
        """
        uv_check = self.backend.execute_command(
            command='export PATH="$HOME/.local/bin:$PATH" && command -v uv',
            timeout=10000,
        )

        if uv_check.exit_code != 0:
            install_command = "curl -LsSf https://astral.sh/uv/install.sh | sh"
            install_result = self.backend.execute_command(
                command=install_command,
                timeout=120000,
            )

            if install_result.exit_code != 0:
                raise RuntimeError(
                    f"Failed to install uv. Exit code: {install_result.exit_code}. Output: {install_result.output}"
                )
