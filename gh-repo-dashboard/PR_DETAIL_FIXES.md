# PR Detail View Fixes

## Issues Fixed

### Issue 1: PR Detail View Shows Zero/Empty Data
**Problem:** When navigating to a PR detail view, the number appeared as zero and no data was displayed.

**Root Cause:** The `renderPRDetail()` function immediately tried to render `m.prDetail.Number` before the asynchronous `loadPRDetailCmd` completed. Since `prDetail` is initialized as an empty struct with `Number: 0`, it would display "PR #0" with no data.

**Solution:**
1. Added loading state detection in `renderPRDetail()`
2. When `m.prDetail.Number == 0`, display a loading message instead
3. Clear `prDetail` when navigating to a new PR to ensure loading state shows
4. Data appears once `PRDetailLoadedMsg` is processed

**Files Modified:**
- `internal/app/view.go` - Added loading state check in renderPRDetail()
- `internal/app/update.go` - Clear prDetail when entering PR detail view

### Issue 2: Refresh Doesn't Clear Downstream Views
**Problem:** When refreshing from repo list or repo detail, the downstream detail views (branch detail, PR detail) weren't cleared, leading to stale cached data.

**Root Cause:** The `handleRefresh()` function only cleared data for the current view level, not cascading downstream.

**Solution:**
Enhanced `handleRefresh()` to clear all downstream data:

**From Repo List:**
- Clears: summaries, prCount, branches, stashes, worktrees, prs, branchDetail, prDetail
- Effect: Complete fresh start

**From Repo Detail:**
- Clears: branches, stashes, worktrees, prs, branchDetail, prDetail
- Effect: All detail views invalidated

**From Branch Detail:**
- Clears: branchDetail
- Effect: Current branch detail refreshed

**From PR Detail:**
- Clears: prDetail
- Effect: Current PR detail refreshed

**Files Modified:**
- `internal/app/update.go` - Enhanced handleRefresh() with cascading clear

## Technical Details

### Loading State Implementation

```go
func (m Model) renderPRDetail() string {
    // Check if PR detail has been loaded
    if m.prDetail.Number == 0 {
        // Show loading state
        return loadingView()
    }

    // Render full PR detail
    // ...
}
```

### Clear on Navigation

```go
case key.Matches(msg, m.keys.Enter):
    if m.detailTab == DetailTabPRs && m.detailCursor < len(m.prs) {
        m.selectedPR = m.prs[m.detailCursor]
        m.prDetail = models.PRDetail{} // Clear previous detail
        m.viewMode = ViewModePRDetail
        return m, loadPRDetailCmd(m.selectedRepo, m.selectedPR.Number)
    }
```

### Cascading Refresh

```go
func (m Model) handleRefresh() (tea.Model, tea.Cmd) {
    // Clear cache
    cache.ClearAll()

    switch m.viewMode {
    case ViewModeRepoList:
        // Clear EVERYTHING
        m.summaries = make(map[string]models.RepoSummary)
        m.branches = nil
        m.prs = nil
        m.branchDetail = models.BranchDetail{}
        m.prDetail = models.PRDetail{}
        // ...

    case ViewModeRepoDetail:
        // Clear all detail views
        m.branches = nil
        m.prs = nil
        m.branchDetail = models.BranchDetail{}
        m.prDetail = models.PRDetail{}
        // ...
    }
}
```

## Test Coverage

### New Tests Added

**PR Detail Loading State:**
```go
TestPRDetailLoadingState          - Verifies loading message when Number == 0
TestPRDetailClearedOnNavigation   - Verifies detail cleared when entering new PR
```

**Refresh Downstream Clearing:**
```go
TestRefreshClearsDownstreamFromRepoList   - Verifies all downstream data cleared
TestRefreshClearsDownstreamFromRepoDetail - Verifies detail views cleared
TestRefreshClearsBranchDetail             - Verifies branch detail cleared
TestRefreshClearsPRDetail                 - Verifies PR detail cleared
```

**Test Results:**
```
Total new tests: 6
All tests pass: 48/48 (app package)
Build: SUCCESS
```

## User Experience Improvements

### Before Fix:
1. Navigate to PR tab → Press Enter
2. See "PR #0" with no data
3. Confused about what went wrong
4. Refresh doesn't help if parent view still has cached data

### After Fix:
1. Navigate to PR tab → Press Enter
2. See "Loading PR details..." message
3. Data appears when loaded (typically <1 second)
4. Refresh from any level clears all downstream stale data

## Edge Cases Handled

1. **Navigating Between Different PRs:** Previous PR detail is cleared before loading new one
2. **Refresh from Parent View:** All child views are invalidated
3. **Empty/Zero PR Number:** Loading state shows instead of trying to render invalid data
4. **Slow Network:** Loading message remains until data arrives
5. **Error Loading:** Message handler deals with error, loading state clears

## Related Files

### Core Implementation:
- `internal/app/view.go` - Loading state rendering
- `internal/app/update.go` - Navigation clearing, refresh cascading

### Tests:
- `internal/app/pr_test.go` - PR detail tests (741 lines)
- `internal/app/refresh_test.go` - Refresh tests (306 lines)

### Models:
- `internal/models/pr.go` - PRInfo, PRDetail structs
- `internal/app/messages.go` - PRDetailLoadedMsg

## Performance Impact

- **Minimal:** Clearing structs is O(1), only affects current session
- **Network:** Same number of API calls, just properly sequenced
- **UX:** Better - clear loading indicators instead of confusing empty states

## Future Considerations

1. Could add spinner/animation to loading state
2. Could cache PR details longer (currently 5 minutes)
3. Could preload next/prev PR when viewing current one
4. Could show partial data while loading (if available from list)
