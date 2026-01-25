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

## Planned Features

### Oh-My-Posh Integration

CLI command to expose current PR information for shell prompt integration:

```sh
# Example usage in oh-my-posh prompt segment
reda pr-info --format=json
```

**Features:**
- Read PR name/number from cached data for current repository
- Fast response time (cache-only, no API calls)
- JSON output for easy parsing by prompt engines
- Display PR status, title, and checks in shell prompt
- Configurable output format (json, text, template)

**Use case:** Show current PR context directly in your shell prompt without slowing down prompt rendering. Uses the existing TTL cache infrastructure to avoid GitHub API rate limits.

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

## Alternatives

### Multi-Repository TUIs

**[Git-Scope](https://github.com/Bharath-code/git-scope)** - The most similar tool to repo-dashboard, built with Bubble Tea (Go) instead of Textual (Python).

**Comparison with Git-Scope:**

| Feature | repo-dashboard | Git-Scope |
|---------|---------------|-----------|
| **Language** | Python (Textual) | Go (Bubble Tea) |
| **VCS Support** | Git + Jujutsu (jj) | Git only |
| **Startup Time** | ~100-500ms | ~10ms (cached) |
| **GitHub Integration** | PR details, checks, status via gh CLI | Contribution graphs |
| **Filtering** | 6 modes (dirty, ahead, behind, has_pr, has_stash, all) | Dirty filter + pagination |
| **Batch Operations** | Fetch all, prune remote, cleanup merged branches | None |
| **Search** | Fuzzy search with 0.6 similarity threshold | Fuzzy search by name/path/branch |
| **Additional Features** | Worktrees/workspaces, stash tracking, PR opening | Editor launch (VSCode/Vim/etc), disk usage, timeline view |
| **Workspace Switching** | Via CLI arguments | In-app with `w` key |
| **Theme** | Catppuccin (dark/light) | GitHub-style |

**Choose Git-Scope if you:**
- Prefer faster startup times (Go performance)
- Need editor integration (direct launch to VSCode, Neovim, etc.)
- Want contribution graphs and timeline views
- Work exclusively with Git repositories

**Choose repo-dashboard if you:**
- Use Jujutsu (jj) or mixed Git/jj workflows
- Need GitHub PR integration and status checks
- Want batch maintenance operations (fetch, prune, cleanup)
- Prefer worktree/workspace management
- Work with stashes regularly

### Other Multi-Repository Tools

- **[Gita](https://github.com/nosarthur/gita)** - CLI tool to manage multiple git repositories with custom groups and batch operations
- **[gitbatch](https://github.com/isacikgoz/gitbatch)** - Manage your git repositories in one place with interactive TUI
- **[mgitstatus](https://github.com/fboender/multi-git-status)** - Show uncommitted, untracked, and unpushed changes for multiple repos
- **[mu-repo](https://github.com/fabioz/mu-repo)** - Tool to help in dealing with multiple git repositories
- **[RepoBar](https://github.com/steipete/RepoBar)** - macOS menu bar app for monitoring GitHub repositories with CI status, activity preview, and local git integration
- **[Mani](https://github.com/alajmo/mani)** - Go-based CLI with YAML configuration, built-in TUI, batch operations, and parallel command execution across repos

### DIY Alternative: Bash + gh CLI

You can achieve similar functionality using bash and the GitHub CLI:

```bash
#!/bin/bash
# Example script showing repo status (similar to mani/repo-dashboard output)

for repo in ~/Developer/*/; do
  cd "$repo" || continue

  # Skip non-git repos
  [[ ! -d .git ]] && continue

  # Get basic git info
  name=$(basename "$repo")
  branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "?")

  # Ahead/behind counts
  upstream=$(git rev-parse --abbrev-ref --symbolic-full-name @{u} 2>/dev/null)
  if [[ -n "$upstream" ]]; then
    ahead=$(git rev-list --count "$upstream..HEAD" 2>/dev/null || echo "0")
    behind=$(git rev-list --count "HEAD..$upstream" 2>/dev/null || echo "0")
  else
    ahead="0"
    behind="0"
  fi

  # Status counts (staged, unstaged, untracked)
  staged=$(git diff --cached --numstat 2>/dev/null | wc -l | tr -d ' ')
  unstaged=$(git diff --numstat 2>/dev/null | wc -l | tr -d ' ')
  untracked=$(git ls-files --others --exclude-standard 2>/dev/null | wc -l | tr -d ' ')

  # PR info (requires gh CLI)
  pr_info=$(gh pr view --json number,title 2>/dev/null | jq -r '"\(.number): \(.title)"' 2>/dev/null || echo "—")

  # Last modified
  last_modified=$(git log -1 --format=%ar 2>/dev/null || echo "?")

  # Output
  printf "%-20s %-15s ↑%-2s ↓%-2s +%-2s *%-2s ?%-2s %-40s %s\n" \
    "$name" "$branch" "$ahead" "$behind" "$staged" "$unstaged" "$untracked" \
    "${pr_info:0:40}" "$last_modified"
done
```

**Output example:**
```
repo-dashboard       main            ↑0  ↓0  +2  *1  ?0  123: Add feature X                       2 hours ago
my-project           develop         ↑3  ↓1  +0  *5  ?2  —                                        1 day ago
another-repo         feat/new-ui     ↑1  ↓0  +1  *0  ?0  456: Redesign UI components              3 days ago
```

### Single-Repository TUIs

Terminal UIs focused on managing individual repositories (different use case):

- **[lazygit](https://github.com/jesseduffield/lazygit)** - Simple terminal UI for git commands with keyboard-driven interface and wide feature coverage
- **[GitUI](https://github.com/extrawurst/gitui)** - Blazing fast terminal UI for git written in Rust
- **[Gitu](https://github.com/altsem/gitu)** - TUI Git client inspired by Magit
- **[Neogit](https://github.com/NeogitOrg/neogit)** - Magit for Neovim
