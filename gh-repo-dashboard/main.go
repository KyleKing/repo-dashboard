package main

import (
	"flag"
	"fmt"
	"os"
	"path/filepath"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/kyleking/gh-repo-dashboard/internal/app"
)

func main() {
	depth := flag.Int("depth", 3, "Maximum directory depth to scan")
	flag.Parse()

	scanPaths := flag.Args()
	if len(scanPaths) == 0 {
		home, err := os.UserHomeDir()
		if err != nil {
			fmt.Fprintf(os.Stderr, "Error getting home directory: %v\n", err)
			os.Exit(1)
		}
		scanPaths = []string{filepath.Join(home, "Developer")}
	}

	absPathList := make([]string, 0, len(scanPaths))
	for _, p := range scanPaths {
		absPath, err := filepath.Abs(p)
		if err != nil {
			fmt.Fprintf(os.Stderr, "Error resolving path %s: %v\n", p, err)
			os.Exit(1)
		}
		absPathList = append(absPathList, absPath)
	}

	model := app.New(absPathList, *depth)
	p := tea.NewProgram(model, tea.WithAltScreen())

	if _, err := p.Run(); err != nil {
		fmt.Fprintf(os.Stderr, "Error running program: %v\n", err)
		os.Exit(1)
	}
}
