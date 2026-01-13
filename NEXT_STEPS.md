# Next Steps

## Immediate Priorities

### Option 1: Filter & Sort (Recommended)
**Why:** Most impactful feature for users with many repositories
**Effort:** 3-4 hours
**Complexity:** Medium

**Implementation:**
1. Add filter/sort state to app.py
2. Implement fuzzy matching (use `difflib` or add `fzf` dependency)
3. Add filter presets (dirty, ahead, PR)
4. Add sort modes (name, modified, status)
5. Bind `f` (filter) and `s` (sort) keys
6. Update breadcrumbs to show active filter/sort

**Files to Create/Modify:**
- `src/multi_repo_view/filters.py` (NEW) - Fuzzy matching logic
- `src/multi_repo_view/app.py` - Add filter/sort state and methods
- `src/multi_repo_view/app.tcss` - Filter indicator styling
- `tests/test_filters.py` (NEW) - Filter/sort tests

---

### Option 2: Help Modal (Quick Win)
**Why:** Improves discoverability, fast to implement
**Effort:** 30-60 minutes
**Complexity:** Low

**Implementation:**
1. Create `HelpModal(ModalScreen)` in modals.py
2. Format all BINDINGS from app.py into readable sections
3. Show current theme
4. Bind to `?` key (already bound, just needs implementation)

**Code Snippet:**
```python
class HelpModal(ModalScreen):
    """Display help and keybindings"""

    BINDINGS = [Binding("escape", "dismiss", "Close")]

    def compose(self) -> ComposeResult:
        help_text = """
[bold]Navigation[/]
j/k or ↓/↑  Navigate
g/G         Jump to top/bottom
space/enter Select/Open
escape      Back/Close

[bold]Actions[/]
c  Copy popup
o  Open PR in browser
r  Refresh all data
?  Help
q  Quit
"""
        with Vertical(classes="help-modal-container"):
            yield Static(help_text, classes="help-modal-content")
```

---

### Option 3: Performance & Caching
**Why:** Better UX, especially for large repos
**Effort:** 2-3 hours
**Complexity:** Medium

**Implementation:**
1. Update `get_branch_list_async()` to use `branch_cache`
2. Update `get_commits_ahead/behind()` to use `commit_cache`
3. Add cache invalidation in `action_refresh()`
4. Add cache for worktree/stash data

**Cache Keys:**
- Branch list: `f"{repo_path}:branches"`
- Commits: `f"{repo_path}:{branch}:commits"`
- Worktrees: `f"{repo_path}:worktrees"`
- Stashes: `f"{repo_path}:stashes"`

---

## Secondary Priorities

### Polish & Error Handling
**Effort:** 2-3 hours

**Tasks:**
- Better error messages when git/gh not found
- Handle repos without upstream (show warning, not error)
- Handle detached HEAD gracefully
- Add loading indicators for slow operations
- Show warnings for repos with issues

---

## Future Enhancements (Low Priority)

1. **CLI-only mode** - `--cli` flag for non-interactive JSON output
2. **gh-poi integration** - Identify safe-to-delete branches
3. **Full Catppuccin themes** - Replace textual themes with full palette
4. **Custom TCSS support** - Load user theme from `~/.config/multi-repo-view/theme.tcss`
5. **Configuration file** - Custom keybindings in `~/.config/multi-repo-view/config.toml`
6. **jj-vcs support** - Support Jujutsu version control

---

## Current Status

✅ **Complete:** 10/10 core phases
✅ **Tests:** 48/48 passing
✅ **Documentation:** Updated and cleaned up

**Ready for:**
- Filter & Sort implementation
- Help Modal
- Performance optimizations

---

## Decision Guide

**Choose Filter & Sort if:**
- Users have 5+ repositories
- Finding specific repos is a pain point
- Ready for a medium-complexity feature

**Choose Help Modal if:**
- Need a quick win (~1 hour)
- Onboarding is important
- Want to tackle something simple first

**Choose Performance if:**
- App feels slow
- Users have large repositories
- Ready to optimize existing features

---

## Commands

```bash
# Run app
uv run multi-repo-view

# Run tests
uv run pytest -v

# Run with custom options
uv run multi-repo-view --depth 3 --theme light

# Format code
uv run ruff format src/ tests/
```
