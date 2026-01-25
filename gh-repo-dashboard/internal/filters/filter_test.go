package filters

import (
	"testing"

	"github.com/kyleking/gh-repo-dashboard/internal/models"
)

func TestFilterReposAll(t *testing.T) {
	paths := []string{"/repo1", "/repo2", "/repo3"}
	summaries := map[string]models.RepoSummary{
		"/repo1": {Path: "/repo1", Ahead: 1},
		"/repo2": {Path: "/repo2", Behind: 2},
		"/repo3": {Path: "/repo3"},
	}

	result := FilterRepos(paths, summaries, models.FilterModeAll)
	if len(result) != 3 {
		t.Errorf("expected 3 repos, got %d", len(result))
	}
}

func TestFilterReposAhead(t *testing.T) {
	paths := []string{"/repo1", "/repo2", "/repo3"}
	summaries := map[string]models.RepoSummary{
		"/repo1": {Path: "/repo1", Ahead: 1},
		"/repo2": {Path: "/repo2", Behind: 2},
		"/repo3": {Path: "/repo3"},
	}

	result := FilterRepos(paths, summaries, models.FilterModeAhead)
	if len(result) != 1 {
		t.Errorf("expected 1 repo, got %d", len(result))
	}
	if result[0] != "/repo1" {
		t.Errorf("expected /repo1, got %s", result[0])
	}
}

func TestFilterReposBehind(t *testing.T) {
	paths := []string{"/repo1", "/repo2", "/repo3"}
	summaries := map[string]models.RepoSummary{
		"/repo1": {Path: "/repo1", Ahead: 1},
		"/repo2": {Path: "/repo2", Behind: 2},
		"/repo3": {Path: "/repo3"},
	}

	result := FilterRepos(paths, summaries, models.FilterModeBehind)
	if len(result) != 1 {
		t.Errorf("expected 1 repo, got %d", len(result))
	}
	if result[0] != "/repo2" {
		t.Errorf("expected /repo2, got %s", result[0])
	}
}

func TestFilterReposDirty(t *testing.T) {
	paths := []string{"/repo1", "/repo2", "/repo3"}
	summaries := map[string]models.RepoSummary{
		"/repo1": {Path: "/repo1", Staged: 2},
		"/repo2": {Path: "/repo2", Unstaged: 1},
		"/repo3": {Path: "/repo3"},
	}

	result := FilterRepos(paths, summaries, models.FilterModeDirty)
	if len(result) != 2 {
		t.Errorf("expected 2 repos, got %d", len(result))
	}
}

func TestFilterReposHasPR(t *testing.T) {
	paths := []string{"/repo1", "/repo2"}
	summaries := map[string]models.RepoSummary{
		"/repo1": {Path: "/repo1", PRInfo: &models.PRInfo{Number: 123}},
		"/repo2": {Path: "/repo2"},
	}

	result := FilterRepos(paths, summaries, models.FilterModeHasPR)
	if len(result) != 1 {
		t.Errorf("expected 1 repo, got %d", len(result))
	}
	if result[0] != "/repo1" {
		t.Errorf("expected /repo1, got %s", result[0])
	}
}

func TestFilterReposHasStash(t *testing.T) {
	paths := []string{"/repo1", "/repo2"}
	summaries := map[string]models.RepoSummary{
		"/repo1": {Path: "/repo1", StashCount: 3},
		"/repo2": {Path: "/repo2"},
	}

	result := FilterRepos(paths, summaries, models.FilterModeHasStash)
	if len(result) != 1 {
		t.Errorf("expected 1 repo, got %d", len(result))
	}
	if result[0] != "/repo1" {
		t.Errorf("expected /repo1, got %s", result[0])
	}
}
