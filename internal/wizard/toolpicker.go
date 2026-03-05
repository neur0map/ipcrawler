package wizard

import (
	"fmt"
	"strings"

	"github.com/charmbracelet/x/ansi"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
	"github.com/neur0map/ipcrawler/internal/config"
)

// toolPicker is a custom Bubble Tea model for multi-select tool selection
// with a live command tooltip for the focused item.
type toolPicker struct {
	tools      []config.Template
	target     string
	targetType string // "ip", "domain", or "both"
	cursor     int
	selected   map[int]bool
	filtered   []int // indices into tools for visible items

	filtering bool
	filter    string

	done    bool
	aborted bool
	err     string

	width  int
	height int
	offset int // scroll offset
}

func newToolPicker(tools []config.Template, target, targetType string) toolPicker {
	indices := make([]int, len(tools))
	for i := range tools {
		indices[i] = i
	}
	return toolPicker{
		tools:      tools,
		target:     target,
		targetType: targetType,
		selected:   make(map[int]bool),
		filtered:   indices,
	}
}

func (m toolPicker) Init() tea.Cmd {
	return nil
}

func (m toolPicker) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.WindowSizeMsg:
		m.width = msg.Width
		m.height = msg.Height

	case tea.KeyMsg:
		if m.filtering {
			return m.updateFilter(msg)
		}
		return m.updateNormal(msg)
	}
	return m, nil
}

func (m toolPicker) updateNormal(msg tea.KeyMsg) (tea.Model, tea.Cmd) {
	m.err = ""
	n := len(m.filtered)
	if n == 0 {
		if msg.String() == "ctrl+c" || msg.String() == "q" || msg.String() == "esc" {
			m.aborted = true
			return m, tea.Quit
		}
		return m, nil
	}

	switch msg.String() {
	case "up", "k":
		m.cursor--
		if m.cursor < 0 {
			m.cursor = n - 1
		}
		m.ensureVisible()
	case "down", "j":
		m.cursor++
		if m.cursor >= n {
			m.cursor = 0
		}
		m.ensureVisible()
	case " ", "x":
		idx := m.filtered[m.cursor]
		m.selected[idx] = !m.selected[idx]
		if !m.selected[idx] {
			delete(m.selected, idx)
		}
	case "a":
		if len(m.selected) == len(m.filtered) {
			m.selected = make(map[int]bool)
		} else {
			for _, idx := range m.filtered {
				m.selected[idx] = true
			}
		}
	case "/":
		m.filtering = true
		m.filter = ""
	case "enter":
		if len(m.selected) == 0 {
			m.err = "select at least one tool"
			return m, nil
		}
		m.done = true
		return m, tea.Quit
	case "ctrl+c", "q", "esc":
		m.aborted = true
		return m, tea.Quit
	}
	return m, nil
}

func (m toolPicker) updateFilter(msg tea.KeyMsg) (tea.Model, tea.Cmd) {
	switch msg.String() {
	case "esc":
		m.filtering = false
		m.filter = ""
		m.refilter()
	case "enter":
		m.filtering = false
	case "backspace":
		if len(m.filter) > 0 {
			m.filter = m.filter[:len(m.filter)-1]
			m.refilter()
		}
	case "ctrl+c":
		m.aborted = true
		return m, tea.Quit
	default:
		// Only accept printable runes
		if len(msg.Runes) > 0 {
			m.filter += string(msg.Runes)
			m.refilter()
		}
	}
	return m, nil
}

func (m *toolPicker) refilter() {
	if m.filter == "" {
		m.filtered = make([]int, len(m.tools))
		for i := range m.tools {
			m.filtered[i] = i
		}
	} else {
		m.filtered = m.filtered[:0]
		lower := strings.ToLower(m.filter)
		for i, t := range m.tools {
			if strings.Contains(strings.ToLower(t.Name), lower) ||
				strings.Contains(strings.ToLower(t.Category), lower) ||
				strings.Contains(strings.ToLower(t.Description), lower) ||
				matchesTags(t.Tags, lower) {
				m.filtered = append(m.filtered, i)
			}
		}
	}
	if m.cursor >= len(m.filtered) {
		m.cursor = max(0, len(m.filtered)-1)
	}
	m.offset = 0
	m.ensureVisible()
}

