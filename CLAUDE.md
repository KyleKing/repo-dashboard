# Repo Dashboard - Development Guide

K9s-inspired Textual TUI for managing multiple git repositories with progressive loading, filtering, and GitHub PR integration.

## Project Overview

**Framework:** Textual (Python TUI framework)
**Theme:** Catppuccin Macchiato
**Design Philosophy:** Minimal color, single unified background, borders for hierarchy, vim-style keybindings

### Architecture

```
src/repo_dashboard/
├── __main__.py      # CLI entry point
├── app.py           # Main Textual app, UI orchestration (684 lines)
├── models.py        # Data models (RepoSummary, BranchInfo, PRInfo, etc.)
├── filters.py       # Filter and sort logic with fuzzy search
├── git_ops.py       # Git command execution
├── github_ops.py    # GitHub CLI integration
├── discovery.py     # Repository discovery
├── cache.py         # TTL-based caching
├── modals.py        # Modal screens and detail panels
├── themes.py        # Theme configuration
├── utils.py         # Utility functions
└── app.tcss         # Textual CSS styling

tests/
├── test_app.py      # App integration tests
├── test_filters.py  # Filter/sort/search tests
├── test_git_ops.py  # Git operations tests
├── test_snapshots.py # Visual regression tests
└── __snapshots__/   # SVG screenshot baselines
```

## Development Environment

### Prerequisites

- Python >=3.11
- uv (Python package manager)
- git (required for core functionality)
- gh (GitHub CLI, optional for PR features)

### Setup

```bash
# Install dependencies
uv sync

# Run the app
uv run reda

# Run with arguments
uv run reda ~/Developer --depth 2 --theme dark
```

## Testing

### Unit Tests

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run specific test file
uv run pytest tests/test_filters.py

# Run specific test
uv run pytest tests/test_filters.py::test_filter_repos_with_search_text

# Run with coverage
uv run pytest --cov=repo_dashboard --cov-report=html

# Stop on first failure
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

## Code Style

### Python Conventions

**Modern Python features:**
- Use `pathlib.Path` instead of string paths
- Use `dataclass(frozen=True)` for immutable data
- Use `StrEnum` for string enumerations
- Use walrus operator: `if (match := re.search(...)):`
- Use pattern matching where appropriate
- Use `defaultdict`, `Literal[...]` from typing

**Structure:**
- Prefix private functions with underscore: `_filter_dirty()`
- Place imports at top of file (no lazy imports)
- Only use `__all__` in `__init__.py`
- Favor composition over inheritance
- Write small, composable functions with single responsibility

**Error handling:**
- Let exceptions propagate unless you can handle meaningfully
- Use specific exception types
- Use `except Exception as err:` (not `as e:`)
- Validate at system boundaries, trust internal code

**Comments:**
- NEVER add inline comments explaining what code does
- NEVER add docstrings to private functions when self-explanatory
- Only add docstrings with args/returns/raises for public functions
- Do not repeat type info in docstrings

**Strings:**
- Use `textwrap.dedent()` for multiline strings
- Trailing backslash for first line: `dedent("""\`
- No `.strip()` needed with dedent

### Textual-Specific Patterns

**Widget composition:**
```python
def compose(self) -> ComposeResult:
    yield Breadcrumbs([])
    yield Static("", id="filter-sort-status")
    yield Input(placeholder="...", id="search-input")
    with Vertical(id="main-layout"):
        yield DataTable(id="main-table")
    yield Footer()
```

**Event handlers:**
```python
@on(DataTable.RowSelected)
def on_row_selected(self, event: DataTable.RowSelected) -> None:
    """Handle row selection"""
    row_key = str(event.row_key.value)
    # ...
```

**Actions:**
```python
def action_refresh(self) -> None:
    """Refresh all data"""
    # Action method must start with action_
