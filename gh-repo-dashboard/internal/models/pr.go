package models

import "time"

type PRInfo struct {
	Number    int
	Title     string
	State     string
	URL       string
	IsDraft   bool
	Mergeable string
	HeadRef   string
	BaseRef   string
	Checks    ChecksStatus
}

func (p PRInfo) StatusDisplay() string {
	if p.IsDraft {
		return "DRAFT"
	}
	switch p.State {
	case "OPEN":
		return "OPEN"
	case "MERGED":
		return "MERGED"
	case "CLOSED":
		return "CLOSED"
	default:
		return p.State
	}
}

type ChecksStatus struct {
	Total    int
	Passing  int
	Failing  int
	Pending  int
	Skipped  int
}

func (c ChecksStatus) Summary() string {
	if c.Total == 0 {
		return "—"
	}
	if c.Failing > 0 {
		return "failing"
	}
	if c.Pending > 0 {
		return "pending"
	}
	if c.Passing == c.Total {
		return "passing"
	}
	return "mixed"
}

type PRDetail struct {
	PRInfo
	Body       string
	Author     string
	CreatedAt  time.Time
	UpdatedAt  time.Time
	Additions  int
	Deletions  int
	Comments   int
	ReviewsURL string
}

func (p PRDetail) RelativeCreated() string {
	return RelativeTime(p.CreatedAt)
}

func (p PRDetail) RelativeUpdated() string {
	return RelativeTime(p.UpdatedAt)
}

type WorkflowRun struct {
	ID         int64
	Name       string
	Status     string
	Conclusion string
	URL        string
	CreatedAt  time.Time
	UpdatedAt  time.Time
}

func (w WorkflowRun) StatusDisplay() string {
	if w.Status == "completed" {
		return w.Conclusion
	}
	return w.Status
}

type WorkflowSummary struct {
	Runs       []WorkflowRun
	Total      int
	Passing    int
	Failing    int
	InProgress int
}

func (w WorkflowSummary) StatusDisplay() string {
	if w.Total == 0 {
		return "—"
	}
	if w.Failing > 0 {
		return "failing"
	}
	if w.InProgress > 0 {
		return "running"
	}
	if w.Passing == w.Total {
		return "passing"
	}
	return "mixed"
}
