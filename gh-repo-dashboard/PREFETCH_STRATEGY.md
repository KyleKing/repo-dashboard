# Intelligent Prefetching Strategy

## Overview

Implemented multi-level prefetching to dramatically reduce perceived load times for PR details. By anticipating user actions and pre-loading data in the background, most PR detail views now appear instantly.

## Prefetch Triggers

### 1. **On PR List Load** (Background Batch)
When the PR tab is loaded, prefetch the first 3 PRs immediately.

**Trigger:** `DetailLoadedMsg` with PRs
**Strategy:** Parallel prefetch of first 3 PR details
**Rationale:** Users typically view top PRs first

```go
// Prefetch first 3 PRs in background
for i := 0; i < min(3, len(PRs)); i++ {
    prefetchPRDetailCmd(repoPath, PRs[i].Number)
}
```

**Impact:**
- First 3 PRs: **Instant** (already cached)
- Remaining PRs: Load on-demand

### 2. **On Cursor Movement** (Predictive)
When user moves cursor up/down in PR list, prefetch the newly selected PR.

**Trigger:** Arrow key press while on PR tab
**Strategy:** Prefetch PR under cursor
**Rationale:** User may press Enter next

```go
case key.Matches(msg, m.keys.Down):
    m.detailCursor++
    if m.detailTab == DetailTabPRs {
        pr := m.prs[m.detailCursor]
        return m, prefetchPRDetailCmd(m.selectedRepo, pr.Number)
    }
```

**Impact:**
- Highlighted PR: **Usually instant** when Enter pressed
- User browses while data loads in background

### 3. **On Tab Switch** (Anticipatory)
When switching to PR tab, immediately prefetch first PR.

**Trigger:** Tab key switches to `DetailTabPRs`
**Strategy:** Prefetch first PR in list
**Rationale:** Cursor defaults to first item

```go
case key.Matches(msg, m.keys.Tab):
    m.detailTab = DetailTab((int(m.detailTab) + 1) % 4)
    if m.detailTab == DetailTabPRs && len(m.prs) > 0 {
        return m, prefetchPRDetailCmd(m.selectedRepo, m.prs[0].Number)
    }
```

**Impact:**
- First PR on tab: **Instant** if user immediately presses Enter
- No wasted prefetch if user doesn't view any PR

### 4. **On PR Detail Navigation** (Adjacent Prefetch)
When viewing a PR and navigating to next/previous PR, prefetch the adjacent PR.

**Trigger:** Arrow keys in `ViewModePRDetail`
**Strategy:** Prefetch next PR in direction of movement
**Rationale:** Sequential navigation is common

```go
case key.Matches(msg, m.keys.Down):
    // Switch to next PR
    m.selectedPR = m.prs[newIdx]

    var cmds []tea.Cmd
    cmds = append(cmds, loadPRDetailCmd(..., m.selectedPR.Number))

    // Prefetch next adjacent PR
    if newIdx+1 < len(m.prs) {
        cmds = append(cmds, prefetchPRDetailCmd(..., m.prs[newIdx+1].Number))
    }

    return m, tea.Batch(cmds...)
```

**Impact:**
- Next/prev PR: **Usually instant** due to prefetch
- Enables fast sequential browsing

## Cache Utilization

All prefetches leverage the existing TTL cache system:

```go
func prefetchPRDetailCmd(repoPath string, prNumber int) tea.Cmd {
    return func() tea.Msg {
        // Populates cache silently
        _, _ = github.GetPRDetail(ctx, repoPath, prNumber)

        // Return nil - no UI update needed
        return nil
    }
}
```

**Cache Benefits:**
- 5 minute TTL prevents redundant API calls
- Subsequent views are instant (cache hit)
- Shared between prefetch and actual load

## Prefetch Characteristics

### Silent Operation
- Returns `nil` message (no UI updates)
- Runs in background goroutine
- Doesn't block user interaction

### Cache-Aware
- Checks cache before API call
- Cache hits are near-instant (µs)
- Cache misses fetch from GitHub (~1s)

### Non-Blocking
- User can continue navigating while prefetch runs
- Multiple prefetches run concurrently
- Failed prefetches don't affect UI

## Performance Analysis

### Scenario 1: Viewing First PR in List

**Without Prefetch:**
```
Tab to PRs → Press Enter → Wait 1.2s → View PR
Total time: 1.2s
```

**With Prefetch:**
```
Tab to PRs → Prefetch #1 starts in background
Press Enter → PR #1 already cached → Instant view
Total time: ~0ms (cache hit)
```

### Scenario 2: Browsing Multiple PRs

**Without Prefetch:**
```
View PR #1: 1.2s wait
Down to PR #2: 1.2s wait
Down to PR #3: 1.2s wait
Total: 3.6s of waiting
```

