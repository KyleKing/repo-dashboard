package app

import (
	"fmt"
	"path/filepath"
	"strings"

	"github.com/charmbracelet/lipgloss"
	"github.com/kyleking/gh-repo-dashboard/internal/models"
	"github.com/kyleking/gh-repo-dashboard/internal/ui/styles"
)

func (m Model) View() string {
	if m.width == 0 {
		return "Loading..."
	}

	switch m.viewMode {
	case ViewModeHelp:
		return m.renderHelp()
	case ViewModeRepoDetail:
		return m.renderRepoDetail()
	case ViewModeFilter:
		return m.renderFilterModal()
	case ViewModeSort:
		return m.renderSortModal()
	case ViewModeBatchProgress:
		return m.renderBatchProgress()
	default:
		return m.renderRepoList()
	}
}

func (m Model) renderRepoList() string {
	var b strings.Builder

	b.WriteString(m.renderBreadcrumbs())
	b.WriteString("\n")
	b.WriteString(m.renderStatusBar())
	b.WriteString("\n")

	if m.searching {
		b.WriteString(m.searchInput.View())
		b.WriteString("\n")
	}

	b.WriteString(m.renderTable())
	b.WriteString("\n")
	b.WriteString(m.renderFooter())

	return b.String()
}

func (m Model) renderBreadcrumbs() string {
	title := styles.TitleStyle.Render("repo-dashboard")

	badges := []string{}

	repoCount := fmt.Sprintf("%d repos", len(m.filteredPaths))
	if len(m.filteredPaths) != len(m.repoPaths) {
		repoCount = fmt.Sprintf("%d/%d repos", len(m.filteredPaths), len(m.repoPaths))
	}
	badges = append(badges, styles.Badge(repoCount, styles.CountBadgeStyle))

	if dirtyCount := m.DirtyCount(); dirtyCount > 0 {
		badges = append(badges, styles.Badge(fmt.Sprintf("%d dirty", dirtyCount), styles.FilterBadgeStyle))
	}

	if prCount := m.PRCount(); prCount > 0 {
		badges = append(badges, styles.Badge(fmt.Sprintf("%d PRs", prCount), styles.PROpenStyle))
	}

	if m.loading {
		progress := fmt.Sprintf("Loading %d/%d", m.loadedCount, m.loadingCount)
		badges = append(badges, styles.Badge(progress, styles.CountBadgeStyle))
	}

	return title + "  " + strings.Join(badges, " ")
}

func (m Model) renderStatusBar() string {
	parts := []string{}

	filter := m.CurrentFilter()
	if filter != models.FilterModeAll {
		parts = append(parts, styles.Badge(filter.String(), styles.FilterBadgeStyle))
	}

	sortLabel := m.sortMode.String()
	if m.sortReverse {
		sortLabel += " (rev)"
	}
	parts = append(parts, styles.Badge(sortLabel, styles.SortBadgeStyle))

	if m.searchText != "" {
		parts = append(parts, styles.Badge("\""+m.searchText+"\"", styles.SearchBadgeStyle))
	}

	return strings.Join(parts, " ")
}

func (m Model) renderTable() string {
	if len(m.filteredPaths) == 0 {
		if m.loading {
			return styles.SubtitleStyle.Render("  Discovering repositories...")
		}
		return styles.SubtitleStyle.Render("  No repositories found")
	}

	colWidths := struct {
		name     int
		branch   int
		status   int
		pr       int
		modified int
	}{
		name:     20,
		branch:   15,
		status:   12,
		pr:       8,
		modified: 12,
	}

	header := fmt.Sprintf("  %-*s  %-*s  %-*s  %-*s  %s",
		colWidths.name, "NAME",
		colWidths.branch, "BRANCH",
		colWidths.status, "STATUS",
		colWidths.pr, "PR",
		"MODIFIED",
	)
	header = styles.HeaderStyle.Render(header)

	availableHeight := m.height - 6
	if m.searching {
		availableHeight--
	}

	startIdx := 0
	if m.cursor >= availableHeight {
		startIdx = m.cursor - availableHeight + 1
	}

	endIdx := startIdx + availableHeight
	if endIdx > len(m.filteredPaths) {
		endIdx = len(m.filteredPaths)
	}

	var rows []string
	rows = append(rows, header)

	for i := startIdx; i < endIdx; i++ {
		path := m.filteredPaths[i]
		summary := m.summaries[path]
		row := m.renderTableRow(summary, i == m.cursor, colWidths)
		rows = append(rows, row)
	}

	return strings.Join(rows, "\n")
}

