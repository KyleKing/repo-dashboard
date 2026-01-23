# VCS Generalization Refactoring Plan

**Goal:** Support both jj and git while maintaining GitHub-centric workflow focus

**Scope:**
- ✅ VCS abstraction layer (git + jj)
- ✅ Auto-detection of VCS type
- ✅ GitHub CLI integration for both VCS types
- ✅ Divergent level-2 UIs for jj vs git features
- ✅ Limited write capability via batch maintenance tasks
- ❌ YAML config (auto-discovery sufficient)
- ❌ Full mani-like sync/command execution

---

## Phase 1: VCS Abstraction Layer

### 1.1 Core Abstraction

**File: `src/repo_dashboard/vcs_protocol.py` (new)**
```python
from typing import Protocol, Literal
from pathlib import Path
from .models import RepoSummary, BranchInfo, CommitInfo, StashInfo, WorktreeInfo

VCSType = Literal["git", "jj"]

class VCSOperations(Protocol):
    """Protocol for VCS operations - both git and jj must implement"""

    vcs_type: VCSType

    # Read operations (existing functionality)
    def get_status(self, repo_path: Path) -> RepoSummary: ...
    def get_branches(self, repo_path: Path) -> list[BranchInfo]: ...
    def get_commits_ahead_behind(self, repo_path: Path, branch: str) -> tuple[int, int]: ...
    def get_stashes(self, repo_path: Path) -> list[StashInfo]: ...
    def get_worktrees(self, repo_path: Path) -> list[WorktreeInfo]: ...
    def get_commit_log(self, repo_path: Path, branch: str, limit: int) -> list[CommitInfo]: ...
    def get_modified_files(self, repo_path: Path) -> list[str]: ...
    def get_remote_url(self, repo_path: Path) -> str | None: ...

    # Write operations (new - batch maintenance tasks)
    def fetch_all(self, repo_path: Path) -> tuple[bool, str]: ...
    def prune_remote(self, repo_path: Path) -> tuple[bool, str]: ...
    def cleanup_merged_branches(self, repo_path: Path) -> tuple[bool, str]: ...
```

**Rationale:**
- Protocol allows type-checking without inheritance
- Clear contract for both implementations
- Write operations return `(success: bool, message: str)` for UI feedback

### 1.2 Git Implementation

**File: `src/repo_dashboard/vcs_git.py` (refactor from git_ops.py)**
```python
class GitOperations:
    vcs_type: VCSType = "git"

    # Migrate existing git_ops.py functions here
    def get_status(self, repo_path: Path) -> RepoSummary:
        # Existing logic from git_ops.get_repo_summary()
        ...

    # New write operations
    def fetch_all(self, repo_path: Path) -> tuple[bool, str]:
        """git fetch --all --prune"""
        ...

    def prune_remote(self, repo_path: Path) -> tuple[bool, str]:
        """git remote prune origin"""
        ...

    def cleanup_merged_branches(self, repo_path: Path) -> tuple[bool, str]:
        """Delete local branches that are merged into main/master"""
        # git branch --merged main | grep -v main | xargs git branch -d
        ...
```

### 1.3 JJ Implementation

**File: `src/repo_dashboard/vcs_jj.py` (new)**
```python
class JJOperations:
    vcs_type: VCSType = "jj"

    def __init__(self):
        self._is_colocated_cache: dict[Path, bool] = {}

    def _is_colocated(self, repo_path: Path) -> bool:
        """Check if jj repo is colocated with git"""
        if repo_path in self._is_colocated_cache:
            return self._is_colocated_cache[repo_path]

        # Colocated: has both .jj/ and .git/
        # Non-colocated: only .jj/, git data in .jj/repo/store/git
        is_col = (repo_path / ".git").is_dir()
        self._is_colocated_cache[repo_path] = is_col
        return is_col

    def _get_git_dir(self, repo_path: Path) -> str:
        """Get GIT_DIR for gh CLI integration"""
        if self._is_colocated(repo_path):
            return str(repo_path / ".git")
        return str(repo_path / ".jj" / "repo" / "store" / "git")

    def get_status(self, repo_path: Path) -> RepoSummary:
        # jj status --no-pager
        # Parse output to RepoSummary
        # Note: jj terminology differs:
        #   - "working copy" instead of "working directory"
        #   - "change" instead of "commit"
        #   - No concept of "staged" (everything is always staged)
        ...

    def get_branches(self, repo_path: Path) -> list[BranchInfo]:
        # jj branch list
        # Note: jj has bookmarks (like git branches) and anonymous branches
        ...

    def fetch_all(self, repo_path: Path) -> tuple[bool, str]:
        """jj git fetch --all-remotes"""
        ...
```

**jj vs git Concept Mapping:**

| Concept | Git | JJ | Notes |
|---------|-----|-----|-------|
| Current location | HEAD | @ (working copy change) | jj always has a working copy change |
| Branch | branch | bookmark | jj bookmarks are like git branches |
| Staged changes | staged/index | N/A | jj auto-tracks all changes |
| Uncommitted | unstaged + staged | working copy | Different mental model |
| Commits ahead/behind | ahead/behind | ahead/behind | Similar concept |
| Remote tracking | upstream branch | tracking bookmark | Similar |
| Stash | stash | N/A | jj doesn't need stashing (can create changes) |
| Worktree | worktree | workspace | Similar but jj workspaces are more powerful |

### 1.4 VCS Detection & Factory

**File: `src/repo_dashboard/vcs_factory.py` (new)**
```python
def detect_vcs_type(repo_path: Path) -> VCSType | None:
    """Detect VCS type by directory presence"""
    # Prefer jj if both exist (colocated repos)
    if (repo_path / ".jj").is_dir():
        return "jj"
    if (repo_path / ".git").is_dir():
        return "git"
    return None

def get_vcs_operations(repo_path: Path) -> VCSOperations:
    """Factory function to get appropriate VCS operations"""
    vcs_type = detect_vcs_type(repo_path)

    if vcs_type == "jj":
        return JJOperations()
    elif vcs_type == "git":
        return GitOperations()
    else:
        raise ValueError(f"No VCS repository found at {repo_path}")

# Convenience function for GitHub CLI with correct GIT_DIR
def get_github_env(vcs_ops: VCSOperations, repo_path: Path) -> dict[str, str]:
    """Get environment variables for gh CLI"""
    env = os.environ.copy()

    if vcs_ops.vcs_type == "jj":
        # Non-colocated jj repos need GIT_DIR set
        if hasattr(vcs_ops, "_get_git_dir"):
            env["GIT_DIR"] = vcs_ops._get_git_dir(repo_path)

    return env
```

### 1.5 Model Updates

**File: `src/repo_dashboard/models.py`**
```python
from typing import Literal

VCSType = Literal["git", "jj"]

@dataclass(frozen=True)
class RepoSummary:
    path: Path
    name: str
    vcs_type: VCSType  # NEW FIELD
    current_branch: str
    is_dirty: bool
    commits_ahead: int
    commits_behind: int
    has_stash: bool
    modified_date: float
    uncommitted_changes: int = 0  # Note: jj doesn't distinguish staged/unstaged
    upstream_branch: str | None = None
    remote_url: str | None = None

    # jj-specific fields (None for git repos)
    jj_is_colocated: bool | None = None
    jj_working_copy_id: str | None = None  # jj change ID for @
```

---

## Phase 2: Discovery & GitHub Integration

### 2.1 Update Discovery

**File: `src/repo_dashboard/discovery.py`**
```python
def _is_repo_root(path: Path) -> bool:
    """Check if directory is a VCS repository root"""
    return (path / ".git").is_dir() or (path / ".jj").is_dir()

def discover_repos(root_path: Path, max_depth: int = 2) -> list[Path]:
    """Discover both git and jj repositories"""
    # Existing logic works - just update _is_repo_root()
    ...
```

### 2.2 GitHub CLI Integration

**File: `src/repo_dashboard/github_ops.py`**

Update all `subprocess.run()` calls to use `get_github_env()`:

