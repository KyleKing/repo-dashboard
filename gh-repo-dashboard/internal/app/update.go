package app

import (
	"context"

	"github.com/charmbracelet/bubbles/key"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/kyleking/gh-repo-dashboard/internal/discovery"
	"github.com/kyleking/gh-repo-dashboard/internal/filters"
	"github.com/kyleking/gh-repo-dashboard/internal/models"
	"github.com/kyleking/gh-repo-dashboard/internal/vcs"
)

func (m Model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.WindowSizeMsg:
		m.width = msg.Width
		m.height = msg.Height
		m.help.Width = msg.Width
		return m, nil

	case tea.KeyMsg:
		if m.searching {
			return m.handleSearchKey(msg)
		}
		return m.handleKey(msg)

	case ReposDiscoveredMsg:
		m.repoPaths = msg.Paths
		m.loadingCount = len(msg.Paths)
		m.loadedCount = 0
		m.updateFilteredPaths()

		var cmds []tea.Cmd
		for _, path := range msg.Paths {
			cmds = append(cmds, loadRepoSummaryCmd(path))
		}
		return m, tea.Batch(cmds...)

	case RepoSummaryLoadedMsg:
		m.loadedCount++
		if m.loadedCount >= m.loadingCount {
			m.loading = false
		}

		if msg.Error != nil {
			summary := models.RepoSummary{
				Path:    msg.Path,
				VCSType: vcs.DetectVCSType(msg.Path),
				Error:   msg.Error,
			}
			m.summaries[msg.Path] = summary
		} else {
			m.summaries[msg.Path] = msg.Summary
		}
		m.updateFilteredPaths()
		return m, loadPRCmd(msg.Path, msg.Summary.Branch, msg.Summary.Upstream)

	case PRLoadedMsg:
		if summary, ok := m.summaries[msg.Path]; ok {
			summary.PRInfo = msg.PRInfo
			m.summaries[msg.Path] = summary
			m.updateFilteredPaths()
		}
		return m, nil

	case WorkflowLoadedMsg:
		if summary, ok := m.summaries[msg.Path]; ok {
			summary.WorkflowInfo = msg.Workflow
			m.summaries[msg.Path] = summary
		}
		return m, nil

	case ErrorMsg:
		return m, nil
	}

	return m, nil
}

func (m Model) handleKey(msg tea.KeyMsg) (tea.Model, tea.Cmd) {
	switch {
	case key.Matches(msg, m.keys.Quit):
		return m, tea.Quit

	case key.Matches(msg, m.keys.Help):
		if m.viewMode == ViewModeHelp {
			m.viewMode = ViewModeRepoList
		} else {
			m.viewMode = ViewModeHelp
		}
		return m, nil

	case key.Matches(msg, m.keys.Up):
		if m.cursor > 0 {
			m.cursor--
		}
		return m, nil

	case key.Matches(msg, m.keys.Down):
		if m.cursor < len(m.filteredPaths)-1 {
			m.cursor++
		}
		return m, nil

	case key.Matches(msg, m.keys.Top):
		m.cursor = 0
		return m, nil

	case key.Matches(msg, m.keys.Bottom):
		if len(m.filteredPaths) > 0 {
			m.cursor = len(m.filteredPaths) - 1
		}
		return m, nil

	case key.Matches(msg, m.keys.Enter):
		if m.viewMode == ViewModeRepoList && m.cursor < len(m.filteredPaths) {
			m.selectedRepo = m.filteredPaths[m.cursor]
			m.viewMode = ViewModeRepoDetail
		}
		return m, nil

	case key.Matches(msg, m.keys.Back):
		switch m.viewMode {
		case ViewModeRepoDetail:
			m.viewMode = ViewModeRepoList
		case ViewModeHelp:
			m.viewMode = ViewModeRepoList
		case ViewModeFilter:
			m.viewMode = ViewModeRepoList
		}
		return m, nil

	case key.Matches(msg, m.keys.Refresh):
		m.loading = true
		m.summaries = make(map[string]models.RepoSummary)
		return m, discoverReposCmd(m.scanPaths, m.maxDepth)

	case key.Matches(msg, m.keys.Filter):
		m.CycleFilter()
		m.updateFilteredPaths()
		m.cursor = 0
		return m, nil

	case key.Matches(msg, m.keys.Sort):
		m.CycleSort()
		m.updateFilteredPaths()
		return m, nil

	case key.Matches(msg, m.keys.Search):
		m.searching = true
		m.searchInput.Focus()
		return m, nil
	}

	return m, nil
}

func (m Model) handleSearchKey(msg tea.KeyMsg) (tea.Model, tea.Cmd) {
	switch msg.Type {
	case tea.KeyEsc:
		m.searching = false
		m.searchInput.Blur()
		return m, nil

	case tea.KeyEnter:
		m.searching = false
		m.searchText = m.searchInput.Value()
		m.searchInput.Blur()
		m.updateFilteredPaths()
		m.cursor = 0
		return m, nil

	case tea.KeyCtrlC:
		return m, tea.Quit
	}

	var cmd tea.Cmd
	m.searchInput, cmd = m.searchInput.Update(msg)
	m.searchText = m.searchInput.Value()
	m.updateFilteredPaths()
	m.cursor = 0
	return m, cmd
}

func (m *Model) updateFilteredPaths() {
	m.filteredPaths = filters.FilterAndSort(
		m.repoPaths,
		m.summaries,
		m.CurrentFilter(),
		m.sortMode,
		m.searchText,
		m.sortReverse,
	)

	if m.cursor >= len(m.filteredPaths) {
		if len(m.filteredPaths) > 0 {
			m.cursor = len(m.filteredPaths) - 1
		} else {
			m.cursor = 0
		}
	}
}

func discoverReposCmd(scanPaths []string, maxDepth int) tea.Cmd {
	return func() tea.Msg {
		paths := discovery.DiscoverRepos(scanPaths, maxDepth)
		return ReposDiscoveredMsg{Paths: paths}
	}
}

func loadRepoSummaryCmd(path string) tea.Cmd {
	return func() tea.Msg {
		ops := vcs.GetOperations(path)
		summary, err := ops.GetRepoSummary(context.Background(), path)
		return RepoSummaryLoadedMsg{
			Path:    path,
			Summary: summary,
			Error:   err,
		}
	}
}

func loadPRCmd(path string, branch string, upstream string) tea.Cmd {
	if upstream == "" {
		return nil
	}
	return func() tea.Msg {
		return PRLoadedMsg{Path: path, PRInfo: nil}
	}
}
