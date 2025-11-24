# DVC Backend Implementation - Original Idea & Design

## The Problem

Initially, the codebase had two separate storage backends:
1. **GitStateManager**: Great for version control, but limited by GitHub file size restrictions
2. **GCSStateManager**: Handles large files well, but no version control or commit history

Users had to choose one or the other, but couldn't get both benefits simultaneously.

## The Original Idea

**Question**: How could we integrate a backend with both Git and GCS so that GCS handles the big files and Git handles the other files?

The idea was to create a **hybrid backend** that would:
- Use Git for version control of code and small files
- Use GCS for large files (CAD models, images, datasets)
- Provide a single, unified interface

## Why Not a Custom Hybrid?

Building a custom hybrid Git+GCS backend would have required:
- Custom file classification logic (which files go where?)
- Metadata manifest to track file locations
- Atomic operations across two storage systems
- Complex error handling and rollback mechanisms
- Significant maintenance overhead

**The complexity wasn't justified for the use case.**

## The DVC Solution

Instead of building a custom hybrid, we chose **DVC (Data Version Control)**:

### What is DVC?
- Open-source tool specifically designed for versioning large files with Git
- Stores large files in remote storage (GCS, S3, Azure, etc.)
- Commits only small metadata files (`.dvc` files) to Git
- Mature, battle-tested technology
- Free to use with any cloud storage

### Why DVC is Perfect for This Use Case

1. **Single mental model**: Everything is "versioned" - DVC handles the routing automatically
2. **Explicit control**: You choose what's DVC-tracked vs Git-tracked via patterns
3. **Native GCS support**: DVC has built-in GCS backend (no custom integration needed)
4. **Version control for artifacts**: CAD files are versioned alongside code
5. **Git workflow**: `git checkout` + `dvc checkout` = complete snapshot
6. **No custom code**: Leverages existing, well-maintained technology
7. **API access**: Files still stored in GCS bucket, accessible via GCS API
8. **Free**: Unlike Git LFS (which charges), DVC with GCS is free

## Use Case: CAD File Generation

The original motivation was for an agent that generates CAD files:

**Workflow:**
1. Agent generates Python code that creates CAD models
2. Python code (small) → stored in Git (version controlled)
3. CAD files (large: `.step`, `.stl`, `.obj`) → stored in GCS via DVC
4. Later: Easily retrieve CAD files from GCS to display in UI

**Example:**
```python
backend = LocalBackend(project_id="cad-generator", state_manager=DVCStateManager())
backend.start()

# Generate CAD file
backend.execute_command("python generate_cad.py")
# Creates output/model.step

# Shutdown saves:
# - Python code to Git (version controlled)
# - model.step to GCS via DVC (accessible via GCS API)
backend.shutdown()

# Later: Load snapshot
backend.start()  # Gets both Python code and CAD file
```

## Implementation Details

### DVCStateManager Architecture

```python
class DVCStateManager(StateManager):
    """Persist state using DVC (Data Version Control) + Git with GCS backend."""

    def __init__(
        self,
        repo_url: str | None = None,
        gcs_bucket: str | None = None,
        dvc_patterns: list[str] | None = None  # Which files go to DVC
    ):
        # Default patterns for large/binary files
        self.dvc_patterns = dvc_patterns or [
            "*.step", "*.stl", "*.obj",  # CAD files
            "*.png", "*.jpg", "*.mp4",   # Media
            "*.parquet", "*.csv",         # Data files
            "*.pkl", "*.h5"               # Model files
        ]
```

### How It Works

**save_snapshot():**
1. Initialize DVC if needed
2. Configure GCS remote: `gs://{bucket}/dvc-cache`
3. Find files matching `dvc_patterns` (e.g., `*.step`)
4. Add them to DVC: `dvc add output/model.step`
   - Creates `output/model.step.dvc` (tiny metadata file)
   - Uploads `model.step` to GCS
5. Stage all files: `git add .` (includes `.dvc` files)
6. Commit to Git: `git commit -m "message"`
7. Push both: `git push` + `dvc push`

**load_latest():**
1. Clone/fetch Git repo
2. Checkout branch: `git reset --hard origin/branch`
3. Pull DVC files: `dvc pull` (downloads from GCS)

**Result:**
- Git has: Python code, JSON configs, `.dvc` metadata files
- GCS has: CAD files, images, large datasets
- Single commit includes everything

## Benefits Achieved

✅ **Version control**: Full Git history for code and project evolution
✅ **Large file support**: CAD files stored in GCS via DVC
✅ **GCS API access**: Files in GCS bucket, easy to retrieve/display
✅ **Free**: No Git LFS fees, just GCS storage costs
✅ **Unified interface**: Works exactly like GitStateManager
✅ **Flexible**: Customize patterns for what goes to DVC
✅ **Mature**: Leverages battle-tested DVC technology
✅ **Simple**: No custom hybrid complexity

## Configuration

### Environment Variables
```bash
# GitHub for Git storage
PROMPTTODRAFT_GITHUB_STATE_REPO=owner/repo-name
PROMPTTODRAFT_GITHUB_API_KEY=ghp_xxxxx

# GCS for DVC remote
BUCKET_PROMPT_TO_DRAFT=your-gcs-bucket-name
```

### Custom Patterns
```python
# Only track specific files with DVC
dvc_manager = DVCStateManager(
    dvc_patterns=["*.step", "*.stl", "data/*.parquet"]
)
backend = LocalBackend(project_id="my-project", state_manager=dvc_manager)
```

### Empty Patterns (Full Git)
```python
# Don't use DVC at all, everything goes to Git
dvc_manager = DVCStateManager(dvc_patterns=[])
backend = LocalBackend(project_id="my-project", state_manager=dvc_manager)
```

## Comparison: Git vs GCS vs DVC

| Feature | GitStateManager | GCSStateManager | DVCStateManager |
|---------|----------------|-----------------|-----------------|
| **Version control** | ✅ Yes | ❌ No | ✅ Yes |
| **Large files** | ❌ Limited | ✅ Yes | ✅ Yes |
| **Cost** | Free | GCS storage | GCS storage |
| **Commit history** | ✅ Yes | ❌ No (timestamps) | ✅ Yes |
| **File size limit** | ~100MB | Unlimited | Unlimited |
| **Setup complexity** | Low | Low | Medium (Git + GCS) |
| **GCS API access** | ❌ No | ✅ Yes | ✅ Yes |
| **Best for** | Code projects | Large datasets | Code + artifacts |

## Alternative Approaches Considered

### 1. Git LFS (Git Large File Storage)
- **Pro**: Single Git interface, proven technology
- **Con**: Expensive (charges per GB), GitHub hosting required
- **Verdict**: Rejected due to cost

### 2. Custom Hybrid Git+GCS
- **Pro**: Maximum control
- **Con**: High complexity, maintenance burden, error handling
- **Verdict**: Rejected - DVC is simpler

### 3. Separate ArtifactStore
- **Pro**: Clear separation of concerns
- **Con**: Artifacts not in snapshots, separate API to manage
- **Verdict**: Valid alternative, but less integrated

### 4. Keep Separate (Status Quo)
- **Pro**: Simple, already working
- **Con**: Can't get both benefits
- **Verdict**: DVC provides better user experience

## Conclusion

**DVC was the right choice** because it:
- Solves the exact problem (version control + large files)
- Uses mature, well-tested technology
- Simpler than custom implementation
- Free with GCS backend
- Provides unified interface
- Supports the CAD generation use case perfectly

The implementation provides a clean, production-ready solution that combines the best of Git (version control) and GCS (large file storage) without the complexity of a custom hybrid backend.
