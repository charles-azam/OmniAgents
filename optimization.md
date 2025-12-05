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

### 5. Git Operations in GitStateManager - ~12 seconds ✅ OPTIMIZED

**Problem**: Git commands executed via `backend.execute_command()` had overhead from multiple separate shell invocations, especially on remote backends like E2B.

**Locations**:
- `GitStateManager._ensure_git_initialized()`: 7.6s (E2B), 2.5s (Docker)
- `GitStateManager.save_snapshot()`: 3-5s per call

**Solution Implemented**:
Combined multiple git commands into single shell invocations using `&&` operators, reducing the number of remote command executions:

**Before** (_ensure_git_initialized):
```python
backend.execute_command("git init")                    # Command 1
backend.execute_command("git remote add origin ...")   # Command 2
backend.execute_command('git config user.name ...')    # Command 3
backend.execute_command('git config user.email ...')   # Command 4
# Then 3-5 more commands for branch checking/checkout
```

**After**:
```python
backend.execute_command("git init && git remote add origin ... && git config user.name ... && git config user.email ...")  # Single command
# Reduced branch operations from 5 to 3 commands
```

**Before** (save_snapshot):
```python
backend.execute_command("git add .")               # Command 1
backend.execute_command("git status --porcelain")  # Command 2
backend.execute_command("git commit -m '...'")     # Command 3
backend.execute_command("git push ...")            # Command 4
backend.execute_command("git rev-parse HEAD")      # Command 5
```

**After**:
```python
backend.execute_command("git add . && git diff-index --quiet HEAD || git commit -m '...'")  # Combined
backend.execute_command("git rev-parse HEAD")  # Get SHA
backend.execute_command("git push ...")        # Push only if committed
# 5 commands → 3 commands
```

**Files modified**:
- `src/prompttodraft/backends/state_manager.py:272-321` - `_ensure_git_initialized()`
- `src/prompttodraft/backends/state_manager.py:323-362` - `save_snapshot()`

**Expected savings**: ~3-5 seconds on git-based tests, especially E2B

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
| Git command batching | ~3-5s | ✅ Done |

### Current Performance

- **Original**: 255s
- **Current**: ~125-130s (~50% faster)
- **Reduction**: ~125-130 seconds saved

### Next Steps

1. **Enable pytest-xdist** (easy, 2-3x speedup) → Target: ~42-65s total runtime

**Updated Target: Under 60 seconds with pytest-xdist**

---

## Summary

We've achieved a **50% reduction in test time** through:
1. Eliminating Docker graceful shutdown delays
2. Using tar.gz archives for GCS instead of individual files
3. Removing redundant HTTP calls in E2B directory listing
4. Batching git commands to reduce shell execution overhead

The test suite now runs in approximately **130 seconds** instead of 255 seconds, with all tests passing. Further speedup is available through test parallelization with pytest-xdist.

---

## Phase 2 Optimizations (New Run: 74.3s)

After Phase 1 optimizations brought tests from 255s → 130s, new profiling revealed additional bottlenecks:

### 7. GitHub API Client Caching ✅ IMPLEMENTED

**Problem**: Each `cleanup()` and `list_snapshots()` call was creating a new GitHub client and fetching repo metadata:
```
GitStateManager.cleanup: 2.3-2.7s
  ├─ Github(auth=...) + get_repo: ~0.8s
  └─ Repository.get_git_ref: ~1.0s

GitStateManager.list_snapshots: 2.3-3.2s
  ├─ Github(auth=...) + get_repo: ~0.8s
  └─ Repository.get_branch: ~1.0s
```

**Solution Implemented**:
Added `_get_github_client()` method to cache the GitHub client and repo object across multiple calls:

```python
def _get_github_client(self) -> tuple:
    """Get cached GitHub client and repo."""
    if not hasattr(self, '_github_client'):
        from github import Github, Auth
        self._github_client = Github(auth=Auth.Token(token=self.github_token))
        self._github_repo = self._github_client.get_repo(full_name_or_id=self.repo_path)
    return self._github_client, self._github_repo
```