func matchesTags(tags []string, query string) bool {
	for _, tag := range tags {
		if strings.Contains(strings.ToLower(tag), query) {
			return true
		}
	}
	return false
}

func (m *toolPicker) ensureVisible() {
	vh := m.viewportHeight()
	if vh <= 0 {
		return
	}
	if m.cursor < m.offset {
		m.offset = m.cursor
	}
	if m.cursor >= m.offset+vh {
		m.offset = m.cursor - vh + 1
	}
}

func (m toolPicker) viewportHeight() int {
	// header(3 lines) + hint(2 lines) + help(1 line) + padding(2 lines)
	vh := m.height - 8
	if vh < 3 {
		vh = 3
	}
	return vh
}

// --- Rendering ---

var (
	pickerBorder = lipgloss.NewStyle().
			Border(lipgloss.RoundedBorder()).
			BorderForeground(tOrange).
			Padding(1, 2)

	titleStyle = lipgloss.NewStyle().
			Foreground(tOrange).
			Bold(true)

	helpStyle = lipgloss.NewStyle().
			Foreground(tGray)

	selectorStyle = lipgloss.NewStyle().
			Foreground(tOrange)

	selectedStyle = lipgloss.NewStyle().
			Foreground(tGreen)

	unselectedStyle = lipgloss.NewStyle().
			Foreground(tGray)

	sudoStyle = lipgloss.NewStyle().
			Foreground(tRed).
			Bold(true)

	incompatStyle = lipgloss.NewStyle().
			Foreground(tYellow).
			Bold(true)

	hintCmdStyle = lipgloss.NewStyle().
			Foreground(tDim)

	filterPromptStyle = lipgloss.NewStyle().
				Foreground(tOrange)

	errStyle = lipgloss.NewStyle().
			Foreground(tRed)
)

func (m toolPicker) View() string {
	if m.done || m.aborted {
		return ""
	}

	w := m.width
	if w <= 0 {
		w = termWidth()
	}

	var sb strings.Builder

	// Header
	sb.WriteString(titleStyle.Render("Tools"))
	sb.WriteString("\n")

	if m.filtering {
		sb.WriteString(filterPromptStyle.Render("/ "))
		sb.WriteString(lipgloss.NewStyle().Foreground(tWhite).Render(m.filter))
		sb.WriteString(lipgloss.NewStyle().Foreground(tOrange).Render("█"))
		sb.WriteString("\n")
	} else {
		sb.WriteString(helpStyle.Render("space toggle · ↑↓ navigate · / filter · enter confirm"))
		sb.WriteString("\n")
	}

	if m.err != "" {
		sb.WriteString(errStyle.Render("  * " + m.err))
		sb.WriteString("\n")
	}

	sb.WriteString("\n")

	// Compute layout parameters
	// Chrome: border(2+2) + padding(2+2) + selector(2) + prefix(2) = 12 inner
	// But we're rendering inside pickerBorder which adds its own padding.
	// Content width = widget width - border horizontal frame.
	contentWidth := w - pickerBorder.GetHorizontalFrameSize()
	if contentWidth < 40 {
		contentWidth = 40
	}
	// Each option line: selector(2) + prefix(2) + label
	labelWidth := contentWidth - 4 // selector + prefix

	// Build option lines
	maxName := 0
	for _, idx := range m.filtered {
		if len(m.tools[idx].Name) > maxName {
			maxName = len(m.tools[idx].Name)
		}
	}

	vh := m.viewportHeight()
	visible := m.filtered
	if len(visible) > vh {
		end := m.offset + vh
		if end > len(visible) {
			end = len(visible)
		}
		visible = visible[m.offset:end]
	}

	for vi, idx := range visible {
		absIdx := m.offset + vi
		isCursor := absIdx == m.cursor
		isSel := m.selected[idx]
		t := m.tools[idx]

		// Selector
		if isCursor {
			sb.WriteString(selectorStyle.Render("> "))
		} else {
			sb.WriteString("  ")
		}

		// Prefix
		if isSel {
			sb.WriteString(selectedStyle.Render("✓ "))
		} else {
			sb.WriteString(unselectedStyle.Render("· "))
		}

		// Label: tag + name + " : " + desc + [SUDO]
		label := m.buildLabel(t, maxName, labelWidth)
		sb.WriteString(label)
		sb.WriteString("\n")
	}

	// Scroll indicators
	if len(m.filtered) > vh {
		scrollInfo := fmt.Sprintf("  (%d/%d)", m.cursor+1, len(m.filtered))
		if m.offset > 0 {
			scrollInfo = "  ↑" + scrollInfo
		}
		if m.offset+vh < len(m.filtered) {
			scrollInfo = "  ↓" + scrollInfo
		}
		sb.WriteString(helpStyle.Render(scrollInfo))
		sb.WriteString("\n")
	}

	// Command tooltip for focused item
	sb.WriteString("\n")
	if len(m.filtered) > 0 && m.cursor < len(m.filtered) {
		idx := m.filtered[m.cursor]
		cmd := m.tools[idx].Command
		hint := "  $ " + cmd
		maxHint := contentWidth - 2
		if maxHint > 0 {
			hint = ansi.Truncate(hint, maxHint, "…")
		}
		sb.WriteString(hintCmdStyle.Render(hint))
	}

	return pickerBorder.Width(w - pickerBorder.GetHorizontalBorderSize()).Render(sb.String())
}