```python
from .vcs_factory import get_github_env, get_vcs_operations

def get_pr_for_branch(
    repo_path: Path,
    branch: str,
    cache: dict[str, PRInfo | None],
) -> PRInfo | None:
    """Get PR info - works for both git and jj repos"""
    vcs_ops = get_vcs_operations(repo_path)
    env = get_github_env(vcs_ops, repo_path)

    # Rest of logic unchanged, but use env parameter
    result = subprocess.run(
        ["gh", "pr", "list", "--head", branch, "--json", "..."],
        cwd=repo_path,
        env=env,  # NEW: Use custom environment
        capture_output=True,
        text=True,
        timeout=10,
    )
    ...
```

---

## Phase 3: UI Updates

### 3.1 Level 1: Repository List

**File: `src/repo_dashboard/app.py`**

Add VCS type indicator to table:

```python
def _populate_table(self, table: DataTable) -> None:
    """Populate main table with repository data"""
    # Add VCS type column (optional - could use icon in Name column instead)
    table.add_column("VCS", width=4)  # "git" or "jj"
    table.add_column("Name", width=30)
    # ... existing columns

    for repo in sorted_repos:
        # Add VCS icon/badge
        vcs_badge = "🔧" if repo.vcs_type == "jj" else "📁"  # Or use text
        table.add_row(
            repo.vcs_type,  # or vcs_badge
            repo.name,
            # ... existing fields
        )
```

**Styling (app.tcss):**
```css
/* VCS type styling */
DataTable .vcs-git {
    color: $text;
}

DataTable .vcs-jj {
    color: $mauve;  /* Catppuccin mauve for jj */
}
```

### 3.2 Level 2: Repository Details (Unified UI Architecture)

**Design Principle:** Maximize visual consistency and code sharing. Only diverge when VCS features fundamentally differ.

#### Architecture Overview

**Core Strategy:**
- **Single base class** (`RepoDetailScreen`) with shared layout, keybindings, and behavior
- **VCS-specific subclasses** (`GitRepoDetailScreen`, `JJRepoDetailScreen`) for terminology and data loading
- **Shared table structures** with identical columns, spacing, and interaction patterns
- **Unified context panel format** for displaying selected item details
- **Consistent section ordering** across both VCS types

**What's Shared (90% of code):**
- Layout composition (2-column with sections)
- Keybindings (`Tab`, `Space`, `Enter`, `p`, `r`, `Escape`)
- Table navigation logic
- Context panel rendering structure
- PR integration (GitHub-centric)
- Ahead/behind display logic
- File modification lists
- Error handling and loading states

**What's Different (10% of code):**
- Section titles ("Branches" vs "Bookmarks", "Stashes" vs "Conflicts")
- VCS command execution (git vs jj CLI)
- Special features (stashes for git, conflicts for jj)
- Workspace/worktree visibility logic (git always shows, jj hides if single)
- Terminology in prompts and messages

**Benefits:**
- ✅ Consistent user experience across VCS types
- ✅ Reduced maintenance burden (fix once, works for both)
- ✅ Easy to add new VCS support (extend base class)
- ✅ Clear separation of concerns (layout vs data vs VCS operations)
- ✅ Type-safe with Protocol-based VCS abstraction

#### Side-by-Side Comparison

```
┌─ GIT REPO ──────────────────┬─ JJ REPO ───────────────────┐
│                             │                             │
│ ┌─ Branches ──────────────┐ │ ┌─ Bookmarks ─────────────┐ │
│ │ * main        PR #123   │ │ │ * main        PR #123   │ │
│ │   feature     --        │ │ │   feature     --        │ │
│ └─────────────────────────┘ │ └─────────────────────────┘ │
│                             │                             │
│ ┌─ Working State ─────────┐ │ ┌─ Working State ─────────┐ │
│ │ Current: feature        │ │ │ Current: feature        │ │
│ │ Modified: 3 files       │ │ │ Modified: 3 files       │ │
│ └─────────────────────────┘ │ └─────────────────────────┘ │
│                             │                             │
│ ┌─ Stashes ───────────────┐ │ ┌─ Conflicts ─────────────┐ │
│ │ stash@{0} WIP work      │ │ │ (none)                  │ │
│ └─────────────────────────┘ │ └─────────────────────────┘ │
│                             │                             │
│ ┌─ Worktrees ─────────────┐ │ ┌─ Workspaces ────────────┐ │
│ │ ● .          main       │ │ │ Single workspace        │ │
│ │ ○ ../work2   feature    │ │ │ (hidden if one)         │ │
│ └─────────────────────────┘ │ └─────────────────────────┘ │
│                             │                             │
└─────────────────────────────┴─────────────────────────────┘

     IDENTICAL LAYOUT             ONLY LABELS DIFFER
     Same positions               Same table structure
     Same interactions            Same colors & styling
```

**Key observations:**
- Section 1 (top): Only label differs ("Branches" vs "Bookmarks")
- Section 2: Completely identical (working state is universal)
- Section 3: Different feature (stashes vs conflicts) but same position/size
- Section 4: Same concept (workspaces) with different visibility rules
- Right context panel: Identical structure and format for both

#### Unified Layout Structure

Both git and jj use the same 2-column layout:

```
┌──────────────────────────────────────────────────────────────────┐
│ Header: <repo_name> (<vcs_type>)                                 │
├────────────────────────────┬─────────────────────────────────────┤
│ Left Column (Navigation)   │ Right Column (Details)              │
│                            │                                     │
│ ┌─ Branches/Bookmarks ───┐ │ ┌─ <Selected Item> ──────────────┐ │
│ │ * main        PR #123  │ │ │ Tracking: origin/main          │ │
│ │   feature     --       │ │ │ PR: #123 "Add auth"            │ │
│ └────────────────────────┘ │ │ Status: ✓ Checks passed        │ │
│                            │ │                                 │ │
│ ┌─ Working State ────────┐ │ │ Ahead: 2  Behind: 0            │ │
│ │ Current: feature       │ │ │                                 │ │
│ │ Modified: 3 files      │ │ │ Recent commits:                │ │
│ └────────────────────────┘ │ │ - abc123 Add validation        │ │
│                            │ │ - def456 Update tests           │ │
│ ┌─ VCS-Specific ─────────┐ │ │                                 │ │
│ │ Git: Stashes           │ │ │ Modified files:                │ │
│ │ JJ:  Conflicts         │ │ │ M src/auth.py                  │ │
│ └────────────────────────┘ │ │ M tests/test_auth.py           │ │
│                            │ └─────────────────────────────────┘ │
│ ┌─ Workspaces/Worktrees ─┐ │                                     │
│ │ . (main)               │ │                                     │
│ │ ../work2               │ │                                     │
│ └────────────────────────┘ │                                     │
└────────────────────────────┴─────────────────────────────────────┘
│ Footer: Keybindings                                              │
└──────────────────────────────────────────────────────────────────┘
```

#### Code Architecture with Shared Components

**File: `src/repo_dashboard/modals.py`**

##### Base Class and Mixins

