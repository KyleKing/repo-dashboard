package app

import (
	"context"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/kyleking/gh-repo-dashboard/internal/cache"
	"github.com/kyleking/gh-repo-dashboard/internal/github"
	"github.com/kyleking/gh-repo-dashboard/internal/vcs"
)

func loadRepoWithPRCmd(path string) tea.Cmd {
	return func() tea.Msg {
		ctx := context.Background()
		ops := vcs.GetOperations(path)

		summary, err := ops.GetRepoSummary(ctx, path)
		if err != nil {
			return RepoSummaryLoadedMsg{
				Path:  path,
				Error: err,
			}
		}

		if summary.Upstream != "" {
			pr, _ := github.GetPRForBranch(ctx, path, summary.Branch, summary.Upstream)
			summary.PRInfo = pr

			if pr != nil {
				commits, _ := ops.GetCommitLog(ctx, path, 1)
				if len(commits) > 0 {
					workflow, _ := github.GetWorkflowRunsForCommit(ctx, path, commits[0].Hash)
					summary.WorkflowInfo = workflow
				}
			}
		}

		return RepoSummaryLoadedMsg{
			Path:    path,
			Summary: summary,
		}
	}
}

func refreshCmd(scanPaths []string, maxDepth int) tea.Cmd {
	return func() tea.Msg {
		cache.ClearAll()
		return nil
	}
}

type BatchTaskResult struct {
	Path    string
	Success bool
	Message string
}

type BatchTaskCompleteMsg struct {
	TaskName string
	Results  []BatchTaskResult
}

func batchFetchAllCmd(paths []string) tea.Cmd {
	return func() tea.Msg {
		ctx := context.Background()
		var results []BatchTaskResult

		for _, path := range paths {
			ops := vcs.GetOperations(path)
			success, msg, _ := ops.FetchAll(ctx, path)
			results = append(results, BatchTaskResult{
				Path:    path,
				Success: success,
				Message: msg,
			})
		}

		return BatchTaskCompleteMsg{
			TaskName: "Fetch All",
			Results:  results,
		}
	}
}

func batchPruneRemoteCmd(paths []string) tea.Cmd {
	return func() tea.Msg {
		ctx := context.Background()
		var results []BatchTaskResult

		for _, path := range paths {
			ops := vcs.GetOperations(path)
			success, msg, _ := ops.PruneRemote(ctx, path)
			results = append(results, BatchTaskResult{
				Path:    path,
				Success: success,
				Message: msg,
			})
		}

		return BatchTaskCompleteMsg{
			TaskName: "Prune Remote",
			Results:  results,
		}
	}
}

func batchCleanupMergedCmd(paths []string) tea.Cmd {
	return func() tea.Msg {
		ctx := context.Background()
		var results []BatchTaskResult

		for _, path := range paths {
			ops := vcs.GetOperations(path)
			success, msg, _ := ops.CleanupMergedBranches(ctx, path)
			results = append(results, BatchTaskResult{
				Path:    path,
				Success: success,
				Message: msg,
			})
		}

		return BatchTaskCompleteMsg{
			TaskName: "Cleanup Merged",
			Results:  results,
		}
	}
}
