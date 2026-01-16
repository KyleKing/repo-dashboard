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

1. **Full Catppuccin themes** - Replace textual themes with full palette
1. **CLI-only mode** - `--cli` flag for non-interactive JSON output (only from cache, not new retrievals for performance unless requested)
1. **gh-poi integration** - Identify safe-to-delete branches
1. **jj-vcs support** - Support Jujutsu version control

## Commands

```bash
# Run app
uv run reda

# Run tests
uv run pytest -v

# Run with custom options
uv run reda --depth 3 --theme light

# Format code
uv run ruff format src/ tests/
```