```python
from typing import Protocol, Literal
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Static, Header, Footer

# Shared state for table focus management
TableName = Literal["branches", "working", "special", "workspaces"]

class RepoDetailScreen(ModalScreen):
    """Base class for repository details with shared layout and logic"""

    BINDINGS = [
        Binding("escape", "dismiss", "Back"),
        Binding("r", "refresh", "Refresh"),
        Binding("tab", "next_table", "Next Section"),
        Binding("shift+tab", "prev_table", "Prev Section"),
        Binding("p", "open_pr", "Open PR", show=False),
        Binding("space", "select_item", "Select"),
        Binding("enter", "select_item", "Select"),
    ]

    def __init__(self, repo_summary: RepoSummary):
        super().__init__()
        self.repo_summary = repo_summary
        self.vcs_ops = get_vcs_operations(repo_summary.path)
        self.current_table: TableName = "branches"
        self.selected_branch: str | None = None

    def compose(self) -> ComposeResult:
        """Shared layout structure"""
        yield Header()
        with Horizontal(id="detail-layout"):
            with Vertical(id="detail-left"):
                # Section 1: Branches/Bookmarks (VCS-specific terminology)
                yield Static(self._get_branches_title(), classes="section-title")
                yield DataTable(id="branches-table", zebra_stripes=True)

                # Section 2: Working State (unified concept)
                yield Static("Working State", classes="section-title")
                yield Static("", id="working-state-panel", classes="info-panel")

                # Section 3: VCS-specific features
                yield Static(self._get_special_section_title(), classes="section-title")
                yield DataTable(id="special-table", zebra_stripes=True)

                # Section 4: Workspaces/Worktrees (similar concepts)
                yield Static(self._get_workspaces_title(), classes="section-title")
                yield DataTable(id="workspaces-table", zebra_stripes=True)

            with Vertical(id="detail-right"):
                yield Static("", id="detail-context", classes="context-panel")
        yield Footer()

    # Abstract methods for VCS-specific terminology
    def _get_branches_title(self) -> str:
        """Override in subclass: 'Branches' or 'Bookmarks'"""
        raise NotImplementedError

    def _get_special_section_title(self) -> str:
        """Override in subclass: 'Stashes' or 'Conflicts'"""
        raise NotImplementedError

    def _get_workspaces_title(self) -> str:
        """Override in subclass: 'Worktrees' or 'Workspaces'"""
        raise NotImplementedError

    # Shared behavior
    def action_next_table(self) -> None:
        """Navigate to next table section"""
        tables = ["branches", "working", "special", "workspaces"]
        current_idx = tables.index(self.current_table)
        next_idx = (current_idx + 1) % len(tables)
        self.current_table = tables[next_idx]
        self._focus_current_table()

    def action_prev_table(self) -> None:
        """Navigate to previous table section"""
        tables = ["branches", "working", "special", "workspaces"]
        current_idx = tables.index(self.current_table)
        prev_idx = (current_idx - 1) % len(tables)
        self.current_table = tables[prev_idx]
        self._focus_current_table()

    def _focus_current_table(self) -> None:
        """Focus the appropriate table widget"""
        table_map = {
            "branches": "#branches-table",
            "special": "#special-table",
            "workspaces": "#workspaces-table",
        }
        if self.current_table in table_map:
            table = self.query_one(table_map[self.current_table], DataTable)
            table.focus()

    async def on_mount(self) -> None:
        """Initialize all sections with data"""
        await self._load_branches_data()
        await self._load_working_state()
        await self._load_special_section()
        await self._load_workspaces_data()

    # Methods to override for VCS-specific data loading
    async def _load_branches_data(self) -> None:
        """Load branches/bookmarks - override in subclass"""
        raise NotImplementedError

    async def _load_working_state(self) -> None:
        """Load working state - shared logic with VCS-specific calls"""
        panel = self.query_one("#working-state-panel", Static)

        # Get current branch/bookmark
        current = self.repo_summary.current_branch

        # Get modified files count
        modified_files = self.vcs_ops.get_modified_files(self.repo_summary.path)
        file_count = len(modified_files)

        # Render working state (shared format)
        state_text = dedent(f"""\
            Current: {current}
            Modified: {file_count} files
            Status: {"dirty" if self.repo_summary.is_dirty else "clean"}""")

        panel.update(state_text)

    async def _load_special_section(self) -> None:
        """Load VCS-specific section (stashes or conflicts)"""
        raise NotImplementedError

    async def _load_workspaces_data(self) -> None:
        """Load workspaces/worktrees - similar structure, different commands"""
        raise NotImplementedError

    @on(DataTable.RowSelected, "#branches-table")
    def on_branch_selected(self, event: DataTable.RowSelected) -> None:
        """Handle branch/bookmark selection - shared logic"""
        self.selected_branch = str(event.row_key.value)
        self._update_context_panel()

    def _update_context_panel(self) -> None:
        """Update right context panel - shared structure, VCS-specific data"""
        raise NotImplementedError

    def action_open_pr(self) -> None:
        """Open PR in browser if exists - shared logic"""
        if not self.selected_branch:
            self.notify("No branch selected", severity="warning")
            return

        # Use shared GitHub ops
        pr_info = get_pr_for_branch(
            self.repo_summary.path,
            self.selected_branch,
            cache={},  # Could use shared cache
        )

        if pr_info and pr_info.url:
            import webbrowser
            webbrowser.open(pr_info.url)
            self.notify(f"Opened PR #{pr_info.number}")
        else:
            self.notify("No PR found for this branch", severity="info")
```

##### Git Implementation

```python
class GitRepoDetailScreen(RepoDetailScreen):
    """Git-specific repository detail view"""

    def _get_branches_title(self) -> str:
        return "Branches"

    def _get_special_section_title(self) -> str:
        return "Stashes"

    def _get_workspaces_title(self) -> str:
        return "Worktrees"

    async def _load_branches_data(self) -> None:
        """Load git branches"""
        table = self.query_one("#branches-table", DataTable)
        table.add_columns("", "Branch", "Tracking", "PR", "Ahead", "Behind")

        branches = self.vcs_ops.get_branches(self.repo_summary.path)

        for branch in branches:
            # Check for PR
            pr_info = get_pr_for_branch(
                self.repo_summary.path,
                branch.name,
                cache={},
            )
            pr_str = f"#{pr_info.number}" if pr_info else "—"

            # Current branch marker
            marker = "*" if branch.is_current else " "

            # Ahead/behind
            ahead, behind = self.vcs_ops.get_commits_ahead_behind(
                self.repo_summary.path,
                branch.name,
            )

            table.add_row(
                marker,
                branch.name,
                branch.tracking or "—",
                pr_str,
                str(ahead) if ahead > 0 else "—",
                str(behind) if behind > 0 else "—",
                key=branch.name,
            )

    async def _load_special_section(self) -> None:
        """Load git stashes"""
        table = self.query_one("#special-table", DataTable)
        table.add_columns("Index", "Message", "Date")

        stashes = self.vcs_ops.get_stashes(self.repo_summary.path)

        if not stashes:
            table.add_row("—", "No stashes", "—")
            return

        for stash in stashes:
            table.add_row(
                str(stash.index),
                stash.message,
                stash.date,
                key=f"stash@{{{stash.index}}}",
            )

    async def _load_workspaces_data(self) -> None:
        """Load git worktrees"""
        table = self.query_one("#workspaces-table", DataTable)
        table.add_columns("", "Path", "Branch", "Commit")

        worktrees = self.vcs_ops.get_worktrees(self.repo_summary.path)

        if not worktrees:
            table.add_row("—", "No worktrees", "—", "—")
            return

        for worktree in worktrees:
            # Main worktree marker
            marker = "●" if worktree.is_main else "○"

            table.add_row(
                marker,
                str(worktree.path),
                worktree.branch or "—",
                worktree.commit[:8] if worktree.commit else "—",
                key=str(worktree.path),
            )

    def _update_context_panel(self) -> None:
        """Update context panel with git branch details"""
        if not self.selected_branch:
            return

        panel = self.query_one("#detail-context", Static)

        # Get branch info
        ahead, behind = self.vcs_ops.get_commits_ahead_behind(
            self.repo_summary.path,
            self.selected_branch,
        )

        # Get PR info
        pr_info = get_pr_for_branch(
            self.repo_summary.path,
            self.selected_branch,
            cache={},
        )

        # Get recent commits
        commits = self.vcs_ops.get_commit_log(
            self.repo_summary.path,
            self.selected_branch,
            limit=5,
        )

        # Get modified files
        modified = self.vcs_ops.get_modified_files(self.repo_summary.path)

        # Build context text
        pr_section = ""
        if pr_info:
            status_icon = "✓" if pr_info.status == "MERGED" else "○"
            pr_section = dedent(f"""\
                PR: #{pr_info.number} "{pr_info.title}"
                Status: {status_icon} {pr_info.status}
                Checks: {pr_info.checks_status or "—"}
                """)

        commits_section = "Recent commits:\n"
        for commit in commits:
            short_hash = commit.hash[:8]
            commits_section += f"  {short_hash} {commit.message}\n"

        files_section = "Modified files:\n"
        if modified:
            for file in modified[:10]:  # Limit to 10
                files_section += f"  M {file}\n"
            if len(modified) > 10:
                files_section += f"  ... and {len(modified) - 10} more\n"
        else:
            files_section += "  (none)\n"

        context_text = dedent(f"""\
            ━━━ {self.selected_branch} ━━━

            Tracking: {self.selected_branch}@origin
            {pr_section}
            Ahead: {ahead}  Behind: {behind}

            {commits_section}
            {files_section}""")

        panel.update(context_text)
```

