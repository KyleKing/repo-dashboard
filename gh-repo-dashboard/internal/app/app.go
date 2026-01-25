package app

import (
	"github.com/charmbracelet/bubbles/help"
	"github.com/charmbracelet/bubbles/textinput"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/kyleking/gh-repo-dashboard/internal/models"
)

type ViewMode int

const (
	ViewModeRepoList ViewMode = iota
	ViewModeRepoDetail
	ViewModeHelp
	ViewModeFilter
)

type Model struct {
	scanPaths []string
	maxDepth  int

	repoPaths []string
	summaries map[string]models.RepoSummary

	filteredPaths []string
	cursor        int

	activeFilters []models.ActiveFilter
	sortMode      models.SortMode
	sortReverse   bool
	searchText    string
	searching     bool
	searchInput   textinput.Model

	viewMode       ViewMode
	selectedRepo   string
	width          int
	height         int
	loading        bool
	loadingCount   int
	loadedCount    int

	keys KeyMap
	help help.Model
}

func New(scanPaths []string, maxDepth int) Model {
	ti := textinput.New()
	ti.Placeholder = "Search repos..."
	ti.CharLimit = 100

	filters := make([]models.ActiveFilter, 0, len(models.AllFilterModes()))
	for _, mode := range models.AllFilterModes() {
		filters = append(filters, models.NewActiveFilter(mode))
	}

	return Model{
		scanPaths:     scanPaths,
		maxDepth:      maxDepth,
		summaries:     make(map[string]models.RepoSummary),
		activeFilters: filters,
		sortMode:      models.SortModeName,
		searchInput:   ti,
		viewMode:      ViewModeRepoList,
		loading:       true,
		keys:          DefaultKeyMap(),
		help:          help.New(),
	}
}

func (m Model) Init() tea.Cmd {
	return discoverReposCmd(m.scanPaths, m.maxDepth)
}

func (m Model) CurrentFilter() models.FilterMode {
	for _, f := range m.activeFilters {
		if f.Enabled && f.Mode != models.FilterModeAll {
			return f.Mode
		}
	}
	return models.FilterModeAll
}

func (m *Model) SetFilter(mode models.FilterMode) {
	for i := range m.activeFilters {
		m.activeFilters[i].Enabled = m.activeFilters[i].Mode == mode
	}
}

func (m *Model) CycleFilter() {
	current := m.CurrentFilter()
	modes := models.AllFilterModes()
	for i, mode := range modes {
		if mode == current {
			next := modes[(i+1)%len(modes)]
			m.SetFilter(next)
			return
		}
	}
	m.SetFilter(models.FilterModeAll)
}

func (m *Model) CycleSort() {
	m.sortMode = m.sortMode.Next()
}

func (m Model) DirtyCount() int {
	count := 0
	for _, s := range m.summaries {
		if s.IsDirty() {
			count++
		}
	}
	return count
}

func (m Model) PRCount() int {
	count := 0
	for _, s := range m.summaries {
		if s.PRInfo != nil {
			count++
		}
	}
	return count
}

func (m Model) SelectedSummary() (models.RepoSummary, bool) {
	if m.cursor >= 0 && m.cursor < len(m.filteredPaths) {
		path := m.filteredPaths[m.cursor]
		if summary, ok := m.summaries[path]; ok {
			return summary, true
		}
	}
	return models.RepoSummary{}, false
}
