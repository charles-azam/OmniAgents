from prompttodraft.storage_utils import write_to_storage, read_from_storage
from pathlib import Path

def test_storage_utils():
    file_path = Path("test.txt")
    write_to_storage(file_path, "test")
    assert read_from_storage(file_path) == "test"