##### JJ Implementation

```python
class JJRepoDetailScreen(RepoDetailScreen):
    """JJ-specific repository detail view"""

    def _get_branches_title(self) -> str:
        return "Bookmarks"

    def _get_special_section_title(self) -> str:
        return "Conflicts"

    def _get_workspaces_title(self) -> str:
        return "Workspaces"

    async def _load_branches_data(self) -> None:
        """Load jj bookmarks"""
        table = self.query_one("#branches-table", DataTable)
        table.add_columns("", "Bookmark", "Tracking", "PR", "Ahead", "Behind")

        bookmarks = self.vcs_ops.get_branches(self.repo_summary.path)  # Returns bookmarks

        for bookmark in bookmarks:
            # Check for PR (using GitHub branch name)
            pr_info = get_pr_for_branch(
                self.repo_summary.path,
                bookmark.name,
                cache={},
            )
            pr_str = f"#{pr_info.number}" if pr_info else "—"

            # Current bookmark marker
            marker = "*" if bookmark.is_current else " "

            # Ahead/behind (jj supports this too)
            ahead, behind = self.vcs_ops.get_commits_ahead_behind(
                self.repo_summary.path,
                bookmark.name,
            )

            # Tracking status
            tracking = f"{bookmark.name}@origin" if bookmark.tracking else "(local)"

            table.add_row(
                marker,
                bookmark.name,
                tracking,
                pr_str,
                str(ahead) if ahead > 0 else "—",
                str(behind) if behind > 0 else "—",
                key=bookmark.name,
            )

    async def _load_special_section(self) -> None:
        """Load jj conflicts"""
        table = self.query_one("#special-table", DataTable)
        table.add_columns("Change ID", "Bookmark", "Files")

        # jj log -r 'conflicts()' to find conflicted changes
        # This is a placeholder - actual implementation needs jj parsing
        conflicts = self._get_conflicts()

        if not conflicts:
            table.add_row("—", "No conflicts", "—")
            return

        for conflict in conflicts:
            table.add_row(
                conflict.change_id[:8],
                conflict.bookmark or "—",
                ", ".join(conflict.files),
                key=conflict.change_id,
            )

    def _get_conflicts(self) -> list:
        """Get conflicted changes from jj"""
        # Run: jj log -r 'conflicts()' --no-graph -T 'change_id ++ " " ++ description'
        # Parse output to conflict objects
        # TODO: Implement this
        return []

    async def _load_workspaces_data(self) -> None:
        """Load jj workspaces"""
        table = self.query_one("#workspaces-table", DataTable)
        table.add_columns("", "Path", "Change ID", "Bookmark")

        # jj workspace list
        workspaces = self.vcs_ops.get_worktrees(self.repo_summary.path)  # Reuse interface

        if not workspaces or len(workspaces) <= 1:
            # Only show if multiple workspaces exist
            table.add_row("—", "Single workspace", "—", "—")
            return

        for workspace in workspaces:
            # Current workspace marker
            marker = "●" if workspace.is_main else "○"

            table.add_row(
                marker,
                str(workspace.path),
                workspace.commit[:8] if workspace.commit else "—",  # Change ID
                workspace.branch or "—",  # Bookmark
                key=str(workspace.path),
            )

    def _update_context_panel(self) -> None:
        """Update context panel with jj bookmark details"""
        if not self.selected_branch:
            return

        panel = self.query_one("#detail-context", Static)

        # Get bookmark info (similar to git branch)
        ahead, behind = self.vcs_ops.get_commits_ahead_behind(
            self.repo_summary.path,
            self.selected_branch,
        )

        # Get PR info (same as git)
        pr_info = get_pr_for_branch(
            self.repo_summary.path,
            self.selected_branch,
            cache={},
        )

        # Get recent changes (jj log)
        changes = self.vcs_ops.get_commit_log(
            self.repo_summary.path,
            self.selected_branch,
            limit=5,
        )

        # Get modified files
        modified = self.vcs_ops.get_modified_files(self.repo_summary.path)

        # Build context text (similar structure to git)
        pr_section = ""
        if pr_info:
            status_icon = "✓" if pr_info.status == "MERGED" else "○"
            pr_section = dedent(f"""\
                PR: #{pr_info.number} "{pr_info.title}"
                Status: {status_icon} {pr_info.status}
                Checks: {pr_info.checks_status or "—"}
                """)

        changes_section = "Recent changes:\n"
        for change in changes:
            change_id = change.hash[:8]  # jj change ID
            changes_section += f"  {change_id} {change.message}\n"

        files_section = "Modified files:\n"
        if modified:
            for file in modified[:10]:
                files_section += f"  M {file}\n"
            if len(modified) > 10:
                files_section += f"  ... and {len(modified) - 10} more\n"
        else:
            files_section += "  (none)\n"

        tracking_status = "(local only)" if ahead == -1 else f"{self.selected_branch}@origin"

        context_text = dedent(f"""\
            ━━━ {self.selected_branch} ━━━

            Tracking: {tracking_status}
            {pr_section}
            Ahead: {ahead if ahead >= 0 else "—"}  Behind: {behind if behind >= 0 else "—"}

            {changes_section}
            {files_section}""")

        panel.update(context_text)
```

#### Model Updates for Worktrees/Workspaces

**File: `src/repo_dashboard/models.py`**

```python
@dataclass(frozen=True)
class WorktreeInfo:
    """Git worktree or JJ workspace information"""
    path: Path
    branch: str | None  # Git branch or JJ bookmark
    commit: str | None  # Commit hash (git) or change ID (jj)
    is_main: bool  # True for main worktree/workspace
    is_detached: bool = False  # Git-specific: detached HEAD
```

#### VCS Protocol Update

**File: `src/repo_dashboard/vcs_protocol.py`**

Add to protocol:
```python
class VCSOperations(Protocol):
    # ... existing methods

    def get_worktrees(self, repo_path: Path) -> list[WorktreeInfo]: ...
    """Get worktrees (git) or workspaces (jj)"""
```

#### Git Worktree Implementation

**File: `src/repo_dashboard/vcs_git.py`**

```python
def get_worktrees(self, repo_path: Path) -> list[WorktreeInfo]:
    """Get git worktrees using git worktree list --porcelain"""
    result = subprocess.run(
        ["git", "worktree", "list", "--porcelain"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        timeout=5,
    )

    if result.returncode != 0:
        return []

    worktrees = []
    current = {}

    for line in result.stdout.strip().split("\n"):
        if not line:
            # End of worktree entry
            if current:
                worktrees.append(WorktreeInfo(
                    path=Path(current.get("worktree", "")),
                    branch=current.get("branch"),
                    commit=current.get("HEAD"),
                    is_main=current.get("bare", False),
                    is_detached=current.get("detached", False),
                ))
                current = {}
            continue

        key, *value = line.split(maxsplit=1)
        if key == "worktree":
            current["worktree"] = value[0] if value else ""
        elif key == "HEAD":
            current["HEAD"] = value[0] if value else ""
        elif key == "branch":
            # Format: refs/heads/branch-name
            branch_ref = value[0] if value else ""
            current["branch"] = branch_ref.replace("refs/heads/", "")
        elif key == "detached":
            current["detached"] = True
        elif key == "bare":
            current["bare"] = True

    return worktrees
```

#### JJ Workspace Implementation

**File: `src/repo_dashboard/vcs_jj.py`**