func (m Model) renderTableRow(s models.RepoSummary, selected bool, colWidths struct {
	name     int
	branch   int
	status   int
	pr       int
	modified int
}) string {
	cursor := "  "
	if selected {
		cursor = "> "
	}

	name := truncate(s.Name(), colWidths.name)
	branch := truncate(s.Branch, colWidths.branch)
	status := s.StatusSummary()
	pr := "—"
	if s.PRInfo != nil {
		pr = fmt.Sprintf("#%d", s.PRInfo.Number)
	}
	modified := s.RelativeModified()

	var style lipgloss.Style
	if selected {
		style = styles.SelectedRowStyle
	} else {
		style = styles.TableRowStyle
	}

	nameStyle := style
	branchStyle := styles.BranchStyle
	if selected {
		branchStyle = branchStyle.Background(styles.Surface0)
	}

	var statusStyle lipgloss.Style
	switch {
	case s.IsDirty():
		statusStyle = styles.DirtyStyle
	case s.Status() == models.RepoStatusClean:
		statusStyle = styles.CleanStyle
	default:
		statusStyle = style
	}
	if selected {
		statusStyle = statusStyle.Background(styles.Surface0)
	}

	prStyle := style
	if s.PRInfo != nil {
		prStyle = styles.PROpenStyle
		if selected {
			prStyle = prStyle.Background(styles.Surface0)
		}
	}

	row := fmt.Sprintf("%s%-*s  %s  %s  %-*s  %s",
		cursor,
		colWidths.name, nameStyle.Render(name),
		branchStyle.Render(fmt.Sprintf("%-*s", colWidths.branch, branch)),
		statusStyle.Render(fmt.Sprintf("%-*s", colWidths.status, status)),
		colWidths.pr, prStyle.Render(pr),
		style.Render(modified),
	)

	return row
}

func (m Model) renderFooter() string {
	bindings := []struct {
		key  string
		desc string
	}{
		{"j/k", "nav"},
		{"enter", "select"},
		{"f", "filter"},
		{"s", "sort"},
		{"/", "search"},
		{"r", "refresh"},
		{"?", "help"},
		{"q", "quit"},
	}

	var parts []string
	for _, b := range bindings {
		parts = append(parts,
			styles.FooterKeyStyle.Render(b.key)+
				styles.FooterDescStyle.Render(" "+b.desc))
	}

	return strings.Join(parts, "  ")
}

func (m Model) renderHelp() string {
	var b strings.Builder

	b.WriteString(styles.TitleStyle.Render("Help"))
	b.WriteString("\n\n")

	sections := []struct {
		title string
		keys  []struct{ key, desc string }
	}{
		{
			"Navigation",
			[]struct{ key, desc string }{
				{"j/k, Up/Down", "Move up/down"},
				{"h/l, Left/Right", "Switch tabs (detail view)"},
				{"g/G", "Go to top/bottom"},
				{"enter, space", "Select/enter"},
				{"esc, backspace", "Go back"},
				{"tab", "Next tab (detail view)"},
			},
		},
		{
			"Filtering & Sorting",
			[]struct{ key, desc string }{
				{"f", "Open filter menu"},
				{"s", "Open sort menu"},
				{"R", "Reverse sort order"},
				{"/", "Search repositories"},
			},
		},
		{
			"Batch Actions",
			[]struct{ key, desc string }{
				{"F", "Fetch all (filtered repos)"},
				{"P", "Prune remote (filtered repos)"},
				{"C", "Cleanup merged (filtered repos)"},
			},
		},
		{
			"General",
			[]struct{ key, desc string }{
				{"r", "Refresh all data"},
				{"?", "Toggle help"},
				{"q, ctrl+c", "Quit"},
			},
		},
	}

	for _, section := range sections {
		b.WriteString(styles.HeaderStyle.Render(section.title))
		b.WriteString("\n")
		for _, k := range section.keys {
			b.WriteString(fmt.Sprintf("  %s  %s\n",
				styles.HelpKeyStyle.Render(fmt.Sprintf("%-15s", k.key)),
				styles.HelpDescStyle.Render(k.desc)))
		}
		b.WriteString("\n")
	}

	b.WriteString(styles.FooterStyle.Render("Press ? or esc to close"))

	return b.String()
}

