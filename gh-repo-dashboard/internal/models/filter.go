package models

type ActiveFilter struct {
	Mode    FilterMode
	Enabled bool
}

func (f ActiveFilter) DisplayName() string {
	return f.Mode.String()
}

func (f ActiveFilter) ShortKey() string {
	return f.Mode.ShortKey()
}

func NewActiveFilter(mode FilterMode) ActiveFilter {
	return ActiveFilter{
		Mode:    mode,
		Enabled: mode == FilterModeAll,
	}
}