```python
def get_worktrees(self, repo_path: Path) -> list[WorktreeInfo]:
    """Get jj workspaces using jj workspace list"""
    result = subprocess.run(
        ["jj", "workspace", "list"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        timeout=5,
    )

    if result.returncode != 0:
        return []

    workspaces = []
    for line in result.stdout.strip().split("\n"):
        # Format: "workspace_name: /path/to/workspace (change_id)"
        # Or: "default: . (abc123)"
        match = re.match(r"(\w+):\s+(.+?)\s+\(([a-f0-9]+)\)", line)
        if not match:
            continue

        name, path, change_id = match.groups()
        is_main = name == "default" or path == "."

        workspaces.append(WorktreeInfo(
            path=Path(path),
            branch=name if name != "default" else None,
            commit=change_id,
            is_main=is_main,
            is_detached=False,  # jj doesn't have detached state
        ))

    return workspaces
```

#### Usage in app.py

**File: `src/repo_dashboard/app.py`**

```python
def action_show_details(self) -> None:
    """Show repository details - route to appropriate screen"""
    repo = self._get_selected_repo()
    if not repo:
        return

    if repo.vcs_type == "git":
        self.push_screen(GitRepoDetailScreen(repo))
    elif repo.vcs_type == "jj":
        self.push_screen(JJRepoDetailScreen(repo))
```

### 3.3 Workspace/Worktree UX Design Deep-Dive

#### Use Cases and User Needs

**Why users need workspace/worktree visibility:**

1. **Multi-branch development**
   - Work on feature branch while keeping main available for quick fixes
   - Review someone else's PR without disrupting current work
   - Run long-running tests in one worktree while developing in another

2. **Context switching**
   - Quickly see which worktree/workspace is on which branch
   - Identify abandoned or stale worktrees that can be cleaned up
   - Jump to specific worktree for focused work

3. **Disk space management**
   - See all worktrees/workspaces consuming disk space
   - Identify which can be removed safely

4. **Mental model alignment**
   - Users may forget they have worktrees/workspaces
   - Dashboard makes them visible and discoverable
   - Reduces confusion about "why is this branch checked out elsewhere?"

#### Git Worktrees vs JJ Workspaces: Conceptual Differences

**Git Worktrees:**
- **Purpose:** Multiple working directories for the same repository
- **Creation:** `git worktree add ../path branch-name`
- **Limitation:** Each branch can only be checked out in one worktree
- **Main worktree:** The original clone location (special status)
- **Structure:** Linked worktrees share .git directory, store metadata in .git/worktrees/
- **Common pattern:** One main worktree for long-lived work, temporary worktrees for side tasks

**JJ Workspaces:**
- **Purpose:** Multiple working copies of the repository, more flexible than git
- **Creation:** `jj workspace add ../path`
- **Advantage:** Can have multiple workspaces on the same change/bookmark
- **No main workspace:** All workspaces are equal (though one is typically "default")
- **Structure:** Each workspace has its own working copy state in .jj/
- **Common pattern:** Multiple workspaces for different concerns (testing, development, review)

#### Display Strategy

**When to show the worktrees/workspaces section:**

| Scenario | Display Strategy | Rationale |
|----------|------------------|-----------|
| Single git repo, no worktrees | Show empty section with hint | User education: "No worktrees. Use `git worktree add` to create." |
| Git with worktrees | Show table with all worktrees | Essential info, helps with navigation |
| Single jj workspace (default only) | Hide section or show "Single workspace" | Reduces clutter, most jj repos don't use multiple workspaces |
| JJ with multiple workspaces | Show table with all workspaces | Important for workspace-heavy workflows |

**Table layout (unified structure):**

```
┌─ Worktrees/Workspaces ──────────────────────────────────┐
│   Path            Branch/Bookmark   Change ID   Status  │
│ ● .               main               abc12345    clean   │
│ ○ ../feature-1    feature-1          def67890    dirty   │
│ ○ ../hotfix       hotfix             ghi11121    clean   │
└─────────────────────────────────────────────────────────┘
```

Columns:
- **Marker:** `●` = current/main, `○` = other
- **Path:** Relative or absolute path to worktree/workspace
- **Branch/Bookmark:** Git branch or JJ bookmark name
- **Change ID:** Git commit hash (short) or JJ change ID
- **Status:** clean/dirty (modified files indicator)

#### Interaction Design

**Selection behavior:**

1. **Navigate with arrow keys**
   - Up/Down to select worktree/workspace row
   - Enter/Space to show details in right panel

2. **Context panel updates on selection:**
   ```
   ━━━ Worktree: ../feature-1 ━━━

   Branch: feature-1
   Commit: def67890 "Add authentication"
   Status: 3 modified files

   Modified files:
     M src/auth.py
     M tests/test_auth.py
     A src/models.py

   Location: /Users/dev/project/feature-1
   Created: 2 days ago
   ```

3. **Actions (future enhancement):**
   - `o` - Open worktree/workspace in new terminal
   - `d` - Delete/remove worktree (with confirmation)
   - `j` - Jump to worktree location in file browser

**Visual differentiation:**

- **Current/main marker:** Use color + symbol
  - `●` in green for main/current
  - `○` in default text color for others

- **Status color coding:**
  - Clean: Default text color
  - Dirty: Orange (peach) to match uncommitted changes theme
  - Detached HEAD (git): Yellow with warning icon

- **Path display:**
  - Show relative path if within parent directory (e.g., `../feature-1`)
  - Show absolute path if elsewhere (e.g., `/Users/dev/projects/feature-1`)
  - Highlight current directory with `●` marker

#### Edge Cases and Error Handling

**Git worktrees:**

1. **Detached HEAD worktree:**
   - Display: "HEAD" in branch column
   - Color: Yellow with ⚠️ icon
   - Context: Show commit hash prominently

2. **Deleted worktree directory (orphaned metadata):**
   - Display: Path with ❌ icon
   - Context: "Directory missing. Run `git worktree prune`"
   - Allow user to trigger cleanup

3. **Locked worktree:**
   - Display: 🔒 icon next to path
   - Context: "Worktree locked. Reason: [lock reason]"

**JJ workspaces:**

1. **Workspace with conflict:**
   - Display: ⚠️ icon in status column
   - Color: Orange (peach)
   - Context: "Workspace has unresolved conflicts"

2. **Workspace on diverged bookmark:**
   - Display: 📌 icon
   - Context: "Bookmark diverged from remote"

3. **Stale workspace (change has been rebased away):**
   - Display: 👻 icon
   - Context: "This change may be obsolete"

#### Progressive Disclosure

**Level 1 (Main repo list):**
- No worktree/workspace visibility
- Possible future: Badge showing "has worktrees" count

**Level 2 (Repo detail view):**
- Dedicated section showing all worktrees/workspaces
- Collapsed by default if only one exists (jj)
- Expanded by default if multiple exist

**Level 3 (Context panel):**
- Selected worktree/workspace details
- Modified files, creation date, size
- Quick actions (future)

#### Data Refresh Strategy

**When to refresh worktree/workspace data:**

1. **On modal open** - Always fetch fresh data
2. **On explicit refresh** (`r` key) - Re-query VCS
3. **After write operations** - If we add worktree management features
4. **Periodic refresh** - Optional: every 30s if modal is open

**Performance considerations:**
- `git worktree list` is fast (~10ms)
- `jj workspace list` is fast (~20ms)
- Cache results within modal session
- No need for aggressive caching

#### Accessibility and Usability

**Keyboard navigation:**
- `Tab` / `Shift+Tab` to move between sections
- Arrow keys for row selection
- `Enter` / `Space` to view details
- `Escape` to go back
- All actions have keyboard shortcuts

**Visual hierarchy:**
- Section headers use consistent styling
- Current selection highlighted with focus ring
- Empty states are informative, not just blank

**Error communication:**
- If git/jj command fails, show friendly message
- Suggest remediation actions where possible
- Don't crash on missing worktrees/workspaces

#### Example Scenarios

**Scenario 1: Git Developer with Multiple Worktrees**

User has:
- Main worktree: `~/project` on `main` (clean)
- Feature worktree: `~/project-feature` on `feature-auth` (dirty)
- Review worktree: `~/project-review` on `pr-123` (clean)

