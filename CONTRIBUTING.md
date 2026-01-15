# Contributing to Multi-Repo View

## Development Setup

### Prerequisites

- Python >=3.11
- uv (Python package manager)
- git (required for core functionality)
- gh (GitHub CLI, optional for PR features)

### Installation

```bash
# Install dependencies
uv sync

# Run the app
uv run multi-repo-view
```

## Testing

### Unit Tests

Run all tests:
```bash
uv run pytest
```

Run with verbose output:
```bash
uv run pytest -v
```

Run specific test file:
```bash
uv run pytest tests/test_filters.py
```

Run with coverage:
```bash
uv run pytest --cov=multi_repo_view --cov-report=html
```

Stop on first failure:
```bash
uv run pytest -x
```

### Visual Snapshot Tests

Uses pytest-textual-snapshot for visual regression testing.

```bash
# Run snapshot tests
uv run pytest tests/test_snapshots.py

# Update snapshots after UI changes
uv run pytest tests/test_snapshots.py --snapshot-update

# View snapshots
ls tests/__snapshots__/
```

**When to update snapshots:**
- After intentional UI changes (new widgets, layout changes, styling)
- After updating Textual version
- When snapshot tests fail due to expected changes

**Workflow:**
1. Make UI changes
2. Run `uv run pytest tests/test_snapshots.py` - tests will fail
3. Review the diff in `snapshot_report.html`
4. If changes are correct: `uv run pytest tests/test_snapshots.py --snapshot-update`
5. Commit updated snapshots: `git add tests/__snapshots__/`

## Recording Demo

Generate demo GIF using VHS:

```bash
# Install VHS (if not already installed)
# macOS:
brew install vhs

# Other platforms:
# https://github.com/charmbracelet/vhs#installation

# Record the demo
vhs < .github/assets/demo.tape
```

The demo will be saved as `.github/assets/demo.gif`.

**Editing the demo:**
1. Edit `.github/assets/demo.tape` to change the recording script
2. Run `vhs < .github/assets/demo.tape` to regenerate
3. Commit both the tape file and generated GIF

**VHS tips:**
- Use `Set PlaybackSpeed` to control animation speed
- Use `Sleep` between actions to let UI settle
- Use `Hide`/`Show` to hide setup commands
- Use Catppuccin Macchiato theme to match app theme

## Code Style

See [CLAUDE.md](./CLAUDE.md) for detailed code style guidelines.

**Key principles:**
- Functional style with small, composable functions
- Modern Python: pathlib, dataclasses, pattern matching, walrus operator
- Prefix private functions with underscore
- Let exceptions propagate unless you can handle meaningfully
- No inline comments explaining what code does
- Only add docstrings to public functions

## Architecture

See [CLAUDE.md](./CLAUDE.md) for detailed architecture documentation.

**Key components:**
- `app.py` - Main Textual app, UI orchestration
- `models.py` - Data models (RepoSummary, BranchInfo, PRInfo)
- `filters.py` - Filter and sort logic with fuzzy search
- `git_ops.py` - Git command execution
- `github_ops.py` - GitHub CLI integration
- `discovery.py` - Repository discovery
- `cache.py` - TTL-based caching
- `modals.py` - Modal screens and detail panels

## Common Tasks

### Adding a new filter mode

1. Add enum value to `FilterMode` in `models.py`
2. Add filter function in `filters.py` (e.g., `_filter_xyz()`)
3. Add case to `filter_repos()` in `filters.py`
4. Add tests in `tests/test_filters.py`

### Adding a new keybinding

1. Add `Binding` to `BINDINGS` list in `app.py`
2. Implement `action_<name>()` method
3. Update help text in `modals.py`
4. Add test in `tests/test_app.py`

### Adding a new modal/screen

1. Create modal class inheriting `ModalScreen` in `modals.py`
2. Define `compose()` method with widgets
3. Add CSS styling to `app.tcss`
4. Use `self.push_screen(YourModal())` to show

### Modifying UI layout

1. Make changes to `compose()`, CSS, or widget code
2. Run `uv run pytest tests/test_snapshots.py` - will fail
3. Review visual diff in `snapshot_report.html`
4. If correct: `uv run pytest tests/test_snapshots.py --snapshot-update`
5. Commit updated snapshots

## External Dependencies

### Required

- **git** - Core functionality depends on git CLI

### Optional

- **gh** (GitHub CLI) - PR features require this
  - Install: `brew install gh` (macOS) or see https://cli.github.com/

## Debugging

### Textual DevTools

```bash
# Run with devtools console
uv run textual console

# In another terminal, run the app
uv run multi-repo-view
```

### Logging

Textual provides built-in logging:
```python
self.log("Debug message")  # Shows in devtools console
self.notify("User message")  # Shows as notification in app
```

## Performance Considerations

- Fuzzy search runs on every keystroke (acceptable for <1000 repos)
- Progressive loading prevents blocking on initial scan
- TTL caching reduces redundant git/GitHub operations
- Workers run concurrently for parallel data loading
- Table virtualization (Textual handles this) for large lists
