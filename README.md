# Repo Dashboard

![.github/assets/demo.gif](https://raw.githubusercontent.com/kyleking/wip-reda/main/.github/assets/demo.gif)

K9s-inspired TUI for managing multiple git and jj repositories with GitHub PR integration.

## Usage

```sh
# Scan current directory
uv run reda

# Scan specific paths
uv run reda ~/Developer ~/Projects

# Scan with custom depth
uv run reda --depth 2 ~/Developer

# Use light theme
uv run reda --theme light
```

## Supported Version Control Systems

- **Git**: Full support for git repositories
- **Jujutsu (jj)**: Full support for jj repositories (both colocated and non-colocated)

The dashboard automatically detects the VCS type and uses appropriate operations. Colocated repositories (having both `.git` and `.jj`) are treated as jj repositories.

**Requirements:**
- Python >=3.11
- git CLI (if managing git repos)
- jj CLI (if managing jj repos)
- gh CLI (GitHub CLI) - optional, for PR features with both git and jj repos

## Keybindings

### Navigation
- `j`/`k` or `↓`/`↑` - Navigate up/down
- `g`/`G` - Jump to top/bottom
- `Space`/`Enter` - Select item
- `Esc` - Go back

### Actions
- `o` - Open PR in browser
- `c` - Copy (branch/PR/path)
- `f` - Filter popup (multiple filters, AND logic)
- `s` - Sort popup
- `r` - Refresh all data
- `?` - Show help
- `q` - Quit

### Batch Tasks
- `F` - Fetch all (filtered repos)
- `P` - Prune remote branches (filtered repos, git only)
- `C` - Cleanup merged branches (filtered repos)

## Status Symbols

### Repository Status
- `↑N` - N commits ahead of tracking branch
- `↓N` - N commits behind tracking branch
- `*N` - N uncommitted changes
- `$N` - N stashed changes
- `WN` - N worktrees/workspaces

### Workflow Status (GitHub Actions)
- `✓N` - N successful workflow runs
- `✗N` - N failed workflow runs
- `○N` - N skipped workflow runs
- `◷N` - N pending/in-progress workflow runs

Workflow status is displayed in the Status column for each repository and branch. Detailed workflow information (workflow names and individual run results) is shown when viewing branch details.

## Features

### Core Functionality
- **Multi-VCS Support**: Works with both git and jj repositories
- **Progressive Loading**: Data loads asynchronously as it becomes available
- **TTL Caching**: Intelligent caching for PR information, workflow status, and VCS operations
- **GitHub Integration**: Pull request info, status checks, and workflow runs via gh CLI
- **Workflow Status**: View GitHub Actions workflow status with icons (✓ success, ✗ failure, ○ skipped, ◷ pending)

### Filtering & Sorting
- **Multi-Filter Support**: Combine multiple filters with AND logic
- **Filter Modes**: all, dirty, ahead, behind, has_pr, has_stash
- **Sort Modes**: name, modified, status, branch (all reversible)
- **Fuzzy Search**: Real-time search with similarity matching

### Repository Management
- **Batch Operations**: Fetch, prune, and cleanup across filtered repositories
- **Worktree Detection**: Git worktrees and jj workspaces
- **Stash Tracking**: Git stash monitoring (jj doesn't use stashes)
- **Branch Details**: View branches, PRs, commits, workflow runs, and modified files
- **Workflow Monitoring**: Real-time GitHub Actions workflow status with detailed run information

### User Experience
- **Vim-Style Keybindings**: Familiar navigation patterns
- **Breadcrumb Navigation**: Context-aware status badges
- **Help Modal**: Complete keybinding reference
- **Catppuccin Themes**: Dark and light themes with minimal color usage

## Batch Operations

Perform maintenance tasks across multiple repositories simultaneously:

### Fetch All (`F`)
Updates remote refs for all filtered repositories.
- **Git**: `git fetch --all --prune`
- **JJ**: `jj git fetch --all-remotes`

### Prune Remote (`P`)
Cleans up stale remote branch references.
- **Git**: `git remote prune origin`
- **JJ**: No-op (jj handles this automatically during fetch)

### Cleanup Merged Branches (`C`)
Deletes local branches/bookmarks that have been merged into main/master.
- **Git**: Deletes local branches merged into main
- **JJ**: Deletes bookmarks that are ancestors of main

**Usage:**
1. Apply filters to select repositories (e.g., filter by "dirty" or search for specific repos)
2. Press `F`, `P`, or `C` to run the batch operation
3. View real-time progress and results in the modal
4. Operations run sequentially across all filtered repositories

**Safety:**
- Batch operations only work in the repository list view
- Only operate on currently filtered/visible repositories
- Each operation shows success/failure status with detailed messages
- Failed operations don't stop the batch (continues to next repo)

## Development

### Running Tests

Run all tests:
```sh
uv run pytest
```

Run with verbose output:
```sh
uv run pytest -v
```

Run specific test file:
```sh
uv run pytest tests/test_app.py
```

### Visual Snapshot Testing

This project uses [pytest-textual-snapshot](https://github.com/Textualize/pytest-textual-snapshot) for visual regression testing. Snapshot tests capture SVG screenshots of the TUI and detect visual changes.

**View existing snapshots:**
```sh
ls tests/__snapshots__/
```

**Run snapshot tests:**
```sh
uv run pytest tests/test_snapshots.py
```

**Update snapshots after intentional UI changes:**
```sh
uv run pytest tests/test_snapshots.py --snapshot-update
```

**How it works:**
- First run generates baseline SVG screenshots stored in `tests/__snapshots__/`
- Subsequent runs compare new screenshots against baselines
- Tests fail if screenshots differ (indicating unintended visual changes)
- Use `--snapshot-update` to accept new visuals as the new baseline

**When to update snapshots:**
- After intentionally changing UI layout, styling, or colors
- After updating Textual version (may change rendering)
- When adding new snapshot tests

**Common workflows:**
```sh
# Make UI changes
# Run tests to see if snapshots differ
uv run pytest tests/test_snapshots.py

# Review the diff (pytest shows what changed)
# If changes are intentional, update snapshots
uv run pytest tests/test_snapshots.py --snapshot-update

# Commit updated snapshots with your changes
git add tests/__snapshots__/
```

### Recording the Demo

Generate demo GIF using VHS:

```sh
vhs < .github/assets/demo.tape
```

See [CONTRIBUTING.md](./CONTRIBUTING.md) for more details on VHS setup and recording.
