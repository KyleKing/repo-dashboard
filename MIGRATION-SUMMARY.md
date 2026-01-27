# Python to Go Migration Summary

This document summarizes the migration from the Python (Textual) implementation to the Go (Bubble Tea) implementation.

## Overview

| Aspect | Python | Go |
|--------|--------|-----|
| Framework | Textual 0.47+ | Bubble Tea 1.2.4 |
| Language | Python 3.11+ | Go 1.23 |
| Entry Point | `reda` (pyproject.toml script) | `gh-repo-dashboard/main.go` |
| Styling | Textual CSS (app.tcss) | Lipgloss |

## Feature Parity

### Core Features (100% Equivalent)

| Feature | Status |
|---------|--------|
| Repository discovery | Equivalent |
| VCS abstraction (Git/JJ) | Equivalent |
| Filter system (DIRTY, AHEAD, BEHIND, HAS_PR, HAS_STASH) | Equivalent |
| Sort system (NAME, MODIFIED, STATUS, BRANCH) | Equivalent |
| GitHub PR integration | Equivalent |
| Batch tasks (fetch, prune, cleanup) | Equivalent |
| TTL caching | Equivalent |
| Progressive loading | Equivalent |

### Go Enhancements

| Feature | Description |
|---------|-------------|
| Multi-sort support | Go supports multi-field sorting with priority and direction (ASC/DESC) |
| Generics cache | Type-safe cache with `[T any]` generics |
| Explicit ConflictedCount | Tracks conflicted files separately in VCS operations |
| Enhanced PRInfo | Additional fields: IsDraft, Mergeable, ReviewDecision, ApprovedBy, ChangesRequests |
| MockVCS | Built-in mock type for testing |
| PR List operations | GetPRsForRepo, GetPRCount for comprehensive PR handling |

### Python-Only Features (Not Migrated)

| Feature | Reason |
|---------|--------|
| Async/await patterns | Go uses synchronous operations with context.Context |
| pytest-textual-snapshot | Go golden file tests use teatest (documented in test-improvements.md) |
| Protocol type hints | Go uses interfaces instead |
| Frozen dataclasses | Go uses value structs (immutable by convention) |
| Breadcrumb widget | Different UI approach in Bubble Tea |
| Worker groups | Go uses goroutines with different concurrency model |

## Architecture Mapping

### Python → Go File Mapping