Dashboard shows:
```
┌─ Worktrees ─────────────────────────────────────────────┐
│   Path              Branch         Commit    Status     │
│ ● .                 main           abc1234   clean      │
│ ○ ../project-feature feature-auth  def5678   dirty (3)  │
│ ○ ../project-review  pr-123        ghi9012   clean      │
└─────────────────────────────────────────────────────────┘
```

Actions:
- Select feature worktree → see 3 modified files in context
- Press `r` to refresh → updates status
- Visual reminder of active work contexts

**Scenario 2: JJ User with Single Workspace**

User has:
- One workspace: `~/project` on `main` bookmark

Dashboard shows:
```
┌─ Workspaces ────────────────────────────────────────────┐
│ Single workspace (default)                              │
└─────────────────────────────────────────────────────────┘
```

Or section is hidden entirely (configurable).

**Scenario 3: JJ User with Multiple Workspaces**

User has:
- Default workspace: `~/project` on `main` bookmark
- Testing workspace: `~/project-test` on `main` bookmark (different change)
- Experiment workspace: `~/project-exp` on `experiment` bookmark

Dashboard shows:
```
┌─ Workspaces ────────────────────────────────────────────┐
│   Path              Bookmark    Change ID   Status      │
│ ● .                 main        klmn234     clean       │
│ ○ ../project-test   main        opqr567     dirty (2)   │
│ ○ ../project-exp    experiment  stuv890     clean       │
└─────────────────────────────────────────────────────────┘
```

Note: Two workspaces on `main` bookmark with different changes (jj feature).

**Scenario 4: Abandoned Worktrees**

User has forgotten worktrees:
- Worktree from 6 months ago still exists
- Dashboard surfaces this information

```
┌─ Worktrees ─────────────────────────────────────────────┐
│   Path              Branch    Commit    Status   Age    │
│ ● .                 main      abc1234   clean    -      │
│ ○ ../old-feature    old-feat  def5678   clean    6mo    │
└─────────────────────────────────────────────────────────┘
```

Context panel shows:
```
━━━ Worktree: ../old-feature ━━━

Branch: old-feature (merged)
Last modified: 6 months ago
Status: May be safe to remove

Suggested action:
  git worktree remove ../old-feature
```

This helps with repository hygiene.

#### Implementation Priority

**Phase 1 (Must-have):**
- Basic worktree/workspace listing
- Show path, branch/bookmark, commit/change ID
- Current/main marker
- Empty state handling

**Phase 2 (Should-have):**
- Status indicators (clean/dirty)
- Context panel with details
- Refresh capability
- Error handling for orphaned worktrees

**Phase 3 (Nice-to-have):**
- Age/last modified information
- Quick actions (open, delete)
- Conflict indicators (jj)
- Merged branch detection (git)

#### Design Consistency Checklist

- [ ] Both git and jj use same table structure
- [ ] Same column headers where concepts align
- [ ] Same color scheme (green for current, orange for dirty)
- [ ] Same keyboard shortcuts
- [ ] Same section positioning (bottom of left column)
- [ ] Same context panel format
- [ ] Only terminology differs ("Worktrees" vs "Workspaces")

#### CSS Styling (Shared)

**File: `src/repo_dashboard/app.tcss`**

```css
/* Repository detail screens - shared styles */
#detail-layout {
    height: 100%;
}

#detail-left {
    width: 45%;
    border-right: solid $blue;
}

#detail-right {
    width: 55%;
    padding: 1;
}

.section-title {
    background: $surface0;
    color: $blue;
    padding: 0 1;
    margin-top: 1;
}

.info-panel {
    background: $surface0;
    padding: 1;
    margin: 0 1 1 1;
}

.context-panel {
    background: $surface0;
    padding: 1;
    height: 100%;
    overflow-y: auto;
}

/* VCS-specific table styling */
#branches-table, #special-table, #workspaces-table {
    height: auto;
    max-height: 15;
    margin: 0 1 1 1;
}

/* Current branch/bookmark marker */
DataTable .current-marker {
    color: $green;
}

/* PR indicator */
DataTable .has-pr {
    color: $green;
}

/* Conflict indicator (jj) */
DataTable .conflict {
    color: $peach;
}
```

---

## Phase 4: Batch Maintenance Tasks

### 4.1 Proposed Maintenance Tasks

**High-value, safe operations:**

1. **Fetch All** (`f` in filtered view)
   - git: `git fetch --all --prune`
   - jj: `jj git fetch --all-remotes`
   - Use case: Update remote refs for all selected repos

2. **Prune Remote** (`p` in filtered view)
   - git: `git remote prune origin`
   - jj: Implicit in fetch (no separate prune needed)
   - Use case: Clean up stale remote branch refs

3. **Cleanup Merged Branches** (`c` in filtered view)
   - git: Delete local branches merged into main/master
   - jj: Delete bookmarks that are ancestors of main
   - Use case: Remove branches after PR merge
   - Safety: Confirm before deletion, show preview

4. **Run Command** (`x` in filtered view)
   - Execute arbitrary command across filtered repos in parallel
   - Template variables: `{repo_path}`, `{repo_name}`, `{branch}`
   - Use case: Custom workflows (e.g., `uv sync`, `npm install`, `make test`)
   - Safety: Dry-run preview, confirmation required

**Medium-value (consider for later):**

5. **Update Main Branch** (risky - read-only preferred)
   - git: `git checkout main && git pull`
   - jj: `jj bookmark set main -r main@origin`
   - Safety concern: Could cause conflicts, lose work

6. **Sync Fork** (GitHub-specific)
   - Use `gh` CLI: `gh repo sync`
   - Use case: Update fork from upstream
   - Safety: Read GitHub state first

### 4.2 Implementation: Batch Task Runner

**File: `src/repo_dashboard/batch_tasks.py` (new)**
```python
from dataclasses import dataclass
from typing import Callable
from pathlib import Path
from .vcs_protocol import VCSOperations

@dataclass(frozen=True)
class BatchTaskResult:
    repo_path: Path
    repo_name: str
    success: bool
    message: str
    duration_ms: int

class BatchTaskRunner:
    """Execute tasks across multiple repositories"""

    def __init__(self, repos: list[RepoSummary]):
        self.repos = repos

    async def run_task(
        self,
        task_name: str,
        task_fn: Callable[[VCSOperations, Path], tuple[bool, str]],
    ) -> list[BatchTaskResult]:
        """Run task across all repos in parallel"""
        # Use Textual workers for parallel execution
        results = []
        for repo in self.repos:
            vcs_ops = get_vcs_operations(repo.path)
            start = time.time()
            success, message = task_fn(vcs_ops, repo.path)
            duration = int((time.time() - start) * 1000)

            results.append(BatchTaskResult(
                repo_path=repo.path,
                repo_name=repo.name,
                success=success,
                message=message,
                duration_ms=duration,
            ))

        return results

# Pre-defined tasks
def task_fetch_all(vcs_ops: VCSOperations, repo_path: Path) -> tuple[bool, str]:
    return vcs_ops.fetch_all(repo_path)

def task_prune_remote(vcs_ops: VCSOperations, repo_path: Path) -> tuple[bool, str]:
    return vcs_ops.prune_remote(repo_path)

def task_cleanup_merged(vcs_ops: VCSOperations, repo_path: Path) -> tuple[bool, str]:
    return vcs_ops.cleanup_merged_branches(repo_path)
```

### 4.3 UI: Batch Task Modal

**File: `src/repo_dashboard/modals.py`**
```python
class BatchTaskModal(ModalScreen):
    """Modal for running batch tasks with progress and results"""

    def __init__(self, repos: list[RepoSummary], task_name: str):
        super().__init__()
        self.repos = repos
        self.task_name = task_name

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(f"Running: {self.task_name}", id="task-title")
        yield Static(f"On {len(self.repos)} repositories", id="task-count")
        with Vertical(id="task-progress"):
            yield ProgressBar(total=len(self.repos), id="task-progress-bar")
            yield DataTable(id="task-results")  # Show results as they complete
        yield Footer()

    async def on_mount(self) -> None:
        """Start task execution"""
        results_table = self.query_one("#task-results", DataTable)
        results_table.add_columns("Repo", "Status", "Message", "Time")

        runner = BatchTaskRunner(self.repos)
        # TODO: Execute task with worker and update UI incrementally
```

