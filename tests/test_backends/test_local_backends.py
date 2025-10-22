def test_local_backend() -> None:
    """Test the local backend."""
    backend = LocalBackend()
    assert backend is not None