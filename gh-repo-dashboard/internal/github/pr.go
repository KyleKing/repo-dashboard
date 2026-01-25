package github

import (
	"context"
	"encoding/json"
	"os/exec"
	"strings"

	"github.com/kyleking/gh-repo-dashboard/internal/cache"
	"github.com/kyleking/gh-repo-dashboard/internal/models"
	"github.com/kyleking/gh-repo-dashboard/internal/vcs"
)

type prResponse struct {
	Number              int    `json:"number"`
	Title               string `json:"title"`
	State               string `json:"state"`
	URL                 string `json:"url"`
	IsDraft             bool   `json:"isDraft"`
	MergeStateStatus    string `json:"mergeStateStatus"`
	HeadRefName         string `json:"headRefName"`
	BaseRefName         string `json:"baseRefName"`
	StatusCheckRollup   []statusCheck `json:"statusCheckRollup"`
}

type statusCheck struct {
	State      string `json:"state,omitempty"`
	Status     string `json:"status,omitempty"`
	Conclusion string `json:"conclusion,omitempty"`
}

func GetPRForBranch(ctx context.Context, repoPath string, branch string, upstream string) (*models.PRInfo, error) {
	cacheKey := upstream + ":" + branch
	if cached, ok := cache.PRCache.Get(cacheKey); ok {
		return cached, nil
	}

	env := vcs.GetGitHubEnv(repoPath)

	cmd := exec.CommandContext(ctx, "gh", "pr", "view", branch,
		"--json", "number,title,state,url,isDraft,mergeStateStatus,headRefName,baseRefName,statusCheckRollup")
	cmd.Dir = repoPath
	if len(env) > 0 {
		cmd.Env = append(cmd.Environ(), env...)
	}

	out, err := cmd.Output()
	if err != nil {
		cache.PRCache.Set(cacheKey, nil)
		return nil, err
	}

	var resp prResponse
	if err := json.Unmarshal(out, &resp); err != nil {
		return nil, err
	}

	checks := parseChecks(resp.StatusCheckRollup)

	pr := &models.PRInfo{
		Number:    resp.Number,
		Title:     resp.Title,
		State:     resp.State,
		URL:       resp.URL,
		IsDraft:   resp.IsDraft,
		Mergeable: resp.MergeStateStatus,
		HeadRef:   resp.HeadRefName,
		BaseRef:   resp.BaseRefName,
		Checks:    checks,
	}

	cache.PRCache.Set(cacheKey, pr)
	return pr, nil
}

func parseChecks(checks []statusCheck) models.ChecksStatus {
	var status models.ChecksStatus
	status.Total = len(checks)

	for _, c := range checks {
		state := strings.ToLower(c.State)
		conclusion := strings.ToLower(c.Conclusion)

		switch {
		case state == "pending" || c.Status == "IN_PROGRESS" || c.Status == "QUEUED":
			status.Pending++
		case conclusion == "success" || state == "success":
			status.Passing++
		case conclusion == "failure" || conclusion == "error" || state == "failure" || state == "error":
			status.Failing++
		case conclusion == "skipped" || conclusion == "neutral":
			status.Skipped++
		default:
			status.Pending++
		}
	}

	return status
}

func GetPRDetail(ctx context.Context, repoPath string, prNumber int) (*models.PRDetail, error) {
	env := vcs.GetGitHubEnv(repoPath)

	cmd := exec.CommandContext(ctx, "gh", "pr", "view", string(rune(prNumber)),
		"--json", "number,title,state,url,isDraft,mergeStateStatus,headRefName,baseRefName,body,author,createdAt,updatedAt,additions,deletions,comments")
	cmd.Dir = repoPath
	if len(env) > 0 {
		cmd.Env = append(cmd.Environ(), env...)
	}

	out, err := cmd.Output()
	if err != nil {
		return nil, err
	}

	var resp struct {
		prResponse
		Body      string `json:"body"`
		Author    struct {
			Login string `json:"login"`
		} `json:"author"`
		CreatedAt string `json:"createdAt"`
		UpdatedAt string `json:"updatedAt"`
		Additions int    `json:"additions"`
		Deletions int    `json:"deletions"`
		Comments  int    `json:"comments"`
	}

	if err := json.Unmarshal(out, &resp); err != nil {
		return nil, err
	}

	return &models.PRDetail{
		PRInfo: models.PRInfo{
			Number:    resp.Number,
			Title:     resp.Title,
			State:     resp.State,
			URL:       resp.URL,
			IsDraft:   resp.IsDraft,
			Mergeable: resp.MergeStateStatus,
			HeadRef:   resp.HeadRefName,
			BaseRef:   resp.BaseRefName,
		},
		Body:      resp.Body,
		Author:    resp.Author.Login,
		Additions: resp.Additions,
		Deletions: resp.Deletions,
		Comments:  resp.Comments,
	}, nil
}
