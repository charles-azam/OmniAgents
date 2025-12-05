# Test Performance Optimization Plan

## Current State
Test suite runtime: **255 seconds** (4+ minutes)

## Identified Bottlenecks

### 1. Docker Container Shutdown - ~91 seconds (36% of total time) ✅ IMPLEMENTED

**Problem**: `container.stop()` waits for graceful shutdown (default 10s timeout) before killing containers. The container runs `sleep infinity`, which doesn't respond to SIGTERM quickly, causing the full timeout wait.

**Locations**:
- `test_docker_backend_e2e`: 40.4s in shutdown
- `test_docker_backend_git_storage`: 30.4s in shutdown
- `test_docker_backend_container_reuse`: 20.2s in shutdown

**Solution Implemented (Option 1)**:
Changed `container.stop()` to `container.stop(timeout=0)` to immediately send SIGKILL instead of waiting for graceful shutdown.

```python
# Before
self._container.stop()  # Waits up to 10s for graceful shutdown

# After
self._container.stop(timeout=0)  # Immediately kills the container
```

**Files modified**:
- `src/prompttodraft/backends/docker_backend.py:116` - `DockerBackend.shutdown()` method

**Expected savings**: ~85 seconds

**Alternative approaches if needed**:
- **Option 2**: Don't remove containers, only stop them for true reuse between tests
  - Would require updating test cleanup logic
  - Faster container restart on subsequent `start()` calls
- **Option 3**: Add a `remove_container` parameter to `shutdown()` method
  - Gives control over whether to remove containers
  - Tests could pass `remove_container=False` for speed
  - Production could pass `remove_container=True` for cleanup

---

### 2. E2B Recursive Directory Listing - ~21 seconds ✅ OPTIMIZED

**Problem**: `E2BBackend.list_directory()` was calling `exists()` before every `list()` call, making double HTTP requests for each directory.

**Location**:
- `prompttodraft/backends/e2b_backend.py:186` - `E2BBackend.list_directory()`

**Current behavior was**:
```
list_directory
  ├─ exists check (HTTP call) ← REMOVED
  ├─ list directory (HTTP call)
  └─ for each subdirectory:
       └─ exists check (HTTP call) ← REMOVED
       └─ list directory (HTTP call)
```

**Solution Implemented**:
Removed unnecessary `exists()` check - now directly calls `list()` and catches exceptions if directory doesn't exist.

```python
# Before
if not self._sandbox.files.exists(path=str(sandbox_path)):
    raise FileNotFoundError(f"Directory {path} does not exist")
entries = self._sandbox.files.list(path=str(sandbox_path))

# After
try:
    entries = self._sandbox.files.list(path=str(sandbox_path))
except Exception:
    raise FileNotFoundError(f"Directory {path} does not exist")
```

**Files modified**:
- `src/prompttodraft/backends/e2b_backend.py:186-197` - `E2BBackend.list_directory()` method

**Expected savings**: ~10-15 seconds on E2B tests with deep directory structures

---

### 3. GCS Archive-Based Storage - ~12 seconds ✅ IMPLEMENTED

**Problem**: GCS was storing individual files, requiring multiple upload/download/delete operations and complex path parsing.

**Previous structure**:
```
project_id/timestamp/file1.py
project_id/timestamp/file2.py
project_id/timestamp/dir/file3.py
```

**New structure**:
```
project_id/timestamp.tar.gz  (single archive)
```

**Solution Implemented**:
Refactored `GCSStateManager` to create tar.gz archives containing all files, drastically reducing GCS operations:
- `save_snapshot`: Create tar.gz in memory, single upload instead of N uploads
- `load_latest`: Single list + single download + extract instead of list + N downloads
- `cleanup`: Delete archives instead of individual files
- `list_snapshots`: Parse archive filenames instead of complex path parsing

**Benefits**:
- Fewer GCS API calls (1 upload vs N uploads, 1 download vs N downloads)
- Simpler code (~50% reduction in state_manager.py)
- Atomic snapshots (all files or none)
- Compression saves bandwidth and storage

**Files modified**:
- `src/prompttodraft/backends/state_manager.py` - Complete refactor of GCSStateManager
- `src/prompttodraft/storage_utils.py` - Added support for bytes content
- `tests/test_backend/test_backend.py` - Updated to create test archives

