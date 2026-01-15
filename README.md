# Multi-Repo View

K9s-inspired TUI for managing multiple git repositories.

## Usage

```sh
# Scan current directory
uv run multi-repo-view

# Scan specific paths
uv run multi-repo-view ~/Developer ~/Projects

# Scan with custom depth
uv run multi-repo-view --depth 2 ~/Developer

# Use light theme
uv run multi-repo-view --theme light
```

## Keybindings

### Navigation
- `j`/`k` or `↓`/`↑` - Navigate up/down
- `g`/`G` - Jump to top/bottom
- `Space`/`Enter` - Select item
- `Esc` - Go back

### Actions
- `o` - Open PR in browser
- `c` - Copy (branch/PR/path)
- `f` - Cycle filter mode
- `s` - Cycle sort mode
- `r` - Refresh all data
- `?` - Show help
- `q` - Quit

## Features

- Progressive loading - data loads as it becomes available
- TTL caching for PR information and git operations
- Filter modes: all/dirty/ahead/behind/has_pr/has_stash
- Sort modes: name/modified/status/branch
- Git worktree detection
- Stash tracking
- Breadcrumb navigation with status badges
- Vim-style keybindings
- Help modal with all keybindings
- Catppuccin themes (dark/light)

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
