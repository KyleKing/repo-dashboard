# Repo View

To run:

```sh
uv run multi-repo-view
```

Config file (`~/.config/multi-repo-view/config.toml`):

```tom
[settings]
refresh_interval = 30

[[repos]]
path = "~/Developer/project-a"

[[repos]]
path = "~/Developer/project-b"
```

Keybindings:

- j/k - Navigate repos
- o - Open PR in browser
- r - Manual refresh
- q - Quit
- ? - Show help