### 4.4 Keybindings for Batch Tasks

**File: `src/repo_dashboard/app.py`**
```python
BINDINGS = [
    # ... existing bindings

    # Batch tasks (only visible when repos filtered/selected)
    Binding("shift+f", "batch_fetch", "Fetch All", show=True),
    Binding("shift+p", "batch_prune", "Prune Remote", show=True),
    Binding("shift+c", "batch_cleanup", "Cleanup Merged", show=True),
    Binding("shift+x", "batch_command", "Run Command", show=True),
]

def action_batch_fetch(self) -> None:
    """Fetch all filtered repositories"""
    repos = self.filtered_repos  # Use current filter
    if not repos:
        self.notify("No repositories to fetch", severity="warning")
        return

    self.push_screen(BatchTaskModal(repos, "Fetch All"))

# Similar for other batch actions...
```

---

## Phase 5: Testing Strategy

### 5.1 VCS Operation Tests

**File: `tests/test_vcs_git.py`**
```python
def test_git_operations_status(tmp_path):
    """Test GitOperations.get_status()"""
    # Create test git repo
    repo = tmp_path / "test-repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True)

    ops = GitOperations()
    summary = ops.get_status(repo)

    assert summary.vcs_type == "git"
    assert summary.current_branch == "main"
```

**File: `tests/test_vcs_jj.py`**
```python
def test_jj_operations_status(tmp_path):
    """Test JJOperations.get_status()"""
    # Create test jj repo
    repo = tmp_path / "test-repo"
    repo.mkdir()
    subprocess.run(["jj", "init", "--git"], cwd=repo, check=True)

    ops = JJOperations()
    summary = ops.get_status(repo)

    assert summary.vcs_type == "jj"
    # jj default bookmark is often main or master
    assert summary.current_branch in ["main", "master"]
```

### 5.2 Detection Tests

**File: `tests/test_vcs_factory.py`**
```python
def test_detect_git_repo(tmp_path):
    repo = tmp_path / "git-repo"
    repo.mkdir()
    (repo / ".git").mkdir()

    assert detect_vcs_type(repo) == "git"

def test_detect_jj_repo(tmp_path):
    repo = tmp_path / "jj-repo"
    repo.mkdir()
    (repo / ".jj").mkdir()

    assert detect_vcs_type(repo) == "jj"

def test_detect_colocated_prefers_jj(tmp_path):
    """Colocated repos (both .git and .jj) prefer jj"""
    repo = tmp_path / "colocated"
    repo.mkdir()
    (repo / ".git").mkdir()
    (repo / ".jj").mkdir()

    assert detect_vcs_type(repo) == "jj"
```

### 5.3 GitHub CLI Integration Tests

**File: `tests/test_github_ops.py`**
```python
def test_github_env_for_jj_noncolocated(tmp_path):
    """Test GIT_DIR is set for non-colocated jj repos"""
    repo = tmp_path / "jj-repo"
    repo.mkdir()
    (repo / ".jj").mkdir()
    git_store = repo / ".jj" / "repo" / "store" / "git"
    git_store.mkdir(parents=True)

    ops = JJOperations()
    env = get_github_env(ops, repo)

    assert "GIT_DIR" in env
    assert env["GIT_DIR"] == str(git_store)

def test_github_env_for_git(tmp_path):
    """Test GIT_DIR is not modified for git repos"""
    repo = tmp_path / "git-repo"
    repo.mkdir()
    (repo / ".git").mkdir()

    ops = GitOperations()
    env = get_github_env(ops, repo)

    # Should use system GIT_DIR or none
    # (env should match os.environ)
```

### 5.4 Snapshot Tests

Update snapshots to show VCS type indicator:

```bash
uv run pytest tests/test_snapshots.py --snapshot-update
```

---

## Phase 6: Documentation Updates

### 6.1 README.md

Add sections:
- **Supported VCS:** git and jj (both colocated and non-colocated)
- **Requirements:** git CLI and/or jj CLI depending on repos
- **Batch Tasks:** Document new keybindings and what they do

### 6.2 CLAUDE.md

Update architecture section:
- New files: `vcs_protocol.py`, `vcs_git.py`, `vcs_jj.py`, `vcs_factory.py`, `batch_tasks.py`
- VCS abstraction pattern
- jj vs git concept mapping
- Batch task safety considerations

### 6.3 Help Modal

Update help text to include:
- VCS type indicators
- Batch task keybindings
- Safety warnings for write operations

---

## Implementation Order

### Detailed Task Breakdown

#### Stage 1: Foundation (VCS Abstraction) - ~8-10 hours

1. **Create VCS Protocol** (1h)
   - `vcs_protocol.py`: Define `VCSOperations` protocol
   - `VCSType` literal type
   - Method signatures for read/write operations

2. **Refactor Git Operations** (2-3h)
   - Create `vcs_git.py` from existing `git_ops.py`
   - Move functions to `GitOperations` class
   - Add `get_worktrees()` implementation
   - Test existing functionality still works

3. **Create VCS Factory** (1h)
   - `vcs_factory.py`: `detect_vcs_type()`, `get_vcs_operations()`
   - `get_github_env()` for GitHub CLI integration
   - Unit tests for detection logic

4. **Update Models** (1h)
   - Add `vcs_type: VCSType` to `RepoSummary`
   - Add jj-specific optional fields
   - Update `WorktreeInfo` model
   - Ensure backward compatibility

5. **Update Discovery** (1h)
   - Modify `_is_repo_root()` to detect both `.git` and `.jj`
   - Test discovery with mixed repos

6. **Update GitHub Integration** (1-2h)
   - Modify all `github_ops.py` functions to use `get_github_env()`
   - Test with both git and jj repos (mocked)
   - Ensure `GIT_DIR` is set correctly for non-colocated jj

**Checkpoint:** Can detect VCS type, git operations work through abstraction

#### Stage 2: JJ Support - ~6-8 hours

7. **Implement JJ Operations** (4-5h)
   - Create `vcs_jj.py` with `JJOperations` class
   - Implement all protocol methods:
     - `get_status()` - parse `jj status`
     - `get_branches()` - parse `jj bookmark list`
     - `get_commits_ahead_behind()` - parse `jj log`
     - `get_worktrees()` - parse `jj workspace list`
     - `get_modified_files()` - parse `jj status`
     - `get_remote_url()` - parse `jj git remote`
   - Handle colocated vs non-colocated detection
   - Write unit tests with mock jj commands

8. **Write Operations** (2-3h)
   - Implement `fetch_all()` for both git and jj
   - Implement `prune_remote()` for git (no-op for jj)
   - Implement `cleanup_merged_branches()` for both
   - Add error handling and return messages

**Checkpoint:** Both git and jj repos can be queried, operations return data

#### Stage 3: Level 1 UI Update - ~2-3 hours

9. **VCS Indicator** (1-2h)
   - Add icon/badge to Name column in main table
   - Style git vs jj differently (colors)
   - Update breadcrumb to show "X git, Y jj repos"

10. **Test Level 1** (1h)
    - Update snapshot tests
    - Test filtering/sorting with mixed repos
    - Ensure progressive loading works

**Checkpoint:** Main table shows VCS type, all existing features work

#### Stage 4: Level 2 UI (Unified) - ~10-12 hours

11. **Base Screen Class** (3-4h)
    - Create `RepoDetailScreen` in `modals.py`
    - Implement shared layout composition
    - Implement shared keybindings and navigation
    - Add table focus management
    - Create abstract methods for VCS-specific parts

12. **Git Detail Screen** (3-4h)
    - Create `GitRepoDetailScreen` extending base
    - Implement branches table loading
    - Implement stashes section
    - Implement worktrees section (new feature)
    - Implement context panel updates
    - Test with real git repos

13. **JJ Detail Screen** (3-4h)
    - Create `JJRepoDetailScreen` extending base
    - Implement bookmarks table loading
    - Implement conflicts section
    - Implement workspaces section (with visibility logic)
    - Implement context panel updates
    - Test with real jj repos (if available) or mocked

