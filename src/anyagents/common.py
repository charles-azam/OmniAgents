import tempfile
from datetime import date
from pathlib import Path

ANYAGENTS_PATH = Path(__file__).parent
ANYAGENTS_REPO_PATH = ANYAGENTS_PATH.parent.parent

# Backend-specific local storage paths
LOCAL_BACKEND_PATH = Path(tempfile.gettempdir()) / "anyagents"  # LocalBackend: /tmp to avoid nested projects
DOCKER_BACKEND_PATH = ANYAGENTS_REPO_PATH / "data"  # DockerBackend: in repo for easier monitoring

# GCP staging area for bucket operations (used by storage_utils)
GCP_DATA_PATH = ANYAGENTS_REPO_PATH / "gcp_cache"