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
- `r` - Refresh all data
- `q` - Quit
- `?` - Show help

## Features

- Progressive loading - data loads as it becomes available
- TTL caching for PR information
- Git worktree detection
- Stash tracking
- Breadcrumb navigation
- Catppuccin themes (dark/light)
