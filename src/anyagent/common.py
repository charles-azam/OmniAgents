import tempfile
from datetime import date
from pathlib import Path

ANYAGENT_PATH = Path(__file__).parent
ANYAGENT_REPO_PATH = ANYAGENT_PATH.parent.parent

# Backend-specific local storage paths
LOCAL_BACKEND_PATH = Path(tempfile.gettempdir()) / "anyagent"  # LocalBackend: /tmp to avoid nested projects
DOCKER_BACKEND_PATH = ANYAGENT_REPO_PATH / "data"  # DockerBackend: in repo for easier monitoring

# GCP staging area for bucket operations (used by storage_utils)
GCP_DATA_PATH = ANYAGENT_REPO_PATH / "gcp_cache"