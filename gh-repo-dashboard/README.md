# gh-repo-dashboard

A TUI dashboard for managing multiple git and jj repositories. Inspired by k9s.

## Installation

```bash
gh extension install kyleking/gh-repo-dashboard
```

Or build from source:

```bash
go build -o gh-repo-dashboard .
```

## Usage

```bash
# Scan default directory (~/Developer)
gh repo-dashboard

# Scan specific directories
gh repo-dashboard ~/projects ~/work

# Limit scan depth
gh repo-dashboard -depth 2 ~/Developer
```

## Features

- Progressive loading of repository status
- Filter by: all, dirty, ahead, behind, has PR, has stash
- Sort by: name, modified, status, branch
- Fuzzy search
- GitHub PR integration (requires gh CLI)
- Batch operations: fetch all, prune remote, cleanup merged branches
- Supports both git and jj (Jujutsu) repositories

## Keybindings

### Navigation

| Key | Action |
|-----|--------|
| `j` / `down` | Move down |
| `k` / `up` | Move up |
| `g` | Go to top |
| `G` | Go to bottom |
| `enter` / `space` | Select / drill down |
| `esc` / `backspace` | Go back |

### Views

| Key | Action |
|-----|--------|
| `?` | Help |
| `/` | Search |
| `f` | Filter modal |
| `s` | Sort modal |
| `R` | Reverse sort |
| `r` | Refresh |

### Detail View

| Key | Action |
|-----|--------|
| `tab` | Next tab |
| `h` / `left` | Previous tab |
| `l` / `right` | Next tab |

### Batch Operations

| Key | Action |
|-----|--------|
| `F` | Fetch all (filtered repos) |
| `P` | Prune remote (filtered repos) |
| `C` | Cleanup merged branches |

## Filter Modes

- **ALL** - Show all repositories
- **DIRTY** - Uncommitted changes or unpushed commits
- **AHEAD** - Commits ahead of tracking branch
- **BEHIND** - Commits behind tracking branch
- **HAS_PR** - Has associated GitHub PR
- **HAS_STASH** - Has stashed changes

## Requirements

- git CLI (for git repositories)
- jj CLI (for Jujutsu repositories, optional)
- gh CLI (for GitHub PR features, optional)

## Theme

Uses Catppuccin Macchiato color scheme.

## License

MIT