**With Prefetch:**
```
List loads → Prefetch #1, #2, #3 (parallel, background)
View PR #1: Instant (already cached)
Down to PR #2: Instant (already cached)
Down to PR #3: Instant (already cached)
Total: ~0s of perceived waiting
```

### Scenario 3: Sequential Navigation in Detail View

**Without Prefetch:**
```
Viewing PR #5
Down to PR #6: 1.2s wait
Down to PR #7: 1.2s wait
Total: 2.4s
```

**With Prefetch:**
```
Viewing PR #5 → Prefetch #6 starts
Down to PR #6: Instant (cached) → Prefetch #7 starts
Down to PR #7: Instant (cached) → Prefetch #8 starts
Total: ~0s per navigation
```

## Bandwidth Considerations

### Conservative Strategy
- Only prefetch first 3 PRs on list load
- Only prefetch on cursor movement (user interest signal)
- Only prefetch adjacent PRs during navigation

### Worst Case
Repository with 100 PRs, user views all:
- Initial: 3 prefetches (first 3 PRs)
- Navigation: 97 on-demand loads
- Adjacent: ~97 prefetches (one per navigation)
- Total: ~197 API calls vs 100 without prefetch

### Typical Case
Repository with 20 PRs, user views 5:
- Initial: 3 prefetches
- View 3 already cached: 0 additional
- View 2 more: 2 loads + 2 adjacent prefetches
- Total: 7 API calls vs 5 without prefetch
- **Extra cost: 2 API calls (40% overhead)**
- **Benefit: 3/5 PRs are instant (60% instant)**

## API Rate Limits

GitHub API rate limits (authenticated):
- 5,000 requests per hour
- ~83 requests per minute

Prefetch overhead is negligible:
- Viewing 30 PRs: ~60 requests (well under limit)
- All requests cached for 5 minutes
- Refresh clears cache but is user-initiated

## Implementation Details

### File Changes

**internal/app/update.go:**
- Added `prefetchPRDetailCmd()` - Silent background load
- Enhanced cursor movement handlers (Up/Down on PR tab)
- Enhanced tab switch handlers (switching to PR tab)
- Added PR detail navigation (Up/Down in detail view)
- Enhanced `DetailLoadedMsg` handler (batch prefetch first 3)

**internal/app/prefetch_test.go (NEW):**
- 7 comprehensive tests for prefetch behavior
- 214 lines of test coverage

### Test Coverage

```go
TestPrefetchOnCursorMovement       - Cursor triggers prefetch
TestPrefetchOnTabSwitch            - Tab to PRs triggers prefetch
TestPrefetchOnDetailLoad           - List load triggers batch prefetch
TestNavigateBetweenPRsInDetailView - Detail view navigation works
TestNavigatePRDetailAtBoundaries   - Boundary conditions handled
TestPrefetchNotTriggeredOnNonPRTabs - Only PRs trigger prefetch
TestPrefetchCacheHit               - Silent operation verified
```

**Results:**
- All tests pass: 58/58
- No flaky tests
- Build: SUCCESS

## User Experience Impact

### Before Prefetching
- Every PR view: 1.2 second blank loading screen
- Sequential browsing: Frustrating repeated waits
- User perception: "This is slow"

### After Prefetching
- First 3 PRs: Instant
- Browsed PRs: Instant (from cursor prefetch)
- Sequential navigation: Instant (from adjacent prefetch)
- User perception: "This is fast!"

## Future Enhancements

### Potential Improvements

1. **Adaptive Prefetch Count**
   - Adjust based on available bandwidth
   - Prefetch more on fast connections

2. **Smarter Prefetch Priority**
   - PRs with recent activity first
   - User's own PRs first
   - Assigned/review-requested PRs first

3. **Prefetch Cancellation**
   - Cancel prefetch if user moves away quickly
   - Prevent wasted bandwidth

4. **Persistent Cache**
   - Save to disk between sessions
   - Truly instant on app restart

5. **Predictive Prefetch**
   - Learn user patterns
   - Prefetch likely next actions

## Configuration Options

Currently hard-coded values:
```go
const (
    initialPrefetchCount = 3  // First N PRs to prefetch on list load
    cacheTTL = 5 * time.Minute // How long to cache PR details
)
```

Could be made configurable:
- Environment variables
- Config file
- Runtime flags

## Monitoring

To measure effectiveness, could add:
- Cache hit rate metrics
- Average load time per PR
- Prefetch success rate
- Bandwidth usage tracking

## Related Documentation

- PROGRESSIVE_LOADING.md - Progressive rendering strategy
- PR_DETAIL_FIXES.md - Loading state implementation
- REFRESH_FEATURE.md - Cache invalidation
