# Repo Dashboard - Development Guide

K9s-inspired Textual TUI for managing multiple git and jj repositories with progressive loading, filtering, GitHub PR integration, and batch maintenance tasks.

## Project Overview

**Positioning:** Multi-repository TUI focusing on multi-VCS support (Git + Jujutsu), GitHub PR integration, and batch maintenance operations. Most similar to [Git-Scope](https://github.com/Bharath-code/git-scope), but differentiated by:
- Multi-VCS support (Git + Jujutsu vs Git-only)
- GitHub PR integration with detailed status checks
- Batch operations (fetch, prune, cleanup merged branches)
- Worktree/workspace and stash management
- Built with Textual (Python) vs Bubble Tea (Go)

**Trade-offs:**
- Slower startup (~100-500ms vs ~10ms for Git-Scope) due to Python vs Go
- More features but higher complexity
- Broader VCS support but more maintenance surface

**Framework:** Textual (Python TUI framework)
**Theme:** Catppuccin Macchiato
**Design Philosophy:** Minimal color, single unified background, borders for hierarchy, vim-style keybindings

### Architecture

```
src/repo_dashboard/
├── __main__.py      # CLI entry point
├── app.py           # Main Textual app, UI orchestration
├── models.py        # Data models (RepoSummary, BranchInfo, PRInfo, etc.)
├── filters.py       # Filter and sort logic with fuzzy search
├── vcs_protocol.py  # VCS abstraction protocol
├── vcs_git.py       # Git implementation
├── vcs_jj.py        # Jujutsu (jj) implementation
├── vcs_factory.py   # VCS detection and factory
├── batch_tasks.py   # Batch operations across repos
├── git_ops.py       # Legacy git operations (being phased out)
├── github_ops.py    # GitHub CLI integration
├── discovery.py     # Repository discovery
├── cache.py         # TTL-based caching
├── modals.py        # Modal screens and detail panels
├── themes.py        # Theme configuration
├── utils.py         # Utility functions
└── app.tcss         # Textual CSS styling

tests/
├── test_app.py         # App integration tests
├── test_filters.py     # Filter/sort/search tests
├── test_vcs_factory.py # VCS detection and factory tests
├── test_vcs_jj.py      # JJ operations tests
├── test_git_ops.py     # Git operations tests
├── test_github_ops.py  # GitHub integration tests
├── test_batch_tasks.py # Batch task runner tests
├── test_modals.py      # Modal component tests
├── test_snapshots.py   # Visual regression tests
└── __snapshots__/      # SVG screenshot baselines
```

## Development Environment

### Prerequisites

- Python >=3.11
- uv (Python package manager)
- git CLI (if managing git repos)
- jj CLI (if managing jj repos)
- gh (GitHub CLI, optional for PR features with both git and jj)

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

## VCS Support

The dashboard uses a protocol-based abstraction to support multiple version control systems.

### Architecture

**VCS Protocol Pattern:**
- `VCSOperations` protocol defines the interface for both read and write operations
- `GitOperations` and `JJOperations` implement the protocol
- `detect_vcs_type()` auto-detects VCS by directory presence (`.git` or `.jj`)
- `get_vcs_operations()` factory returns the appropriate implementation
- Colocated repos (both `.git` and `.jj`) prefer jj

**Key Files:**
- `vcs_protocol.py` - Protocol defining VCS operations interface
- `vcs_git.py` - Git implementation with full protocol support
- `vcs_jj.py` - Jujutsu implementation with full protocol support
- `vcs_factory.py` - VCS detection and factory function
- `batch_tasks.py` - Batch operations using VCS abstraction

### Git vs JJ Concept Mapping

| Concept | Git | JJ (Jujutsu) | Notes |
|---------|-----|--------------|-------|
| Current location | HEAD | @ (working copy) | jj always has a working copy change |
| Branch | branch | bookmark | jj bookmarks are similar to git branches |
| Staged changes | index/staging | N/A | jj automatically tracks all changes |
| Uncommitted | unstaged + staged | working copy | Different mental model |
| Commits ahead/behind | ahead/behind | ahead/behind | Similar concept |
| Remote tracking | upstream branch | tracking bookmark | Similar |
| Stash | stash | N/A | jj doesn't need stashing (can create changes) |
| Worktree | worktree | workspace | Similar but jj workspaces are more powerful |

### VCS Operations

**Read Operations (existing):**
- `get_repo_summary_async()` - Get repository status and metadata
- `get_current_branch_async()` - Get current branch/bookmark name
- `get_branch_list_async()` - List all branches/bookmarks
- `get_stash_list()` - List stashes (git only, jj returns empty)
- `get_worktree_list()` - List worktrees/workspaces
- `get_commit_log()` - Get commit/change history

**Write Operations (batch tasks):**
- `fetch_all()` - Fetch from all remotes
  - Git: `git fetch --all --prune`
  - JJ: `jj git fetch --all-remotes`
- `prune_remote()` - Prune stale remote branches
  - Git: `git remote prune origin`
  - JJ: No-op (jj handles this automatically)
- `cleanup_merged_branches()` - Delete merged local branches/bookmarks
  - Git: Deletes local branches merged into main
  - JJ: Deletes bookmarks that are ancestors of main

All write operations return `(success: bool, message: str)` for UI feedback.

### GitHub CLI Integration

GitHub integration works for both git and jj repositories via the `gh` CLI:

- For git repos: Uses standard git directory
- For jj repos (non-colocated): Sets `GIT_DIR` environment variable to `.jj/repo/store/git`
- For jj repos (colocated): Uses `.git` directory like standard git repos

The `get_github_env()` helper in `vcs_factory.py` handles this transparently.

## Batch Tasks

Batch operations execute maintenance tasks across multiple repositories simultaneously.

### Architecture

**BatchTaskRunner:**
- Runs async tasks sequentially across filtered repositories
- Uses VCS factory to get appropriate operations for each repo
- Tracks progress and duration for each operation
- Handles errors gracefully (continues on failure)

**BatchTaskModal:**
- Real-time progress bar showing completion
- Results table with columns: Repository, Status, Message, Time
- Color-coded status icons (✓ green for success, ✗ red for failure)
- Scrollable results for large repository sets

### Adding a New Batch Task

1. Add async method to `VCSOperations` protocol (vcs_protocol.py)
   ```python
   async def new_operation(self, repo_path: Path) -> tuple[bool, str]:
       """Description of operation"""
       ...
   ```

2. Implement in both `GitOperations` and `JJOperations`
   ```python
   # vcs_git.py
   async def new_operation(self, repo_path: Path) -> tuple[bool, str]:
       # Git-specific implementation
       ...

   # vcs_jj.py
   async def new_operation(self, repo_path: Path) -> tuple[bool, str]:
       # JJ-specific implementation
       ...
   ```

3. Create task function in `batch_tasks.py`
   ```python
   async def task_new_operation(
       vcs_ops: VCSOperations, repo_path: Path
   ) -> tuple[bool, str]:
       return await vcs_ops.new_operation(repo_path)
   ```

4. Add action method to `app.py`
   ```python
   def action_batch_new_operation(self) -> None:
       from repo_dashboard.batch_tasks import task_new_operation
       from repo_dashboard.filters import filter_repos_multi

       if self._current_view != "repo_list":
           self.notify("Batch tasks only available in repo list view", severity="warning")
           return

       filtered = filter_repos_multi(self._summaries, self._active_filters, self._search_text)
       filtered_repos = list(filtered.values())
       if not filtered_repos:
           self.notify("No repositories for operation", severity="warning")
           return

       self.push_screen(
           BatchTaskModal("Operation Name", task_new_operation, filtered_repos)
       )
   ```

5. Add keybinding to BINDINGS list
   ```python
   Binding("N", "batch_new_operation", "New Operation", show=False)
   ```

6. Update help modal text in `modals.py`
   ```python
   [bold]Batch Tasks[/]
   F             Fetch all (filtered repos)
   P             Prune remote (filtered repos)
   C             Cleanup merged branches (filtered repos)
   N             New operation (filtered repos)
   ```

7. Add tests to `tests/test_batch_tasks.py`

### Safety Considerations

**Read-Only by Default:**
- All existing functionality remains read-only
- Write operations require explicit user action (keybinding)

**Batch Task Safety:**
- Only operate on currently filtered repos (explicit scope)
- Progress feedback shows results incrementally
- Failures highlighted but don't stop batch execution
- Modal display provides confirmation before operations begin

**JJ-Specific Considerations:**
- Non-colocated repos require GIT_DIR for gh CLI (handled automatically)
- jj operations are generally safer (immutable history)
- Some git concepts don't map to jj (stash, staged changes)
- jj has more powerful undo capabilities

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

### Required (VCS-specific)

- **git** - For managing git repositories
  - Used for: status, branch list, commits, stashes, worktrees
  - Assumes git is in PATH
  - Not needed if only managing jj repos

- **jj** - For managing jujutsu repositories
  - Used for: status, bookmark list, changes, workspaces
  - Assumes jj is in PATH
  - Not needed if only managing git repos
  - Install: See https://github.com/martinvonz/jj

### Optional

- **gh** (GitHub CLI) - PR features for both git and jj repos
  - Used for: fetching PR info, check status, PR details
  - Works with both git and jj repositories
  - For non-colocated jj repos: automatically sets GIT_DIR
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

## Planned Features

### Oh-My-Posh Integration

Add CLI command for shell prompt integration to display PR information:

**Command:**
```bash
reda pr-info [--format=json|text|template]
```

**Implementation Requirements:**
- Read PR data from existing cache (cache.py)
- Detect current repository from working directory
- Return PR number, title, and status without API calls
- Fast response time (<50ms) for prompt rendering
- JSON output for parsing by prompt engines
- Template support for custom formatting

**Architecture:**
- Add new CLI command to `__main__.py`
- Reuse `PRCache` from `cache.py`
- Detect VCS type and get current branch
- Look up cached PR info for `{upstream}:{branch}` key
- Return empty/error state if no cache or not in repo

**Use Case:**
Users can display current PR context in their shell prompt without slowing down prompt rendering. This complements the TUI by providing at-a-glance PR info without launching the full application.

**Output Formats:**
- `json`: `{"number": 123, "title": "Feature X", "state": "OPEN", "checks": "passing"}`
- `text`: `#123: Feature X [✓]`
- `template`: User-defined Go template string

**Error Handling:**
- Not in repository: exit silently (no output)
- No cached data: exit silently or show placeholder
- Invalid cache: attempt refresh or show stale indicator

## Release Checklist

1. Run full test suite: `uv run pytest -v`
2. Verify snapshots are current
3. Test manually with real repositories (both git and jj if available)
4. Test batch operations (fetch, prune, cleanup)
5. Update version in `pyproject.toml`
6. Update `README.md` if features changed
7. Run with both light and dark themes
