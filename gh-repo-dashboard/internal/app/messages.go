package app

import "github.com/kyleking/gh-repo-dashboard/internal/models"

type ReposDiscoveredMsg struct {
	Paths []string
}

type RepoSummaryLoadedMsg struct {
	Path    string
	Summary models.RepoSummary
	Error   error
}

type PRLoadedMsg struct {
	Path   string
	PRInfo *models.PRInfo
	Error  error
}

type WorkflowLoadedMsg struct {
	Path     string
	Workflow *models.WorkflowSummary
	Error    error
}

type ErrorMsg struct {
	Error error
}

type TickMsg struct{}

type WindowSizeMsg struct {
	Width  int
	Height int
}