func (m Model) renderRepoDetail() string {
	summary, ok := m.summaries[m.selectedRepo]
	if !ok {
		return "Repository not found"
	}

	var b strings.Builder

	b.WriteString(styles.TitleStyle.Render(summary.Name()))
	b.WriteString("\n")
	b.WriteString(styles.SubtitleStyle.Render(summary.Path))
	b.WriteString("\n\n")

	b.WriteString(m.renderDetailTabs())
	b.WriteString("\n\n")

	switch m.detailTab {
	case DetailTabBranches:
		b.WriteString(m.renderBranchList())
	case DetailTabStashes:
		b.WriteString(m.renderStashList())
	case DetailTabWorktrees:
		b.WriteString(m.renderWorktreeList())
	}

	b.WriteString("\n")
	b.WriteString(styles.FooterStyle.Render("tab: switch tabs  j/k: navigate  esc: back"))

	return b.String()
}

func (m Model) renderDetailTabs() string {
	tabs := []struct {
		name  string
		tab   DetailTab
		count int
	}{
		{"Branches", DetailTabBranches, len(m.branches)},
		{"Stashes", DetailTabStashes, len(m.stashes)},
		{"Worktrees", DetailTabWorktrees, len(m.worktrees)},
	}

	var parts []string
	for _, t := range tabs {
		label := fmt.Sprintf("%s (%d)", t.name, t.count)
		if t.tab == m.detailTab {
			parts = append(parts, styles.Badge(label, styles.SortBadgeStyle))
		} else {
			parts = append(parts, styles.Badge(label, styles.CountBadgeStyle))
		}
	}

	return strings.Join(parts, " ")
}

func (m Model) renderBranchList() string {
	if len(m.branches) == 0 {
		return styles.SubtitleStyle.Render("  No branches found")
	}

	var rows []string
	header := fmt.Sprintf("  %-20s  %-20s  %-10s  %s",
		"BRANCH", "UPSTREAM", "STATUS", "LAST COMMIT")
	rows = append(rows, styles.HeaderStyle.Render(header))

	for i, branch := range m.branches {
		cursor := "  "
		if i == m.detailCursor {
			cursor = "> "
		}

		name := truncate(branch.Name, 20)
		if branch.IsCurrent {
			name = "* " + name
		}
		upstream := truncate(branch.Upstream, 20)
		status := ""
		if branch.Ahead > 0 {
			status += fmt.Sprintf("↑%d", branch.Ahead)
		}
		if branch.Behind > 0 {
			if status != "" {
				status += " "
			}
			status += fmt.Sprintf("↓%d", branch.Behind)
		}
		if status == "" {
			status = "✓"
		}
		lastCommit := branch.RelativeLastCommit()

		var style lipgloss.Style
		if i == m.detailCursor {
			style = styles.SelectedRowStyle
		} else {
			style = styles.TableRowStyle
		}

		nameStyle := styles.BranchStyle
		if branch.IsCurrent {
			nameStyle = styles.PROpenStyle
		}
		if i == m.detailCursor {
			nameStyle = nameStyle.Background(styles.Surface0)
		}

		row := fmt.Sprintf("%s%s  %-20s  %-10s  %s",
			cursor,
			nameStyle.Render(fmt.Sprintf("%-20s", name)),
			style.Render(upstream),
			style.Render(status),
			style.Render(lastCommit),
		)
		rows = append(rows, row)
	}

	return strings.Join(rows, "\n")
}

