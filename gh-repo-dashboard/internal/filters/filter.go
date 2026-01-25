package filters

import "github.com/kyleking/gh-repo-dashboard/internal/models"

func FilterRepos(paths []string, summaries map[string]models.RepoSummary, mode models.FilterMode) []string {
	if mode == models.FilterModeAll {
		return paths
	}

	var filtered []string
	for _, path := range paths {
		summary, ok := summaries[path]
		if !ok {
			continue
		}

		if passesFilter(summary, mode) {
			filtered = append(filtered, path)
		}
	}

	return filtered
}

func passesFilter(s models.RepoSummary, mode models.FilterMode) bool {
	switch mode {
	case models.FilterModeAll:
		return true
	case models.FilterModeAhead:
		return s.Ahead > 0
	case models.FilterModeBehind:
		return s.Behind > 0
	case models.FilterModeDirty:
		return s.IsDirty()
	case models.FilterModeHasPR:
		return s.PRInfo != nil
	case models.FilterModeHasStash:
		return s.StashCount > 0
	default:
		return true
	}
}

func FilterAndSort(
	paths []string,
	summaries map[string]models.RepoSummary,
	filterMode models.FilterMode,
	sortMode models.SortMode,
	searchText string,
	reverse bool,
) []string {
	filtered := FilterRepos(paths, summaries, filterMode)

	if searchText != "" {
		filtered = SearchRepos(filtered, summaries, searchText)
	}

	sorted := SortPaths(filtered, summaries, sortMode, reverse)

	return sorted
}
