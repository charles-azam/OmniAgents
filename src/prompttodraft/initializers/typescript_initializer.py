"""TypeScript project initializer using npm package manager."""

from prompttodraft.initializers.base import ProjectInitializer


class TypeScriptInitializer(ProjectInitializer):
    """
    Initializer for TypeScript projects using npm package manager.

    Handles README.md, .gitignore, npm setup, and TypeScript configuration.
    """

    @property
    def language_name(self) -> str:
        """Get the language name."""
        return "TypeScript"

    def get_docker_image(self) -> str:
        """Get the Docker image for TypeScript projects."""
        return "node:20-slim"

    def get_docker_env_vars(self) -> dict[str, str]:
        """Get Docker environment variables for Node/npm."""
        return {
            "NPM_CONFIG_CACHE": "/workspace/.npm",
            "NODE_PATH": "/workspace/node_modules",
        }

    def get_package_manager_commands(self) -> dict[str, str]:
        """Get npm package manager command patterns."""
        return {
            "run": "npm run {script}",
            "install": "npm install {package}",
            "uninstall": "npm uninstall {package}",
            "test": "npm test -- {path}",
            "build": "npm run build",
        }

    def is_initialized(self) -> bool:
        """
        Check if TypeScript project is initialized.

        Returns:
            True if package.json exists, False otherwise
        """
        package_json_path = f"{self.working_dir}/package.json"
        return self.backend.file_exists(path=package_json_path) is not None

    def initialize(self) -> None:
        """
        Initialize TypeScript project.

        Creates README.md, .gitignore with TypeScript patterns, runs npm init if needed,
        installs TypeScript, creates tsconfig.json, and installs dependencies.

        Raises:
            RuntimeError: If any initialization step fails
        """
        # Ensure README.md exists
        readme_path = f"{self.working_dir}/README.md"
        if self.backend.file_exists(path=readme_path) is None:
            self.backend.write_file(file_path=readme_path, content="")

        # Ensure .gitignore exists with TypeScript patterns
        gitignore_path = f"{self.working_dir}/.gitignore"
        if self.backend.file_exists(path=gitignore_path) is None:
            gitignore_patterns = [
                "node_modules/",
                "dist/",
                "build/",
                "*.js.map",
                ".next/",
                ".nuxt/",
                ".cache/",
                "coverage/",
                ".env.local",
                ".env.*.local",
                "*.tsbuildinfo",
            ]
            self.backend.write_file(file_path=gitignore_path, content="\n".join(gitignore_patterns) + "\n")

        # Run npm init if package.json doesn't exist
        package_json_path = f"{self.working_dir}/package.json"
        if self.backend.file_exists(path=package_json_path) is None:
            result = self.backend.execute_command(
                command=f'cd "{self.working_dir}" && npm init -y',
                timeout=120000
            )
            if result.exit_code != 0:
                raise RuntimeError(
                    f"'npm init' failed with exit code {result.exit_code}. Output: {result.output}"
                )

            # Install TypeScript and related dependencies
            result = self.backend.execute_command(
                command=f'cd "{self.working_dir}" && npm install --save-dev typescript @types/node',
                timeout=300000
            )
            if result.exit_code != 0:
                raise RuntimeError(
                    f"'npm install typescript' failed with exit code {result.exit_code}. Output: {result.output}"
                )

        # Create tsconfig.json if it doesn't exist
        tsconfig_path = f"{self.working_dir}/tsconfig.json"
        if self.backend.file_exists(path=tsconfig_path) is None:
            tsconfig_content = """{
  "compilerOptions": {
    "target": "ES2020",
    "module": "commonjs",
    "lib": ["ES2020"],
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}
"""
            self.backend.write_file(file_path=tsconfig_path, content=tsconfig_content)

        # Always run npm install to ensure dependencies are up to date
        result = self.backend.execute_command(
            command=f'cd "{self.working_dir}" && npm install',
            timeout=300000
        )
        if result.exit_code != 0:
            raise RuntimeError(
                f"'npm install' failed with exit code {result.exit_code}. Output: {result.output}"
            )