```

**Bindings:**
```python
BINDINGS = [
    Binding("r", "refresh", "Refresh"),
    Binding("/", "search", "Search", show=False),
]
```

**Widget queries:**
```python
table = self.query_one(DataTable)
search_input = self.query_one("#search-input", Input)
```

**Workers for async:**
```python
self.run_worker(
    self._load_repo_summary(path),
    group="summaries",
    exclusive=False,
)
```

## Design Principles

### UI Design

**Catppuccin Macchiato Colors:**
- Base: `#24273a` (background)
- Surface0: `#363a4f` (elevated surfaces, cursor)
- Text: `#cad3f5` (primary text)
- Subtext0: `#a5adcb` (secondary text)
- Blue: `#8aadf4` (primary accent, borders)
- Mauve: `#c6a0f6` (search accent)
- Yellow: `#eed49f` (filter accent)
- Green: `#a6da95` (success, PRs)
- Peach: `#f5a97f` (dirty repos)

**Visual hierarchy:**
- Borders provide visual separation
- Color is reserved for actionable elements (badges, accents)
- Minimal color usage overall
- Single unified background
- Focus states use Surface0 for cursor

### Filtering Architecture

**Compositional filtering:**
```
FilterMode → SearchText → SortMode → Display
```

Example: "DIRTY" filter + "api" search = dirty repos containing "api"

**Filter modes (cycle with `f`):**
- ALL - Show all repositories
- DIRTY - Uncommitted changes or unpushed commits
- AHEAD - Commits ahead of tracking branch
- BEHIND - Commits behind tracking branch
- HAS_PR - Has associated GitHub PR
- HAS_STASH - Has stashed changes

**Sort modes (cycle with `s`):**
- NAME - Alphabetical by repo name
- MODIFIED - Most recently modified first
- STATUS - Dirty repos first, then by uncommitted count
- BRANCH - By branch name, then repo name

**Search (activate with `/`):**
- Fuzzy matching with 0.6 similarity threshold
- Case-insensitive substring matching
- Applied after filter mode, before sort
- Real-time updates as you type

## Key Features

### Progressive Loading

- Repo list appears immediately with placeholder data
- Workers load `RepoSummary` for each repo asynchronously
- Table updates incrementally as data becomes available
- No blocking on slow git operations

### Caching Strategy

Three caches with TTL:
- `pr_cache` - GitHub PR information (key: `{upstream}:{branch}`)
- `branch_cache` - Branch lists
- `commit_cache` - Commit information

Refresh with `r` clears all caches.

### View Hierarchy

**View 1: Repo List** (initial)
- Shows all discovered repositories
- Columns: Name, Branch, Status, PR, Modified
- Breadcrumb shows: repos count, dirty count, PRs count

**View 2: Repository Details** (drill-down with Space/Enter)
- Shows branches, stashes, worktrees
- Right panel displays details for selected item
- Loads branch PR info progressively

**View 3: Branch Details** (context panel)
- Shows commits ahead/behind
- PR information if exists
- Modified/staged/untracked files

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
  - Used for: status, branch list, commits, stashes, worktrees
  - Assumes git is in PATH

### Optional

- **gh** (GitHub CLI) - PR features require this
  - Used for: fetching PR info, check status, PR details
  - If missing: PR columns show "—" instead of failing
  - Install: `brew install gh` (macOS) or see https://cli.github.com/

## Debugging

### Textual DevTools

```bash
# Run with devtools console
uv run textual console

# In another terminal, run the app
uv run reda
```

### Logging

Textual provides built-in logging:
```python
self.log("Debug message")  # Shows in devtools console
self.notify("User message")  # Shows as notification in app
```

### Common Issues

**Focus issues:**
- Hidden widgets should be `disabled=True` to remove from focus chain
- Use `widget.focus()` to explicitly set focus

**Table updates:**
- Clear and rebuild table when filters/sort change
- Use `table.update_cell()` for single cell updates
- Use `table.refresh()` when data structure changes

**Worker race conditions:**
- Use worker groups for related tasks
- Use `exclusive=True` to cancel previous workers
- Handle worker cancellation gracefully

## Performance Considerations

- Fuzzy search runs on every keystroke (acceptable for <1000 repos)
- Progressive loading prevents blocking on initial scan
- TTL caching reduces redundant git/GitHub operations
- Workers run concurrently for parallel data loading
- Table virtualization (Textual handles this) for large lists

## Release Checklist

1. Run full test suite: `uv run pytest -v`
2. Verify snapshots are current
3. Test manually with real repositories
4. Update version in `pyproject.toml`
5. Update `README.md` if features changed
6. Run with both light and dark themes