14. **CSS Styling** (1h)
    - Add shared styles for detail screens
    - Ensure Catppuccin theme consistency
    - Test responsiveness

**Checkpoint:** Level 2 detail views work for both git and jj

#### Stage 5: Batch Tasks - ~6-8 hours

15. **Batch Task Runner** (2-3h)
    - Create `batch_tasks.py`
    - Implement `BatchTaskRunner` class
    - Define task functions (`task_fetch_all`, etc.)
    - Handle worker execution and result aggregation

16. **Batch Task UI** (2-3h)
    - Create `BatchTaskModal` in `modals.py`
    - Implement progress bar and results table
    - Handle incremental updates as tasks complete
    - Add error highlighting

17. **Batch Task Actions** (1-2h)
    - Add keybindings to main app
    - Implement `action_batch_fetch()`, etc.
    - Add confirmation dialogs
    - Test with multiple repos

18. **Run Command Feature** (1h - optional)
    - Add command input modal
    - Implement template variable substitution
    - Execute across filtered repos
    - Show aggregated output

**Checkpoint:** Batch operations work, users can fetch/prune/cleanup

#### Stage 6: Testing - ~4-6 hours

19. **Unit Tests** (2-3h)
    - `test_vcs_git.py`: Git operations tests
    - `test_vcs_jj.py`: JJ operations tests (mocked)
    - `test_vcs_factory.py`: Detection and factory tests
    - `test_github_ops.py`: GitHub integration tests

20. **Integration Tests** (1-2h)
    - Test full workflows (discover → display → detail → batch)
    - Test error handling paths
    - Test with edge cases (empty repos, no remotes, etc.)

21. **Snapshot Tests** (1h)
    - Update all snapshots with new UI
    - Verify visual consistency
    - Test both git and jj views if possible

**Checkpoint:** All tests pass, coverage is adequate

#### Stage 7: Documentation - ~2-3 hours

22. **Update README** (1h)
    - Document VCS support (git + jj)
    - Update requirements section
    - Add batch task documentation
    - Update screenshots/demo

23. **Update CLAUDE.md** (1h)
    - Document new architecture
    - Add VCS abstraction section
    - Update file structure
    - Add jj vs git concept mapping

24. **Update Help Modal** (1h)
    - Add VCS indicator explanation
    - Document batch task keybindings
    - Add safety warnings
    - Update keybinding reference

**Checkpoint:** Documentation is complete and accurate

---

### Total Estimated Time

| Stage | Hours | Cumulative |
|-------|-------|------------|
| 1. Foundation | 8-10h | 8-10h |
| 2. JJ Support | 6-8h | 14-18h |
| 3. Level 1 UI | 2-3h | 16-21h |
| 4. Level 2 UI | 10-12h | 26-33h |
| 5. Batch Tasks | 6-8h | 32-41h |
| 6. Testing | 4-6h | 36-47h |
| 7. Documentation | 2-3h | 38-50h |

**Total: ~38-50 hours** (roughly 1-1.5 weeks full-time or 2-3 weeks part-time)

### Risk Mitigation

**High-risk areas:**
1. **JJ command parsing** - jj output format may vary across versions
   - Mitigation: Test with multiple jj versions, add version checks
2. **GitHub CLI with non-colocated jj** - GIT_DIR handling may be fragile
   - Mitigation: Extensive testing, fallback to manual repo path
3. **Unified UI complexity** - Keeping git and jj UIs in sync
   - Mitigation: Strong base class abstraction, shared tests
4. **Batch task safety** - Write operations could cause data loss
   - Mitigation: Confirmation dialogs, clear warnings, dry-run option

**Medium-risk areas:**
1. **Worktree/workspace edge cases** - Many corner cases to handle
   - Mitigation: Graceful degradation, show what we can
2. **Performance with many repos** - Batch operations may be slow
   - Mitigation: Progress feedback, cancelable operations
3. **Test coverage for jj** - Hard to test without jj installed
   - Mitigation: Mock jj commands, add integration test instructions

### Success Criteria

**Must have:**
- ✅ Both git and jj repos are detected and displayed
- ✅ Level 1 (main list) works with mixed repos
- ✅ Level 2 (detail view) shows branches/bookmarks with PR info
- ✅ Worktrees/workspaces are visible and navigable
- ✅ GitHub integration works for both VCS types
- ✅ At least one batch task works (fetch)
- ✅ Tests pass, no regressions

**Should have:**
- ✅ All batch tasks implemented (fetch, prune, cleanup)
- ✅ Conflicts visible for jj repos
- ✅ Stashes visible for git repos
- ✅ Comprehensive error handling
- ✅ Updated documentation

**Nice to have:**
- ⭕ Run custom command feature
- ⭕ Quick actions on worktrees/workspaces
- ⭕ Workspace age/last modified display
- ⭕ Dry-run mode for write operations

---

## Safety Considerations

### Read-Only by Default
- All existing functionality remains read-only
- Write operations require explicit user action (keybinding)
- Confirmation modals for destructive operations

### Batch Task Safety
- **Preview before execution:** Show which repos will be affected
- **Confirmation required:** User must confirm before batch write
- **Progress feedback:** Show results incrementally, highlight failures
- **Rollback not possible:** Warn that operations are not atomic
- **Filter awareness:** Only operate on currently filtered repos (explicit scope)

### jj-Specific Considerations
- Non-colocated repos require GIT_DIR for gh CLI (handled)
- jj operations are generally safer (immutable history)
- Some git concepts don't map to jj (stash, staged changes)
- jj has more powerful undo capabilities (mention in docs)

---

## Future Enhancements (Out of Scope for This Phase)

- YAML configuration (unlikely needed with auto-discovery)
- Full mani-like sync (clone missing repos)
- Interactive command builder with template system
- Bulk PR operations (merge, close, update)
- Git hooks integration
- Custom task definitions in config
- Task history/logging
- Dry-run mode for all write operations
- Integration with other VCS (hg, fossil, etc.)

---

## Open Questions & Decisions

### Resolved

1. **VCS indicator placement:** ✅ Icon/badge in Name column to save space
2. **Batch task confirmation:** ✅ Modal with preview and confirm button
3. **Parallel execution limit:** ✅ Use Textual worker pool (default: 40 threads via AnyIO)
4. **Error handling:** ✅ Continue on error, show all results, highlight failures
5. **Command execution output:** ✅ Merged stdout/stderr in scrollable text area
6. **UI architecture:** ✅ Unified base class with VCS-specific implementations
7. **Code sharing:** ✅ Maximize sharing via base class, mixins, and shared utilities
8. **Workspace visibility:** ✅ Show for git (always), hide for jj if single workspace

### Remaining

1. **jj change history depth:**
   - **Recommendation:** Default 5 (not 10) in context panel to match git commits
   - Configurable via future config file if needed

2. **Workspace/worktree actions:**
   - **For later:** Quick actions (open, delete, jump to)
   - **Phase 1:** Read-only visibility only
   - **Phase 2+:** Add write operations if user demand exists

3. **Empty state messaging:**
   - **Git worktrees:** Show hint "No worktrees. Use `git worktree add`"
   - **JJ workspaces:** Hide section entirely if single workspace
   - **Alternative:** Show collapsed section with expand option

4. **Conflict display (jj):**
   - **Question:** Show all conflicts or only in current bookmark?
   - **Recommendation:** All conflicts across repo (surfacing hidden issues)
   - **Alternative:** Filter to current bookmark only

5. **Detached HEAD handling (git):**
   - **Question:** How prominently to warn about detached HEAD?
   - **Recommendation:** Yellow warning icon + explanation in context panel
   - **Rationale:** It's unusual but not necessarily wrong (common during rebase)

6. **Worktree age display:**
   - **Question:** Show relative time ("6 months ago") or absolute date?
   - **Recommendation:** Relative time, with tooltip showing absolute
   - **Implementation:** Use existing `modified_date` pattern

7. **Cross-workspace navigation:**
   - **For later:** Quick jump between worktrees/workspaces
   - **Complexity:** Would require terminal integration or file browser
   - **Phase 1:** Just display information