| Python | Go |
|--------|-----|
| models.py | internal/models/*.go |
| vcs_protocol.py | internal/vcs/operations.go |
| vcs_git.py | internal/vcs/git.go |
| vcs_jj.py | internal/vcs/jj.go |
| vcs_factory.py | internal/vcs/factory.go |
| filters.py | internal/filters/*.go |
| discovery.py | internal/discovery/discovery.go |
| batch_tasks.py | internal/batch/*.go |
| cache.py | internal/cache/ttl.go |
| github_ops.py | internal/github/*.go |
| app.py | internal/app/app.go, update.go, view.go |
| modals.py | internal/app/view.go (integrated) |
| themes.py | internal/ui/styles/styles.go |

### Test Mapping

| Python | Go |
|--------|-----|
| test_filters.py | internal/filters/*_test.go |
| test_vcs_factory.py | internal/vcs/factory_test.go |
| test_git_ops.py | internal/vcs/git_test.go |
| test_vcs_jj.py | internal/vcs/jj_test.go |
| test_github_ops.py | internal/github/pr_test.go |
| test_batch_tasks.py | internal/batch/batch_test.go |
| test_app.py | internal/app/app_test.go |
| test_snapshots.py | See test-improvements.md for golden file testing |

## VCS Concept Mapping

| Concept | Git | JJ (Jujutsu) |
|---------|-----|--------------|
| Current location | HEAD | @ (working copy) |
| Branch | branch | bookmark |
| Remote tracking | upstream branch | tracking bookmark |
| Uncommitted changes | unstaged + staged | working copy |
| Stash | stash | N/A (use changes) |
| Worktree | worktree | workspace |

## Go Project Structure

```
gh-repo-dashboard/
├── main.go                    # CLI entry point
├── go.mod / go.sum           # Dependencies
├── internal/
│   ├── app/                  # Bubble Tea app
│   │   ├── app.go           # Model definition
│   │   ├── update.go        # Update function (message handling)
│   │   ├── view.go          # View rendering
│   │   ├── keymap.go        # Key bindings
│   │   ├── commands.go      # Tea commands
│   │   └── messages.go      # Message types
│   ├── models/               # Data structures
│   │   ├── repo.go          # RepoSummary, WorktreeInfo
│   │   ├── branch.go        # BranchInfo
│   │   ├── pr.go            # PRInfo, PRDetail, WorkflowSummary
│   │   ├── filter.go        # ActiveFilter, ActiveSort
│   │   └── enums.go         # FilterMode, SortMode, etc.
│   ├── vcs/                  # VCS abstraction
│   │   ├── operations.go    # VCSOperations interface
│   │   ├── git.go           # Git implementation
│   │   ├── jj.go            # JJ implementation
│   │   ├── factory.go       # Detection and factory
│   │   └── mock.go          # Test mock
│   ├── filters/              # Filter/sort logic
│   │   ├── filter.go        # FilterRepos, FilterReposMulti
│   │   ├── sort.go          # SortPaths, SortPathsMulti
│   │   └── search.go        # Fuzzy search
│   ├── discovery/            # Repo discovery
│   │   └── discovery.go     # DiscoverRepos
│   ├── batch/                # Batch operations
│   │   ├── runner.go        # Task runner
│   │   └── tasks.go         # Task definitions
│   ├── github/               # GitHub integration
│   │   ├── pr.go            # PR operations
│   │   └── workflow.go      # Workflow runs
│   ├── cache/                # Caching
│   │   └── ttl.go           # Generic TTL cache
│   └── ui/styles/            # Styling
│       └── styles.go        # Lipgloss styles
└── test-improvements.md      # Testing patterns documentation
```

## Testing Improvements

The Go implementation includes documentation for three testing approaches:

1. **teatest (Golden File)** - Visual regression testing with snapshot comparison
2. **catwalk (Data-Driven)** - Complex interaction sequence testing
3. **Direct Testing** - State transition and business logic testing

See `gh-repo-dashboard/test-improvements.md` for detailed examples and patterns.

## Running the Go Implementation

```bash
cd gh-repo-dashboard
go build -o gh-repo-dashboard .
./gh-repo-dashboard ~/Developer --depth 2
```

Or as a GitHub CLI extension:
```bash
gh extension install .
gh repo-dashboard ~/Developer
```

## Key Differences from Python

1. **Concurrency Model**: Go uses goroutines with context.Context instead of Python's async/await
2. **Type System**: Go interfaces vs Python Protocols; Go generics vs Python type hints
3. **Error Handling**: Go's explicit error returns vs Python's exceptions
4. **UI Framework**: Bubble Tea's Elm-like architecture vs Textual's widget composition
5. **Styling**: Lipgloss inline styling vs Textual CSS files

## Deleted Python Files

### Source Files (src/repo_dashboard/)
- `__init__.py`, `__main__.py`
- `app.py`, `app.tcss`
- `models.py`, `filters.py`, `cache.py`
- `vcs_protocol.py`, `vcs_git.py`, `vcs_jj.py`, `vcs_factory.py`
- `git_ops.py`, `github_ops.py`
- `discovery.py`, `batch_tasks.py`
- `modals.py`, `themes.py`, `utils.py`

### Test Files (tests/)
- `__init__.py`
- `test_app.py`, `test_filters.py`, `test_modals.py`
- `test_git_ops.py`, `test_git_ops_async.py`
- `test_vcs_factory.py`, `test_vcs_jj.py`
- `test_github_ops.py`, `test_batch_tasks.py`
- `test_models_status.py`, `test_snapshots.py`
- `__snapshots__/` (visual regression baselines)

### Configuration Files
- `pyproject.toml`
- `uv.lock`
- `.venv/` (virtual environment)
