Conversion Plan: repo-dashboard → Go/Bubbletea gh-cli Extension

 Executive Summary

 Converting repo-dashboard from Python/Textual to Go/Bubbletea is viable with
 significant architectural mapping. The VCS abstraction pattern transfers well to Go
 interfaces, while the TUI layer requires reimplementation using Bubbletea's Elm
 architecture.

 ---
 1. Tradeoffs
 Aspect: Distribution
 Python/Textual: Requires Python/uv install
 Go/Bubbletea: Single binary, gh extension install
 ────────────────────────────────────────
 Aspect: Startup time
 Python/Textual: ~500ms (Python init)
 Go/Bubbletea: ~50ms (compiled binary)
 ────────────────────────────────────────
 Aspect: Memory
 Python/Textual: ~50-100MB (Python runtime)
 Go/Bubbletea: ~10-20MB
 ────────────────────────────────────────
 Aspect: Development speed
 Python/Textual: Faster iteration, REPL
 Go/Bubbletea: Compile step, stricter types
 ────────────────────────────────────────
 Aspect: Testing
 Python/Textual: pytest with async support
 Go/Bubbletea: go test, stricter mocking
 ────────────────────────────────────────
 Aspect: CSS styling
 Python/Textual: Separate .tcss file
 Go/Bubbletea: Inline lipgloss styles
 ────────────────────────────────────────
 Aspect: Widget library
 Python/Textual: Rich Textual widgets (DataTable)
 Go/Bubbletea: Build from bubbles primitives
 ────────────────────────────────────────
 Aspect: Concurrency
 Python/Textual: asyncio workers
 Go/Bubbletea: goroutines + channels
 ────────────────────────────────────────
 Aspect: Error handling
 Python/Textual: Exceptions propagate
 Go/Bubbletea: Explicit error returns
 ────────────────────────────────────────
 Aspect: Type safety
 Python/Textual: Runtime (dataclasses)
 Go/Bubbletea: Compile-time (structs)
 Key gains:
 - Zero-dependency distribution via gh extension
 - Faster startup/runtime performance
 - Better cross-platform consistency
 - Native goroutine concurrency model

 Key losses:
 - Textual's rich DataTable widget (must build custom)
 - Hot reload during development
 - Python's pattern matching ergonomics
 - Simpler async/await syntax

 ---
 2. Architecture Mapping

 Python/Textual Go/Bubbletea
 ─────────────────────────────────────────────────────
 app.py (RepoDashboardApp) → internal/app/app.go (Model)
 - on_mount() → Init() tea.Cmd
 - on_* handlers → Update(msg tea.Msg)
 - compose() → View() string
 - run_worker() → Goroutine + channel + Cmd

 models.py → internal/models/models.go
 - dataclass(frozen=True) → struct
 - StrEnum → type X string + const
 - Protocol → interface

 vcs_protocol.py → internal/vcs/operations.go (interface)
 vcs_git.py → internal/vcs/git.go
 vcs_jj.py → internal/vcs/jj.go
 vcs_factory.py → internal/vcs/factory.go

 github_ops.py → internal/github/ops.go
 cache.py → internal/cache/ttl.go
 filters.py → internal/filters/filters.go
 discovery.py → internal/discovery/discovery.go
 batch_tasks.py → internal/batch/tasks.go

 modals.py → internal/ui/modal/*.go (one per modal)
 app.tcss → internal/ui/styles/styles.go (lipgloss)

 ---
 3. Go Project Structure

 gh-repo-dashboard/
 ├── main.go # CLI entry, flag parsing
 ├── go.mod
 ├── internal/ ├── app/ ├── app.go # Root tea.Model ├── update.go # Message handlers ├── view.go # View composition ├── keymap.go # Key bindings └── messages.go # Custom message types ├── models/ ├── repo.go # RepoSummary, RepoDetail ├── branch.go # BranchInfo ├── pr.go # PRInfo, WorkflowSummary ├── enums.go # VCSType, FilterMode, SortMode └── items.go # RepoItem, WorktreeInfo, etc. ├── vcs/ ├── operations.go # VCSOperations interface ├── git.go # GitOperations ├── jj.go # JJOperations └── factory.go # Detection + factory ├── github/ ├── pr.go # PR fetching └── workflow.go # Workflow status ├── discovery/ └── discovery.go # Repo scanning ├── cache/ └── ttl.go # TTL cache with generics ├── filters/ ├── filter.go # Filter modes ├── sort.go # Sort modes └── search.go # Fuzzy search ├── batch/ ├── runner.go # BatchTaskRunner └── tasks.go # Task functions ├── ui/ ├── panes/ ├── repolist.go # Repo list table ├── repodetail.go # Branch/stash/worktree view └── detailpanel.go # Right-side detail panel ├── modal/ ├── stack.go # Modal stack manager ├── filter.go # Filter popup ├── sort.go # Sort popup ├── help.go # Help modal ├── batch.go # Batch task progress └── detail.go # Branch/stash/worktree detail ├── styles/ └── styles.go # Lipgloss style definitions └── theme/ └── theme.go # Catppuccin colors └── exec/ └── exec.go # Command execution helper └── testdata/ # Test fixtures

 ---
 4. Comparable Dependencies
 ┌────────────────────┬─────────────────────────┬────────────────────────┐ Python Go Purpose ├────────────────────┼─────────────────────────┼────────────────────────┤ textual charmbracelet/bubbletea TUI framework ├────────────────────┼─────────────────────────┼────────────────────────┤ textual.widgets charmbracelet/bubbles Pre-built components ├────────────────────┼─────────────────────────┼────────────────────────┤ rich (via textual) charmbracelet/lipgloss Styling/layout ├────────────────────┼─────────────────────────┼────────────────────────┤ asyncio goroutines + channels Concurrency ├────────────────────┼─────────────────────────┼────────────────────────┤ dataclasses native structs Data modeling ├────────────────────┼─────────────────────────┼────────────────────────┤ difflib (fuzzy) sahilm/fuzzy Fuzzy matching ├────────────────────┼─────────────────────────┼────────────────────────┤ pathlib path/filepath Path handling ├────────────────────┼─────────────────────────┼────────────────────────┤ subprocess os/exec Command execution ├────────────────────┼─────────────────────────┼────────────────────────┤ json encoding/json JSON parsing ├────────────────────┼─────────────────────────┼────────────────────────┤ re regexp Regex ├────────────────────┼─────────────────────────┼────────────────────────┤ pytest testing (stdlib) Testing ├────────────────────┼─────────────────────────┼────────────────────────┤ — cli/go-gh/v2 GitHub CLI integration └────────────────────┴─────────────────────────┴────────────────────────┘
 ---
 5. Key Design Changes

 5.1 State Management (Elm Architecture)

 Python (Textual):
 class RepoDashboardApp(App):
 _summaries: dict[Path, RepoSummary]
 _current_view: str
 _active_filters: list[ActiveFilter]

 def on_mount(self):
 self._load_repos()

 @on(DataTable.RowSelected)
 def on_row_selected(self, event):
 # Mutate state directly
 self._selected_row = event.row_key

 Go (Bubbletea):
 type Model struct {
 summaries map[string]models.RepoSummary
 currentView ViewMode
 filters []ActiveFilter
 selectedRow int
 // All state in one struct
 }

 func (m Model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
 switch msg := msg.(type) {
 case RowSelectedMsg:
 m.selectedRow = msg.Index
 return m, nil
 }
 // Return new model (immutable update pattern)
 }

 5.2 Async Operations

 Python:
 self.run_worker(
 self._load_repo_summary(path),
 group="summaries",
 exclusive=False,
 )

 async def _load_repo_summary(self, path):
 summary = await get_repo_summary_async(path)
 self._summaries[path] = summary
 self._update_table()

 Go:
 // Message type for async results
 type RepoLoadedMsg struct {
 Path string
 Summary models.RepoSummary
 Err error
 }

 // Spawn goroutine, return Cmd that yields message
 func loadRepoCmd(path string) tea.Cmd {
 return func() tea.Msg {
 summary, err := vcs.GetRepoSummary(path)
 return RepoLoadedMsg{Path: path, Summary: summary, Err: err}
 }
 }

 // Handle in Update
 case RepoLoadedMsg:
 if msg.Err == nil {
 m.summaries[msg.Path] = msg.Summary
 }
 return m, nil

 5.3 VCS Interface

 Python (Protocol):
 class VCSOperations(Protocol):
 vcs_type: VCSType

 async def get_repo_summary_async(self, path: Path) -> RepoSummary: ...
 async def fetch_all(self, path: Path) -> tuple[bool, str]: ...

 Go (Interface):
 type VCSOperations interface {
 VCSType() models.VCSType
 GetRepoSummary(path string) (models.RepoSummary, error)
 FetchAll(path string) (bool, string, error)
 }

 type GitOperations struct{}
 func (g *GitOperations) VCSType() models.VCSType { return models.VCSGit }
 func (g *GitOperations) GetRepoSummary(path string) (models.RepoSummary, error) { ...
 }

 5.4 Table Rendering

 Textual provides DataTable; Bubbletea requires manual rendering with lipgloss:

 func (m Model) renderRepoTable() string {
 var rows []string

 // Header
 header := lipgloss.JoinHorizontal(lipgloss.Left,
 styles.HeaderCell.Width(20).Render("Name"),
 styles.HeaderCell.Width(15).Render("Branch"),
 styles.HeaderCell.Width(12).Render("Status"),
 styles.HeaderCell.Width(8).Render("PR"),
 )
 rows = append(rows, header)

 // Data rows
 for i, repo := range m.filteredRepos() {
 style := styles.Row
 if i == m.selectedRow {
 style = styles.SelectedRow
 }
 row := lipgloss.JoinHorizontal(lipgloss.Left,
 style.Width(20).Render(truncate(repo.Name, 18)),
 style.Width(15).Render(repo.Branch),
 style.Width(12).Render(formatStatus(repo)),
 style.Width(8).Render(formatPR(repo.PRInfo)),
 )
 rows = append(rows, row)
 }

 return lipgloss.JoinVertical(lipgloss.Left, rows...)
 }

 ---
 6. Logic Changes

 6.1 Error Handling

 Python: Exceptions propagate, caught at boundaries
 try:
 pr_info = await get_pr_for_branch_async(path, branch)
 except Exception as err:
 pr_info = None # Graceful degradation

 Go: Explicit error returns everywhere
 prInfo, err := github.GetPRForBranch(path, branch)
 if err != nil {
 // Log or ignore, but must handle
 prInfo = nil
 }

 6.2 Pattern Matching → Switch Statements

 Python:
 match mode:
 case FilterMode.DIRTY:
 return _filter_dirty(repos)
 case FilterMode.AHEAD:
 return _filter_ahead(repos)

 Go:
 switch mode {
 case models.FilterDirty:
 return filterDirty(repos)
 case models.FilterAhead:
 return filterAhead(repos)
 }

 6.3 Dataclasses → Structs

 Python:
 @dataclass(frozen=True)
 class RepoSummary:
 path: Path
 name: str
 vcs_type: VCSType
 current_branch: str
 ahead_count: int = 0

 Go:
 type RepoSummary struct {
 Path string
 Name string
 VCSType VCSType
 CurrentBranch string
 AheadCount int
 }

 6.4 TTL Cache with Generics

 type TTLCache[T any] struct {
 data map[string]cacheEntry[T]
 ttl time.Duration
 mu sync.RWMutex
 }

 type cacheEntry[T any] struct {
 value T
 timestamp time.Time
 }

 func (c *TTLCache[T]) Get(key string) (T, bool) {
 c.mu.RLock()
 defer c.mu.RUnlock()

 entry, ok := c.data[key]
 if !ok || time.Since(entry.timestamp) > c.ttl {
 var zero T
 return zero, false
 }
 return entry.value, true
 }

 ---
 7. gh CLI Extension Integration

 Add to main.go:

 package main

 import (
 "os"
 tea "github.com/charmbracelet/bubbletea"
 "github.com/cli/go-gh/v2/pkg/api"
 "github.com/spf13/pflag"
 "gh-repo-dashboard/internal/app"
 )

 func main() {
 var paths []string
 var depth int
 var theme string

 pflag.StringSliceVarP(&paths, "paths", "p", []string{"."}, "Paths to scan")
 pflag.IntVarP(&depth, "depth", "d", 2, "Scan depth")
 pflag.StringVarP(&theme, "theme", "t", "auto", "Theme (light/dark/auto)")
 pflag.Parse()

 // go-gh provides authenticated GitHub client
 client, err := api.DefaultRESTClient()
 if err != nil {
 // gh CLI not available - PR features disabled
 client = nil
 }

 model := app.NewModel(paths, depth, client)
 p := tea.NewProgram(model, tea.WithAltScreen())

 if _, err := p.Run(); err != nil {
 os.Exit(1)
 }
 }

 Manifest for gh extension (required for gh extension install):
 # .github/workflows/release.yml
 # Build binaries for all platforms
 # gh extension system auto-discovers based on binary name

 ---
 8. Migration Strategy

 Phase 1: Core Infrastructure
 - Models and enums
 - VCS interface + git implementation
 - Discovery
 - Basic app shell with repo list view

 Phase 2: Read Operations
 - TTL cache
 - GitHub PR/workflow fetching
 - Filters and sort
 - Fuzzy search

 Phase 3: UI Polish
 - Detail view (branches/stashes/worktrees)
 - Modal system (filter, sort, help, detail)
 - Styling with Catppuccin theme

 Phase 4: Write Operations
 - Batch task runner
 - Batch task modal with progress
 - JJ implementation

 Phase 5: Distribution
 - gh extension manifest
 - Release workflow
 - Documentation

 ---
 9. Estimated Effort
 ┌─────────────────┬─────────────┬───────────────┬────────────────────────────┐ Component Python LOC Go LOC (est.) Notes ├─────────────────┼─────────────┼───────────────┼────────────────────────────┤ Models ~400 ~300 Simpler without decorators ├─────────────────┼─────────────┼───────────────┼────────────────────────────┤ VCS abstraction ~800 ~700 Similar complexity ├─────────────────┼─────────────┼───────────────┼────────────────────────────┤ GitHub ops ~200 ~250 More error handling ├─────────────────┼─────────────┼───────────────┼────────────────────────────┤ Cache ~50 ~80 Generic implementation ├─────────────────┼─────────────┼───────────────┼────────────────────────────┤ Filters/sort ~200 ~200 Direct translation ├─────────────────┼─────────────┼───────────────┼────────────────────────────┤ Discovery ~80 ~80 Similar ├─────────────────┼─────────────┼───────────────┼────────────────────────────┤ App core ~1000 ~800 Less widget boilerplate ├─────────────────┼─────────────┼───────────────┼────────────────────────────┤ Modals ~900 ~700 Simpler modal stack ├─────────────────┼─────────────┼───────────────┼────────────────────────────┤ Styling ~200 (tcss) ~300 Inline lipgloss ├─────────────────┼─────────────┼───────────────┼────────────────────────────┤ Total ~3800 ~3400 ~10% reduction └─────────────────┴─────────────┴───────────────┴────────────────────────────┘
 The Go version trades CSS flexibility for compile-time safety and distribution
 simplicity. The biggest effort is reimplementing the DataTable functionality with
 lipgloss.