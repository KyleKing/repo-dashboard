# Refresh Feature Documentation

## Overview

Added comprehensive refresh functionality that works from any view in the application, clearing all cached data and reloading the current context.

## Keybindings

- `r` - Refresh (works from any view)
- `Ctrl+R` - Refresh (alternative keybinding)

## Behavior by View Mode

### From Repo List View
- Clears all caches (PRs, branches, commits, workflows)
- Clears summaries and PR count maps
- Rediscovers all repositories
- Reloads all repository data
- Sets loading state to true

### From Repo Detail View
- Clears all caches
- Reloads branches, stashes, worktrees, and PRs for the current repo
- Reloads PR count if upstream is configured
- Maintains current tab and cursor position

### From Branch Detail View
- Clears all caches
- Reloads branch details (commits, PR info, workflow status)
- Maintains current branch selection

### From PR Detail View
- Clears all caches
- Reloads full PR details (metadata, assignees, reviewers, etc.)
- Maintains current PR selection

### From Other Views
- Filter/Sort/Help/Batch Progress: Refresh works but returns to the underlying view mode's refresh behavior

## User Feedback

When refresh completes, a green status message "Data refreshed" appears at the bottom of the screen for 3 seconds.

## Implementation Details

### Files Modified

1. **internal/app/keymap.go**
   - Updated `Refresh` keybinding to accept both `r` and `ctrl+r`

2. **internal/app/messages.go**
   - Added `RefreshCompleteMsg` type for refresh completion signaling

3. **internal/app/update.go**
   - Added `handleRefresh()` method with context-aware refresh logic
   - Added cache import
   - Integrated refresh handling into all view mode key handlers:
     - `handleKey()` (repo list)
     - `handleDetailKey()` (repo detail)
     - `handleBranchDetailKey()` (branch detail)
     - `handlePRDetailKey()` (PR detail)
   - Added `RefreshCompleteMsg` handler with status message

4. **internal/app/view.go**
   - Updated help text to show `r/ctrl+r` keybinding

5. **internal/app/refresh_test.go** (new file)
   - 9 comprehensive test functions covering:
     - Refresh from each view mode
     - Keybinding verification
     - Cache clearing
     - Status message display
     - View mode preservation
     - Empty state handling

### Cache Clearing

The refresh clears all TTL caches:
- `PRCache` - GitHub PR information
- `PRListCache` - PR lists per repository
- `PRDetailCache` - Detailed PR information
- `BranchCache` - Branch lists
- `CommitCache` - Commit history
- `WorkflowCache` - GitHub workflow run status

## Testing

### Test Coverage

```
TestRefreshFromRepoList                  - Verifies refresh from main list
TestRefreshFromRepoDetail                - Verifies refresh from detail view
TestRefreshFromBranchDetail              - Verifies refresh from branch view
TestRefreshFromPRDetail                  - Verifies refresh from PR view
TestRefreshCompleteMessage               - Verifies status message
TestRefreshKeybindings                   - Verifies both keybindings work
TestRefreshClearsCache                   - Verifies cache is cleared
TestRefreshFromEmptyState                - Verifies refresh with no data
TestRefreshPreservesViewMode             - Verifies view mode maintained
```

All tests pass: **9/9**

### Usage Example

```bash
# Build the application
go build -o gh-repo-dashboard .

# Run it
./gh-repo-dashboard ~/Developer

# In the TUI:
# 1. Navigate to any view (list, detail, branch, PR)
# 2. Press 'r' or Ctrl+R to refresh
# 3. See "Data refreshed" status message
# 4. All data is reloaded with fresh API calls
```

## Benefits

1. **Works Everywhere** - No matter which view you're in, refresh always works
2. **Clears Stale Data** - All caches are cleared, ensuring fresh data
3. **Context-Aware** - Only reloads data relevant to current view
4. **User Feedback** - Clear visual indication that refresh happened
5. **Efficient** - Only reloads what's needed for the current view
6. **Keyboard Shortcuts** - Two options: 'r' for quick access, Ctrl+R for muscle memory

## Common Use Cases

### Scenario 1: Stale PR Information
- Navigate to PR detail view
- Press `r` to refresh
- PR metadata, review status, and checks are reloaded

### Scenario 2: New PRs Created Outside App
- In repo list or repo detail view
- Press `Ctrl+R` to refresh
- New PR counts and PR lists are fetched

### Scenario 3: Branch Updates
- Viewing branch detail
- Press `r` after pushing commits
- Commits, ahead/behind counts, and PR status are updated

### Scenario 4: Cache Timeout Issues
- From any view
- Press `r` to force immediate cache clear and reload
- No need to wait for TTL expiration
