import tempfile
from datetime import date
from pathlib import Path

PROMPT_TO_DRAFT_PATH = Path(__file__).parent
PROMPT_TO_DRAFT_REPO_PATH = PROMPT_TO_DRAFT_PATH.parent.parent
assert (PROMPT_TO_DRAFT_REPO_PATH/"playground").exists(), "Playground directory does not exist"

# Use temp directory to avoid nested projects interfering with parent repository
DATA_PATH = Path(tempfile.gettempdir()) / "prompttodraft"