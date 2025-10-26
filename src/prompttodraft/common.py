import tempfile
from datetime import date
from pathlib import Path

PROMPT_TO_DRAFT_PATH = Path(__file__).parent
PROMPT_TO_DRAFT_REPO_PATH = PROMPT_TO_DRAFT_PATH.parent.parent
assert (PROMPT_TO_DRAFT_REPO_PATH/"playground").exists(), "Playground directory does not exist"

# Backend-specific local storage paths
LOCAL_BACKEND_PATH = Path(tempfile.gettempdir()) / "prompttodraft"  # LocalBackend: /tmp to avoid nested projects
DOCKER_BACKEND_PATH = PROMPT_TO_DRAFT_REPO_PATH / "data"  # DockerBackend: in repo for easier monitoring

# GCP staging area for bucket operations (used by storage_utils)
GCP_DATA_PATH = PROMPT_TO_DRAFT_REPO_PATH / "gcp_cache"