**Measured savings**:
- `test_docker_backend_e2e`: 16.8s → 4.7s (~72% improvement)
- Overall test suite: 255s → 132s (~48% improvement)

---

### 4. GCS Network Calls in load_latest - ~19 seconds (SUPERSEDED BY ARCHIVES)

**Problem**: Every test that calls `start()` hits Google Cloud Storage to list and download blobs.

**Locations**:
- `test_docker_backend_e2e`: 5.8s in GCS calls
- `test_local_backend_e2e`: 6.5s in GCS calls
- `test_docker_backend_git_storage`: Not using GCS (using Git)

**Solution**:
Create a test-only in-memory state manager that doesn't hit real GCS:

```python
class InMemoryStateManager:
    def __init__(self):
        self.snapshots = {}

    def save_snapshot(self, snapshot_id, files):
        self.snapshots[snapshot_id] = files

    def load_latest(self):
        if not self.snapshots:
            return None
        latest_key = max(self.snapshots.keys())
        return self.snapshots[latest_key]

    def cleanup(self):
        self.snapshots.clear()
```

**Files to modify**:
- Create `prompttodraft/backends/test_state_manager.py`
- Update test fixtures in `tests/test_backend/test_backend.py` to use in-memory manager

**Expected savings**: ~15 seconds

---

### 4. E2B Individual Filesystem Operations - ~30 seconds

**Problem**: Each E2B filesystem operation (`exists`, `write`, `make_dir`, `get_info`) takes 2-4 seconds due to network latency.

**Locations**:
- `E2BBackend.file_exists()`: 6.3s (2 HTTP calls)
- `E2BBackend.write_file()`: Multiple 2-3s calls
- Various `Filesystem.exists()` checks: 2-4s each

**Solution**:
Batch operations where possible, or accept this as inherent cost of E2B's remote filesystem. Consider:
1. Caching file existence checks within a session
2. Reducing unnecessary `exists()` checks before operations
3. Using E2B's batch APIs if available

**Expected savings**: ~10-15 seconds

---

### 5. Git Operations in GitStateManager - ~12 seconds

**Problem**: Git commands (`git add`, `git commit`, `git checkout`) executed via backend's `execute_command()` have overhead.

**Locations**:
- `GitStateManager._ensure_git_initialized()`: 7.6s
- `GitStateManager.save_snapshot()`: 3-5s per call

**Solution**:
Use `pygit2` or `gitpython` library for direct git operations instead of shelling out to git commands.

**Expected savings**: ~5-8 seconds

---

### 6. Test Parallelization

**Current**: Tests run sequentially

**Solution**: Use `pytest-xdist` to run backend tests in parallel since they're independent:

```bash
pytest -n auto tests/test_backend/test_backend.py
```

**Expected savings**: 2-3x speedup (tests would run in ~80-120s instead of 255s)

---

## Priority Order

1. **Docker container shutdown** (immediate, easy win, 85s saved)
2. **GCS mock for tests** (moderate effort, 15s saved)
3. **Test parallelization** (easy setup, 2-3x total speedup)
4. **E2B directory listing optimization** (requires refactoring, 15-18s saved)
5. **Git library instead of shell commands** (moderate effort, 5-8s saved)
6. **E2B operation batching/caching** (complex, 10-15s saved)

## Implementation Order

### Phase 1 - Quick Wins (Target: 100s savings)
1. Fix Docker shutdown
2. Add in-memory state manager for tests
3. Enable pytest-xdist

### Phase 2 - Optimizations (Target: 30s savings)
4. Optimize E2B list_directory
5. Use git library instead of shell commands

### Phase 3 - Advanced (Target: 15s savings)
6. Add caching/batching for E2B operations

## Progress Summary

### Completed Optimizations

| Optimization | Time Saved | Status |
|--------------|------------|--------|
| Docker container shutdown (`timeout=0`) | ~85s | ✅ Done |
| GCS archive-based storage | ~12s | ✅ Done |
| E2B list_directory (remove exists check) | ~10-15s | ✅ Done |

### Current Performance

- **Original**: 255s
- **Current**: 132s (~48% faster)
- **Reduction**: 123 seconds saved

### Next Steps

1. **Enable pytest-xdist** (easy, 2-3x speedup) → Target: ~45-65s
2. **Git library instead of shell commands** (moderate, 5-8s saved)

**Updated Target: Under 60 seconds with pytest-xdist**
