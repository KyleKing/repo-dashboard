package models

type ActiveFilter struct {
	Mode     FilterMode
	Enabled  bool
	Inverted bool
}

func (f ActiveFilter) DisplayName() string {
	return f.Mode.String()
}

func (f ActiveFilter) ShortKey() string {
	return f.Mode.ShortKey()
}

func NewActiveFilter(mode FilterMode) ActiveFilter {
	return ActiveFilter{
		Mode:     mode,
		Enabled:  mode == FilterModeAll,
		Inverted: false,
	}
}

type ActiveSort struct {
	Mode     SortMode
	Enabled  bool
	Priority int
	Reverse  bool
}

func (s ActiveSort) DisplayName() string {
	name := s.Mode.String()
	if s.Reverse {
		name += " (rev)"
	}
	return name
}

func (s ActiveSort) ShortKey() string {
	return s.Mode.ShortKey()
}

func NewActiveSort(mode SortMode, priority int) ActiveSort {
	return ActiveSort{
		Mode:     mode,
		Enabled:  false,
		Priority: priority,
		Reverse:  false,
	}
}