func (m Model) renderStashList() string {
	if len(m.stashes) == 0 {
		return styles.SubtitleStyle.Render("  No stashes found")
	}

	var rows []string
	header := fmt.Sprintf("  %-8s  %-40s  %s",
		"INDEX", "MESSAGE", "DATE")
	rows = append(rows, styles.HeaderStyle.Render(header))

	for i, stash := range m.stashes {
		cursor := "  "
		if i == m.detailCursor {
			cursor = "> "
		}

		index := fmt.Sprintf("stash@{%d}", stash.Index)
		message := truncate(stash.Message, 40)
		date := stash.RelativeDate()

		var style lipgloss.Style
		if i == m.detailCursor {
			style = styles.SelectedRowStyle
		} else {
			style = styles.TableRowStyle
		}

		row := fmt.Sprintf("%s%-8s  %s  %s",
			cursor,
			style.Render(index),
			style.Render(fmt.Sprintf("%-40s", message)),
			style.Render(date),
		)
		rows = append(rows, row)
	}

	return strings.Join(rows, "\n")
}

func (m Model) renderWorktreeList() string {
	if len(m.worktrees) == 0 {
		return styles.SubtitleStyle.Render("  No worktrees found")
	}

	var rows []string
	header := fmt.Sprintf("  %-30s  %-20s  %s",
		"PATH", "BRANCH", "STATUS")
	rows = append(rows, styles.HeaderStyle.Render(header))

	for i, wt := range m.worktrees {
		cursor := "  "
		if i == m.detailCursor {
			cursor = "> "
		}

		path := truncate(filepath.Base(wt.Path), 30)
		branch := truncate(wt.Branch, 20)
		status := ""
		if wt.IsBare {
			status = "bare"
		}
		if wt.IsLocked {
			if status != "" {
				status += ", "
			}
			status += "locked"
		}
		if status == "" {
			status = "active"
		}

		var style lipgloss.Style
		if i == m.detailCursor {
			style = styles.SelectedRowStyle
		} else {
			style = styles.TableRowStyle
		}

		row := fmt.Sprintf("%s%s  %s  %s",
			cursor,
			style.Render(fmt.Sprintf("%-30s", path)),
			styles.BranchStyle.Render(fmt.Sprintf("%-20s", branch)),
			style.Render(status),
		)
		rows = append(rows, row)
	}

	return strings.Join(rows, "\n")
}

func (m Model) renderFilterModal() string {
	var b strings.Builder

	b.WriteString(styles.TitleStyle.Render("Select Filter"))
	b.WriteString("\n\n")

	modes := models.AllFilterModes()
	currentFilter := m.CurrentFilter()

	for i, mode := range modes {
		cursor := "  "
		if i == m.filterCursor {
			cursor = "> "
		}

		indicator := "  "
		if mode == currentFilter {
			indicator = "* "
		}

		label := mode.String()
		count := m.countForFilter(mode)
		countStr := fmt.Sprintf("(%d)", count)

		var style lipgloss.Style
		if i == m.filterCursor {
			style = styles.SelectedRowStyle
		} else {
			style = styles.TableRowStyle
		}

		row := fmt.Sprintf("%s%s%s  %s",
			cursor,
			styles.PROpenStyle.Render(indicator),
			style.Render(fmt.Sprintf("%-12s", label)),
			styles.SubtitleStyle.Render(countStr),
		)
		b.WriteString(row)
		b.WriteString("\n")
	}

	b.WriteString("\n")
	b.WriteString(styles.FooterStyle.Render("enter: select  esc: cancel"))

	return b.String()
}

