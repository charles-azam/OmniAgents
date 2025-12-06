import tempfile
from datetime import date
from pathlib import Path

OMNIAGENTS_PATH = Path(__file__).parent
OMNIAGENTS_REPO_PATH = OMNIAGENTS_PATH.parent.parent

# Backend-specific local storage paths
LOCAL_BACKEND_PATH = Path(tempfile.gettempdir()) / "omniagents"  # LocalBackend: /tmp to avoid nested projects
DOCKER_BACKEND_PATH = OMNIAGENTS_REPO_PATH / "data"  # DockerBackend: in repo for easier monitoring

# GCP staging area for bucket operations (used by storage_utils)
GCP_DATA_PATH = OMNIAGENTS_REPO_PATH / "gcp_cache"