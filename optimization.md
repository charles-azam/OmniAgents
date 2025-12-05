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

### 2. E2B Recursive Directory Listing - ~21 seconds

**Problem**: `GCSStateManager.save_snapshot()` calls `list_directory()` recursively, making individual HTTP requests for each subdirectory and file existence check.

**Location**:
- `prompttodraft/backends/state_manager.py:87` - `GCSStateManager.save_snapshot()`
- `prompttodraft/backends/e2b_backend.py:186` - `E2BBackend.list_directory()`

**Current behavior**:
```
list_directory (HTTP call)
  └─ for each item:
       ├─ exists check (HTTP call)
       └─ if directory: list_directory (recursive HTTP call)
```

**Solution**:
Batch operations or use a single recursive filesystem walk API if E2B supports it. Alternatively, cache directory structure during the walk.

**Expected savings**: ~15-18 seconds

---

### 3. GCS Network Calls in load_latest - ~19 seconds

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

## Expected Final Runtime

- Current: 255s
- After Phase 1: ~50-80s (with parallelization)
- After Phase 2: ~35-60s
- After Phase 3: ~25-50s

**Target: Under 60 seconds for full test suite**