func (m Model) countForFilter(mode models.FilterMode) int {
	count := 0
	for _, s := range m.summaries {
		switch mode {
		case models.FilterModeAll:
			count++
		case models.FilterModeAhead:
			if s.Ahead > 0 {
				count++
			}
		case models.FilterModeBehind:
			if s.Behind > 0 {
				count++
			}
		case models.FilterModeDirty:
			if s.IsDirty() {
				count++
			}
		case models.FilterModeHasPR:
			if s.PRInfo != nil {
				count++
			}
		case models.FilterModeHasStash:
			if s.StashCount > 0 {
				count++
			}
		}
	}
	return count
}

func (m Model) renderSortModal() string {
	var b strings.Builder

	b.WriteString(styles.TitleStyle.Render("Select Sort"))
	b.WriteString("\n\n")

	modes := []models.SortMode{
		models.SortModeName,
		models.SortModeModified,
		models.SortModeStatus,
		models.SortModeBranch,
	}

	for i, mode := range modes {
		cursor := "  "
		if i == m.sortCursor {
			cursor = "> "
		}

		indicator := "  "
		if mode == m.sortMode {
			indicator = "* "
		}

		label := mode.String()

		var style lipgloss.Style
		if i == m.sortCursor {
			style = styles.SelectedRowStyle
		} else {
			style = styles.TableRowStyle
		}

		row := fmt.Sprintf("%s%s%s",
			cursor,
			styles.PROpenStyle.Render(indicator),
			style.Render(label),
		)
		b.WriteString(row)
		b.WriteString("\n")
	}

	b.WriteString("\n")
	reverseLabel := "[ ] Reverse order"
	if m.sortReverse {
		reverseLabel = "[x] Reverse order"
	}
	b.WriteString(fmt.Sprintf("    %s\n", styles.SubtitleStyle.Render(reverseLabel)))

	b.WriteString("\n")
	b.WriteString(styles.FooterStyle.Render("enter: select  R: toggle reverse  esc: cancel"))

	return b.String()
}

func (m Model) renderBatchProgress() string {
	var b strings.Builder

	b.WriteString(styles.TitleStyle.Render(m.batchTask))
	b.WriteString("\n\n")

	progressWidth := 40
	filled := 0
	if m.batchTotal > 0 {
		filled = (m.batchProgress * progressWidth) / m.batchTotal
	}
	bar := strings.Repeat("█", filled) + strings.Repeat("░", progressWidth-filled)
	progressStr := fmt.Sprintf("[%s] %d/%d", bar, m.batchProgress, m.batchTotal)
	b.WriteString(progressStr)
	b.WriteString("\n\n")

	if len(m.batchResults) > 0 {
		b.WriteString(styles.HeaderStyle.Render("Results"))
		b.WriteString("\n")

		maxShow := 15
		startIdx := 0
		if len(m.batchResults) > maxShow {
			startIdx = len(m.batchResults) - maxShow
		}

		for i := startIdx; i < len(m.batchResults); i++ {
			result := m.batchResults[i]
			icon := styles.SuccessStyle.Render("✓")
			if !result.Success {
				icon = styles.ErrorStyle.Render("✗")
			}
			name := truncate(filepath.Base(result.Path), 25)
			msg := truncate(result.Message, 40)

			row := fmt.Sprintf("  %s %-25s  %s", icon, name, styles.SubtitleStyle.Render(msg))
			b.WriteString(row)
			b.WriteString("\n")
		}
	}

	b.WriteString("\n")
	if m.batchRunning {
		b.WriteString(styles.SubtitleStyle.Render("Running... please wait"))
	} else {
		b.WriteString(styles.FooterStyle.Render("Press esc to close"))
	}

	return b.String()
}

func truncate(s string, maxLen int) string {
	if len(s) <= maxLen {
		return s
	}
	if maxLen <= 3 {
		return s[:maxLen]
	}
	return s[:maxLen-3] + "..."
}