**Files modified**:
- `src/prompttodraft/backends/state_manager.py:389-395` - Added `_get_github_client()` method
- `src/prompttodraft/backends/state_manager.py:397-407` - Updated `cleanup()` to use cached client
- `src/prompttodraft/backends/state_manager.py:417-427` - Updated `list_snapshots()` to use cached client

**Expected savings**: ~5-8 seconds (multiple API initialization calls eliminated)

---

### 8. Lazy Import for google.cloud.storage ✅ IMPLEMENTED

**Problem**: `google.cloud.storage` was imported at module load time, taking:
```
<module> prompttodraft/storage_utils.py: 2.091s
  └─ <module> google/cloud/storage: 1.159s
     └─ packages_distributions: 1.070s
```

This happened even for tests not using GCS storage (like Git-based tests).

**Solution Implemented**:
Made the storage initialization lazy - only imports and initializes when `get_bucket()` is first called:

```python
# Before: Eager initialization at module load
from google.cloud import storage
STORAGE_CLIENT, BUCKET = _initialize_and_validate_storage()

# After: Lazy initialization on first use
if TYPE_CHECKING:
    from google.cloud import storage

_STORAGE_CLIENT = None
_BUCKET = None

@cache
def get_bucket() -> "storage.Bucket":
    """Get the GCS bucket (lazy initialization)."""
    global _STORAGE_CLIENT, _BUCKET
    if _BUCKET is None:
        _STORAGE_CLIENT, _BUCKET = _initialize_and_validate_storage()
    return _BUCKET
```

**Files modified**:
- `src/prompttodraft/storage_utils.py:12-20` - Added TYPE_CHECKING import
- `src/prompttodraft/storage_utils.py:27-38` - Moved import inside function
- `src/prompttodraft/storage_utils.py:71-81` - Changed to lazy initialization
- `src/prompttodraft/storage_utils.py:198` - Fixed __main__ block

**Expected savings**: ~1.5-2 seconds for tests not using GCS (Git-based tests)

---

### Remaining Bottlenecks (Addressable)

### 9. Git Subprocess Operations (~15-20s)

**Problem**: Multiple git commands via `execute_command()` still take significant time:
```
GitStateManager.save_snapshot: 1.3-3.2s per call
  └─ execute_command (git add/commit/push): 1.3-3.2s
GitStateManager._ensure_git_initialized: 1.4-2.3s per call
  └─ execute_command (git init/config/fetch): 1.4-2.3s
```

**Potential Solutions**:
- **Option A**: Use GitPython library instead of subprocess
- **Option B**: Mock git operations in tests (fastest for tests)
- **Option C**: Further batch operations (limited gains at this point)

**Expected savings**: ~8-12 seconds

---

### 10. Subprocess Communication Overhead (~10-15s)

**Problem**: Multiple `subprocess.communicate()` calls with `poll.poll` waits:
```
LocalBackend.execute_command: 1.3-3.2s per call
  └─ Popen.communicate → PollSelector.select → poll.poll
```

**Analysis**: This is mostly unavoidable overhead for running actual git commands. The only way to eliminate this is:
1. Use in-process libraries (GitPython, etc.)
2. Mock subprocess calls in tests
3. Accept as inherent cost

---

### Summary - Phase 2

**Current Performance**: 74.3s (255s → 130s → 74.3s)
**Improvements Implemented**:
- GitHub API client caching (~5-8s)
- Lazy google.cloud.storage import (~1.5-2s)

**Total Savings from All Optimizations**: ~180+ seconds (~71% reduction)

**Remaining Optimization Opportunities**:
1. Use GitPython instead of subprocess (~8-12s potential savings)
2. Test parallelization with pytest-xdist (2-3x speedup → ~25-37s total)
3. Mock git operations in tests (fastest, but less realistic)

**Next Recommended Action**: Enable pytest-xdist for parallel test execution to achieve **target runtime under 30 seconds**.