func (m toolPicker) buildLabel(t config.Template, maxName, maxWidth int) string {
	plainTag := fmt.Sprintf("%-10s", "["+strings.ToUpper(t.Category)+"]")
	coloredTag := categoryColorFor(t.Category).Render(plainTag)
	paddedName := fmt.Sprintf("%-*s", maxName, t.Name)
	desc := t.Description

	// Right-side tags: [SUDO], [DOMAIN], [IP]
	var rightTags string
	rightReserved := 0
	if t.Sudo {
		rightTags += " " + sudoStyle.Render("[SUDO]")
		rightReserved += 7
	}
	if !isCompatible(t.TargetType, m.targetType) {
		tag := strings.ToUpper(t.TargetType)
		rightTags += " " + incompatStyle.Render("["+tag+"]")
		rightReserved += len(tag) + 3 // brackets + space
	}

	// Budget for description: total - tag(10) - space(1) - name(maxName) - " : "(3) - rightReserved
	if rightReserved < 7 {
		rightReserved = 7 // minimum reservation for alignment
	}
	descBudget := maxWidth - 10 - 1 - maxName - 3 - rightReserved
	if descBudget < 10 {
		descBudget = 10
	}
	if len(desc) > descBudget {
		desc = desc[:descBudget-1] + "…"
	}

	// Pad description so right tags align even when desc is short
	descPadded := fmt.Sprintf("%-*s", descBudget, desc)

	label := coloredTag + " " + paddedName + " : " + descPadded + rightTags

	// Hard safety truncation on the fully assembled, ANSI-colored label
	label = ansi.Truncate(label, maxWidth, "…")

	return label
}

// selectedTools returns the names of all selected tools.
func (m toolPicker) selectedTools() []string {
	var names []string
	for idx := range m.selected {
		names = append(names, m.tools[idx].Name)
	}
	return names
}

// runToolPicker launches the tool picker as a Bubble Tea program and returns
// the selected tool names. Returns nil and an error if the user aborted.
func runToolPicker(tools []config.Template, target, targetType string) ([]string, error) {
	picker := newToolPicker(tools, target, targetType)
	p := tea.NewProgram(picker, tea.WithAltScreen())
	finalModel, err := p.Run()
	if err != nil {
		return nil, fmt.Errorf("tool picker: %w", err)
	}

	m := finalModel.(toolPicker)
	if m.aborted {
		return nil, nil // signal to restart the wizard loop
	}
	return m.selectedTools(), nil
}
