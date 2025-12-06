"""
All of the data is stored in a bucket shared by all of the instances of the webportal crawlers.

This module contains utility functions for interacting with Google Cloud Storage.
"""

import json
import os
import uuid
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING

from dotenv import load_dotenv
from loguru import logger

from omniagents.common import GCP_DATA_PATH

if TYPE_CHECKING:
    from google.cloud import storage  # type: ignore[import-untyped]

load_dotenv()

BUCKET_ENV_VAR = "OMNIAGENTS_BUCKET_NAME"


def _initialize_and_validate_storage() -> tuple["storage.Client", "storage.Bucket"]:
    """
    Initialize storage client and validate read/write access to bucket.

    Returns:
        Tuple of (storage_client, bucket)

    Raises:
        RuntimeError: If bucket is not configured or credentials are invalid
        Exception: If read/write access validation fails
    """
    from google.cloud import storage

    if BUCKET_ENV_VAR not in os.environ:
        raise RuntimeError(f"Bucket not configured. Set {BUCKET_ENV_VAR} environment variable.")

    # # Initialize client
    # bucket_json_key = os.getenv("BUCKET_JSON_KEY")
    # if bucket_json_key:
    #     credentials_info = json.loads(s=bucket_json_key)
    #     client = storage.Client.from_service_account_info(info=credentials_info)
    # else:
    client = storage.Client()

    # Get bucket
    bucket_name = os.getenv(key=BUCKET_ENV_VAR)
    bucket = client.bucket(bucket_name=bucket_name)

    # Test read access
    list(bucket.list_blobs(max_results=1))

    # Test write access
    random_string = str(uuid.uuid4())
    random_filename = str(uuid.uuid4())
    blob = bucket.blob(blob_name=f"ping/{random_filename}.txt")
    blob.upload_from_string(data=f"ping__{random_string}")
    file_content = blob.download_as_bytes().decode(encoding="utf-8")
    assert file_content == f"ping__{random_string}", f"Content mismatch: {file_content}"
    blob.delete()

    logger.info("Storage client initialized with read/write access")
    return client, bucket


_STORAGE_CLIENT = None
_BUCKET = None


@cache
def get_bucket() -> "storage.Bucket":
    """Get the GCS bucket (lazy initialization)."""
    global _STORAGE_CLIENT, _BUCKET
    if _BUCKET is None:
        _STORAGE_CLIENT, _BUCKET = _initialize_and_validate_storage()
    return _BUCKET



def _write_to_bucket(content: str | bytes, blob_name: str) -> None:
    """Write content to bucket storage."""
    bucket = get_bucket()
    blob = bucket.blob(blob_name=blob_name)
    blob.upload_from_string(data=content)
    logger.info(f"Uploaded {blob_name} to bucket")


def write_to_storage(file_path: Path, content: str | bytes) -> None:
    """
    Write content to a file in bucket storage.

    Args:
        file_path: Path object that must be relative to GCP_DATA_PATH
        content: Content to write to the file (string or bytes)

    Raises:
        ValueError: If the path is not relative to GCP_DATA_PATH
    """
    if not file_path.is_relative_to(GCP_DATA_PATH):
        raise ValueError(f"Path {file_path} is not relative to GCP_DATA_PATH {GCP_DATA_PATH}")

    relative_path = file_path.relative_to(GCP_DATA_PATH)
    _write_to_bucket(content=content, blob_name=relative_path.as_posix())


def _read_from_bucket(blob_name: str, as_bytes: bool = False) -> str | bytes:
    """Read a file from bucket storage."""
    bucket = get_bucket()
    blob = bucket.blob(blob_name=blob_name)
    if as_bytes:
        result: bytes = blob.download_as_bytes()
        return result
    result_str: str = blob.download_as_text()
    return result_str


def read_from_storage(file_path: Path, as_bytes: bool = False) -> str | bytes:
    """
    Read a file from bucket storage.

    Args:
        file_path: Path object that must be relative to GCP_DATA_PATH
        as_bytes: If True, return bytes instead of string

    Returns:
        Content of the file as string or bytes

    Raises:
        ValueError: If the path is not relative to GCP_DATA_PATH
    """
    if not file_path.is_relative_to(GCP_DATA_PATH):
        raise ValueError(f"Path {file_path} is not relative to GCP_DATA_PATH {GCP_DATA_PATH}")

    relative_path = file_path.relative_to(GCP_DATA_PATH)
    return _read_from_bucket(blob_name=relative_path.as_posix(), as_bytes=as_bytes)


def file_exists_in_storage(file_path: Path, force_rewrite: bool = False) -> bool:
    """
    Check if a file exists in bucket storage.

    Args:
        file_path: Path object that must be relative to GCP_DATA_PATH
        force_rewrite: If True, always return False to force rewrite

    Returns:
        True if file exists, False otherwise

    Raises:
        ValueError: If the path is not relative to GCP_DATA_PATH
    """
    if force_rewrite:
        return False

    if not file_path.is_relative_to(GCP_DATA_PATH):
        raise ValueError(f"Path {file_path} is not relative to GCP_DATA_PATH {GCP_DATA_PATH}")

    bucket = get_bucket()
    relative_path = file_path.relative_to(GCP_DATA_PATH)
    blob = bucket.blob(blob_name=relative_path.as_posix())
    result: bool = blob.exists()
    return result


def delete_from_storage(file_path: Path) -> bool:
    """
    Delete a file from bucket storage.

    Args:
        file_path: Path object that must be relative to GCP_DATA_PATH

    Returns:
        True if file was deleted successfully, False if file didn't exist

    Raises:
        ValueError: If the path is not relative to GCP_DATA_PATH
    """
    if not file_path.is_relative_to(GCP_DATA_PATH):
        raise ValueError(f"Path {file_path} is not relative to GCP_DATA_PATH {GCP_DATA_PATH}")

    bucket = get_bucket()
    relative_path = file_path.relative_to(GCP_DATA_PATH)
    blob = bucket.blob(blob_name=relative_path.as_posix())

    if blob.exists():
        try:
            blob.delete()
            return True
        except Exception:
            # Ignore errors if blob already deleted (eventual consistency)
            return False
    return False


if __name__ == "__main__":
    bucket = get_bucket()
    print(f"Storage initialized: {bucket.name}")
