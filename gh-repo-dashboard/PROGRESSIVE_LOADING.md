# Progressive Loading for PR Details

## Problem

Loading PR details was perceived as slow because:
1. GitHub API call (`gh pr view`) takes ~1+ seconds
2. User saw "Loading PR details..." blank screen during this time
3. No visual feedback that anything was happening

## Solution: Progressive Loading

Implemented two-phase loading strategy:

### Phase 1: Immediate (0ms)
Show basic PR information already available from the PR list view:
- PR number
- Title
- State (OPEN/MERGED/CLOSED/DRAFT)
- URL
- Head and base branches
- Review decision

### Phase 2: Background (~1s)
Load additional details via GitHub API:
- Author
- Assignees
- Reviewers
- Description/body
- Code changes (additions/deletions)
- Comment count
- Created/updated timestamps

## Implementation Details

### 1. Data Structure Optimization

`PRDetail` embeds `PRInfo`, allowing us to reuse list data:

```go
type PRDetail struct {
    PRInfo  // Embedded - reused from list
    Body       string    // Loaded async
    Author     string    // Loaded async
    Assignees  []string  // Loaded async
    Reviewers  []string  // Loaded async
    // ... other async fields
}
```

### 2. Navigation Handler

When entering PR detail view, immediately populate with list data:

```go
case key.Matches(msg, m.keys.Enter):
    if m.detailTab == DetailTabPRs && m.detailCursor < len(m.prs) {
        m.selectedPR = m.prs[m.detailCursor]

        // Progressive loading: Show basic info immediately
        m.prDetail = models.PRDetail{
            PRInfo: m.selectedPR, // Already loaded from list
        }

        m.viewMode = ViewModePRDetail
        // Start async load of full details
        return m, loadPRDetailCmd(m.selectedRepo, m.selectedPR.Number)
    }
```

### 3. View Rendering

Detect loading state and show appropriate UI:

```go
func (m Model) renderPRDetail() string {
    // Check if fully loaded (Author is populated)
    isFullyLoaded := m.prDetail.Author != ""

    if !isFullyLoaded {
        // Show loading indicator
        loadingIndicator := styles.Italic.Render(" (loading details...)")
        b.WriteString(loadingIndicator)
    }

    // Always show basic info (from list)
    b.WriteString("Title: " + m.prDetail.Title)
    b.WriteString("Branch: " + m.prDetail.HeadRef + " → " + m.prDetail.BaseRef)
    b.WriteString("State: " + m.prDetail.State)

    // Only show detailed stats if fully loaded
    if isFullyLoaded {
        b.WriteString("Author: " + m.prDetail.Author)
        b.WriteString("Changes: +" + m.prDetail.Additions + " -" + m.prDetail.Deletions)
        // ... other details
    }
}
```

### 4. Loading Detection

Use `Author` field as loading indicator:
- Empty `Author` = partial data (from list)
- Populated `Author` = full data (from API)

This works because:
- PR list doesn't include author
- PR detail API always includes author
- Author is required metadata for any PR

## Performance Comparison

### Before (Blocking Load):
```
User presses Enter
↓ 0ms
Show "Loading PR details..."
↓ 1200ms (wait for API)
Show full PR detail
```
**Perceived wait: 1200ms of blank screen**

### After (Progressive Load):
```
User presses Enter
↓ 0ms
Show basic PR info (title, branches, state)
Show "(loading details...)" indicator
↓ 1200ms (API call in background)
Update with full details (author, stats, body)
Remove loading indicator
```
**Perceived wait: 0ms for basic info, 1200ms for extras**

## Test Coverage

### New Tests (3):

```go
TestPRDetailClearedOnNavigation    - Verifies basic info populated immediately
TestPRDetailProgressiveLoading     - Verifies two-phase loading behavior
TestPRDetailProgressiveView        - Verifies UI shows partial then full data
```

**Results:**
- All tests pass
- Total app tests: 51/51
- Build: SUCCESS

## User Experience Impact

### Immediate Feedback
User sees content within milliseconds instead of blank loading screen

### Visual Progress
"(loading details...)" indicator shows work is happening

### Usable Immediately
Can read title, see state, identify branches before full details load

### Graceful Enhancement
Additional details appear seamlessly without layout shift

## Files Modified

1. **internal/app/update.go**
   - Updated Enter handler to populate prDetail with list data
   - Changed from clearing to pre-populating

2. **internal/app/view.go**
   - Added loading state detection (Author != "")
   - Show basic info always, detailed info when loaded
   - Added loading indicator

3. **internal/app/pr_test.go**
   - Added progressive loading tests
   - Updated navigation test expectations

## API Performance Analysis

Actual `gh pr view` performance:
```bash
$ time gh pr view 123 --json number,title,state,...
real    0m1.152s
```

Bottleneck is GitHub API network request (~1s), not local processing.

### Optimization Opportunities Considered:

1. **Reduce requested fields** ❌
   - All fields are displayed in UI
   - Removing any would reduce functionality

2. **Parallel requests** ❌
   - Can't parallelize single PR detail fetch
   - Already using cache for repeated views

3. **Progressive loading** ✅ IMPLEMENTED
   - Show immediate partial data
   - Load full data in background
   - Best UX improvement possible

4. **Increase cache TTL** ⚠️
   - Current: 5 minutes
   - Could increase, but risks stale data
   - User can manually refresh (r/Ctrl+R)

## Future Enhancements

1. **Prefetch adjacent PRs**: When viewing PR #5, preload #4 and #6
2. **Persistent cache**: Save to disk for instant load on restart
3. **Diff preview**: Add code diff visualization (would require additional API call)
4. **Comment preview**: Show recent comments (would require additional API call)

## Related Documentation

- PR_DETAIL_FIXES.md - Original loading state implementation
- REFRESH_FEATURE.md - Cache invalidation and refresh
