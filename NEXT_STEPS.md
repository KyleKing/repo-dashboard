# Next Steps

## Secondary Priorities

### Polish & Error Handling
**Effort:** 2-3 hours

**Tasks:**
- Better error messages when git/gh not found
- Handle repos without upstream (show warning, not error)
- Handle detached HEAD gracefully
- Add loading indicators for slow operations
- Show warnings for repos with issues

## Future Enhancements (Low Priority)

1. **CLI-only mode** - `--cli` flag for non-interactive JSON output
2. **gh-poi integration** - Identify safe-to-delete branches
3. **Full Catppuccin themes** - Replace textual themes with full palette
4. **Custom TCSS support** - Load user theme from `~/.config/multi-repo-view/theme.tcss`
5. **Configuration file** - Custom keybindings in `~/.config/multi-repo-view/config.toml`
6. **jj-vcs support** - Support Jujutsu version control

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
