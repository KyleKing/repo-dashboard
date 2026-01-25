package app

import (
	"fmt"
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

	parts = append(parts, styles.Badge(m.sortMode.String(), styles.SortBadgeStyle))

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
				{"j/k, ↑/↓", "Move up/down"},
				{"g/G", "Go to top/bottom"},
				{"enter, space", "Select/enter"},
				{"esc, backspace", "Go back"},
			},
		},
		{
			"Filtering & Sorting",
			[]struct{ key, desc string }{
				{"f", "Cycle filter (all → dirty → ahead → behind → has_pr → has_stash)"},
				{"s", "Cycle sort (name → modified → status → branch)"},
				{"/", "Search repositories"},
			},
		},
		{
			"Actions",
			[]struct{ key, desc string }{
				{"r", "Refresh all data"},
				{"F", "Fetch all (batch)"},
				{"P", "Prune remote (batch)"},
				{"C", "Cleanup merged (batch)"},
			},
		},
		{
			"General",
			[]struct{ key, desc string }{
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

	b.WriteString(styles.HeaderStyle.Render("Status"))
	b.WriteString("\n")
	b.WriteString(fmt.Sprintf("  Branch:    %s\n", styles.BranchStyle.Render(summary.Branch)))
	b.WriteString(fmt.Sprintf("  Upstream:  %s\n", summary.Upstream))
	b.WriteString(fmt.Sprintf("  Status:    %s\n", summary.StatusSummary()))
	b.WriteString(fmt.Sprintf("  Modified:  %s\n", summary.RelativeModified()))
	b.WriteString("\n")

	if summary.Ahead > 0 || summary.Behind > 0 {
		b.WriteString(styles.HeaderStyle.Render("Sync"))
		b.WriteString("\n")
		if summary.Ahead > 0 {
			b.WriteString(fmt.Sprintf("  %s ahead of upstream\n", styles.AheadStyle.Render(fmt.Sprintf("%d", summary.Ahead))))
		}
		if summary.Behind > 0 {
			b.WriteString(fmt.Sprintf("  %s behind upstream\n", styles.BehindStyle.Render(fmt.Sprintf("%d", summary.Behind))))
		}
		b.WriteString("\n")
	}

	if summary.PRInfo != nil {
		pr := summary.PRInfo
		b.WriteString(styles.HeaderStyle.Render("Pull Request"))
		b.WriteString("\n")
		b.WriteString(fmt.Sprintf("  #%d %s\n", pr.Number, pr.Title))
		b.WriteString(fmt.Sprintf("  Status: %s\n", styles.PRStatusBadge(pr.State, pr.IsDraft)))
		b.WriteString(fmt.Sprintf("  %s → %s\n", pr.HeadRef, pr.BaseRef))
		b.WriteString("\n")
	}

	if summary.StashCount > 0 {
		b.WriteString(styles.HeaderStyle.Render("Stashes"))
		b.WriteString("\n")
		b.WriteString(fmt.Sprintf("  %d stashed changes\n", summary.StashCount))
		b.WriteString("\n")
	}

	b.WriteString(styles.FooterStyle.Render("Press esc to go back"))

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
