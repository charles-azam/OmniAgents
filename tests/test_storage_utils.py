from anyagents.common import GCP_DATA_PATH
from anyagents.storage_utils import write_to_storage, read_from_storage
from pathlib import Path

def test_storage_utils():
    file_path = GCP_DATA_PATH / "test.txt"
    write_to_storage(file_path=file_path, content="test")
    assert read_from_storage(file_path=file_path) == "test"
