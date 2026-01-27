# Bug Fix: PR Detail Error Handling

## Bug Description

When opening a PR detail view, users would initially see details but then they would disappear and be replaced with "Loading PR details..." which would never complete.

## Root Cause

The bug occurred in the `PRDetailLoadedMsg` message handler (internal/app/update.go lines 139-143).

### The Problem Flow

1. User presses Enter on a PR in the list
2. Handler populates `m.prDetail` with basic info from the PR list (Number, Title, State, etc.)
3. Handler calls `loadPRDetailCmd` to fetch full details from GitHub API
4. View renders → sees `prDetail.Number != 0` → shows basic info with "(loading details...)" indicator
5. **If API call fails:**
   - `loadPRDetailCmd` returns `PRDetailLoadedMsg` with:
     - `Error` field set
     - `Detail` field as empty struct (Number = 0)
   - Handler blindly executes: `m.prDetail = msg.Detail`
   - This overwrites the basic info with an empty struct
6. View re-renders → sees `prDetail.Number == 0` → shows "Loading PR details..."
7. Never completes because the load already failed

### Original Code

```go
case PRDetailLoadedMsg:
    if msg.Path == m.selectedRepo && msg.PRNumber == m.selectedPR.Number {
        m.prDetail = msg.Detail  // BUG: Overwrites with empty struct on error
    }
    return m, nil
```

## Fix

Check for errors before updating `prDetail`. If there's an error:
1. Preserve the basic info that was already populated
2. Show an error status message to inform the user

### Fixed Code

```go
case PRDetailLoadedMsg:
    if msg.Path == m.selectedRepo && msg.PRNumber == m.selectedPR.Number {
        if msg.Error != nil {
            // Don't clear basic info on error - preserve what we already have
            // Show error status message
            m.statusMessage = fmt.Sprintf("Failed to load PR details: %v", msg.Error)
            return m, clearStatusAfterDelay()
        }
        m.prDetail = msg.Detail
    }
    return m, nil
```

## Test Coverage

Added `TestPRDetailErrorPreservesBasicInfo` in internal/app/pr_test.go:

```go
func TestPRDetailErrorPreservesBasicInfo(t *testing.T) {
    m := New(nil, 1)
    m.viewMode = ViewModePRDetail
    m.selectedRepo = "/test/repo"
    m.selectedPR = models.PRInfo{
        Number:  456,
        Title:   "Feature PR",
        State:   "OPEN",
        HeadRef: "feature",
        BaseRef: "main",
    }
    m.summaries["/test/repo"] = models.RepoSummary{Path: "/test/repo"}

    // Populate prDetail with basic info (simulating progressive loading)
    m.prDetail = models.PRDetail{
        PRInfo: m.selectedPR,
    }

    // Simulate error response from loadPRDetailCmd
    errorMsg := PRDetailLoadedMsg{
        Path:     "/test/repo",
        PRNumber: 456,
        Detail:   models.PRDetail{}, // Empty detail due to error
        Error:    fmt.Errorf("failed to load PR details"),
    }

    updatedModel, _ := m.Update(errorMsg)
    m = updatedModel.(Model)

    // Verify basic info is preserved after error
    if m.prDetail.Number != 456 {
        t.Errorf("expected PR #456 to be preserved after error, got #%d", m.prDetail.Number)
    }
    if m.prDetail.Title != "Feature PR" {
        t.Errorf("expected title to be preserved after error, got %q", m.prDetail.Title)
    }
}
```

## User Experience Improvement

### Before Fix
1. User opens PR detail → sees basic info briefly
2. Screen clears → shows "Loading PR details..."
3. Never completes (stuck loading forever)
4. User has no idea what happened

### After Fix
1. User opens PR detail → sees basic info immediately
2. If API fails:
   - Basic info remains visible
   - Error message appears at bottom: "Failed to load PR details: [error details]"
   - Error message auto-dismisses after 3 seconds
3. User can still see the basic PR information (title, branches, state)
4. User understands that loading failed but has useful context

## Files Modified

1. **internal/app/update.go** (lines 139-146)
   - Added error check in `PRDetailLoadedMsg` handler
   - Preserve basic info on error
   - Show status message on error

2. **internal/app/pr_test.go**
   - Added `fmt` import (line 4)
   - Added `TestPRDetailErrorPreservesBasicInfo` test (lines 743-789)

## Test Results

- New test: **PASS**
- All app tests (80 tests): **PASS**
- Full test suite: **PASS**
- Build: **SUCCESS**

## Related Issues

This bug was likely triggered by:
- Network failures
- GitHub API rate limiting
- Invalid PR numbers
- Missing `gh` CLI tool
- Authentication issues with GitHub CLI

All of these scenarios would cause `loadPRDetailCmd` to fail and return an error, which would then clear the basic PR info that was already displayed.

## Prevention

To prevent similar bugs in the future:
1. Always check error fields before overwriting existing data
2. Test error paths, not just happy paths
3. Preserve user-visible data when background operations fail
4. Provide clear error messages when operations fail
