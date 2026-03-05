package tracker

import (
	"fmt"
	"os"
	"strings"
	"time"

	"github.com/charmbracelet/bubbles/spinner"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
	"github.com/charmbracelet/log"
	"github.com/neur0map/ipcrawler/internal/runner"
)

// --- Home Depot Orange palette ---

var (
	orange = lipgloss.Color("#F96302")
	green  = lipgloss.Color("#00FF00")
	red    = lipgloss.Color("#FF4444")
	gray   = lipgloss.Color("#6C6C6C")
	white  = lipgloss.Color("#FFFFFF")

	yellow = lipgloss.Color("#FFD700")

	pendingIconStyle = lipgloss.NewStyle().Foreground(gray)
	pendingNameStyle = lipgloss.NewStyle().Foreground(gray)
	waitingIconStyle = lipgloss.NewStyle().Foreground(yellow)
	waitingNameStyle = lipgloss.NewStyle().Foreground(yellow)
	activeNameStyle  = lipgloss.NewStyle().Foreground(orange).Bold(true)
	doneIconStyle    = lipgloss.NewStyle().Foreground(green)
	doneNameStyle    = lipgloss.NewStyle().Foreground(green)
	failIconStyle    = lipgloss.NewStyle().Foreground(red)
	failNameStyle    = lipgloss.NewStyle().Foreground(red)
	skipIconStyle    = lipgloss.NewStyle().Foreground(gray)
	skipNameStyle    = lipgloss.NewStyle().Foreground(gray)
	dimStyle         = lipgloss.NewStyle().Foreground(gray)
	liveLineStyle    = lipgloss.NewStyle().Foreground(white)
	durationStyle    = lipgloss.NewStyle().Foreground(orange).Bold(true)
)

// Predefined high-contrast colors for per-tool verbose prefixes.
var toolColors = []lipgloss.Color{
	lipgloss.Color("#F96302"), // Orange (primary)
	lipgloss.Color("#00FFFF"), // Cyan
	lipgloss.Color("#FFD700"), // Gold
	lipgloss.Color("#FF69B4"), // Hot pink
	lipgloss.Color("#7FFFD4"), // Aquamarine
	lipgloss.Color("#FF6B6B"), // Coral
	lipgloss.Color("#87CEEB"), // Sky blue
	lipgloss.Color("#DDA0DD"), // Plum
	lipgloss.Color("#FFFF00"), // Yellow
	lipgloss.Color("#00FF00"), // Green
}

// ──────────────────────────────────────────────
// Minimal mode — Live Progress View
// ──────────────────────────────────────────────

type doneMsg struct{}

type jobState struct {
	name      string
	status    runner.JobStatus
	lastLine  string
	waitingOn string // dependency name when status == StatusWaiting
	err       error
	duration  time.Duration
}

// Model is the bubbletea model for the live progress view.
// It renders a fixed multi-line list that overwrites in place,
// showing a spinner + the latest stdout line for each active tool.
type Model struct {
	updates  <-chan runner.JobUpdate
	jobs     []jobState
	spinner  spinner.Model
	cancel   func()
	done     bool
	width    int // terminal width from WindowSizeMsg
	nameCol  int // width of the name column (longest tool name)
}

// NewModel creates a tracker model bound to the runner's update channel.
func NewModel(updates <-chan runner.JobUpdate, toolNames []string, cancel func()) Model {
	s := spinner.New()
	s.Spinner = spinner.MiniDot
	s.Style = lipgloss.NewStyle().Foreground(orange)

	// Calculate name column width from the longest tool name
	maxName := 0
	for _, n := range toolNames {
		if len(n) > maxName {
			maxName = len(n)
		}
	}

	jobs := make([]jobState, len(toolNames))
	for i, name := range toolNames {
		jobs[i] = jobState{name: name, status: runner.StatusPending}
	}

	return Model{
		updates: updates,
		jobs:    jobs,
		spinner: s,
		cancel:  cancel,
		width:   100, // sensible default until WindowSizeMsg arrives
		nameCol: maxName,
	}
}

// IsDone returns whether all jobs completed (vs. user cancelled).
func (m Model) IsDone() bool { return m.done }

func (m Model) Init() tea.Cmd {
	return tea.Batch(m.spinner.Tick, waitForUpdate(m.updates))
}

func (m Model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.KeyMsg:
		if msg.String() == "ctrl+c" {
			m.cancel()
			return m, tea.Quit
		}

	case tea.WindowSizeMsg:
		m.width = msg.Width

	case runner.JobUpdate:
		for i := range m.jobs {
			if m.jobs[i].name == msg.ToolName {
				m.jobs[i].status = msg.Status
				if msg.Line != "" && msg.Stream == runner.StreamStdout {
					m.jobs[i].lastLine = msg.Line
				}
				if msg.WaitingOn != "" {
					m.jobs[i].waitingOn = msg.WaitingOn
				}
				if msg.Err != nil {
					m.jobs[i].err = msg.Err
				}
				if msg.Duration > 0 {
					m.jobs[i].duration = msg.Duration
				}
				break
			}
		}
		return m, waitForUpdate(m.updates)

	case doneMsg:
		m.done = true
		return m, tea.Quit

	case spinner.TickMsg:
		var cmd tea.Cmd
		m.spinner, cmd = m.spinner.Update(msg)
		return m, cmd
	}

	return m, nil
}

func (m Model) View() string {
	// Layout: "  icon  Name(padded)  live-line-or-status  [duration]"
	// Fixed columns: 2 (indent) + 2 (icon) + 2 (gap) + nameCol + 2 (gap) = nameCol + 8
	// Duration suffix for done/failed: " 1.2s" = ~8 chars
	// Available for detail: width - nameCol - 8 - durationSuffix
	fixedCols := m.nameCol + 8
	durWidth := 10 // " 1.2s" right-aligned
	detailWidth := m.width - fixedCols - durWidth
	if detailWidth < 20 {
		detailWidth = 20 // floor
	}

	var sb strings.Builder
	sb.WriteString("\n")

	for _, j := range m.jobs {
		paddedName := fmt.Sprintf("%-*s", m.nameCol, j.name)
		var line string

		switch j.status {
		case runner.StatusPending:
			icon := pendingIconStyle.Render("○")
			name := pendingNameStyle.Render(paddedName)
			detail := dimStyle.Render("waiting")
			line = fmt.Sprintf("  %s  %s  %s", icon, name, detail)

		case runner.StatusWaiting:
			icon := waitingIconStyle.Render("◷")
			name := waitingNameStyle.Render(paddedName)
			depInfo := "waiting on dependency"
			if j.waitingOn != "" {
				depInfo = "waiting on " + j.waitingOn
			}
			detail := waitingNameStyle.Render(depInfo)
			line = fmt.Sprintf("  %s  %s  %s", icon, name, detail)

		case runner.StatusRunning:
			icon := m.spinner.View()
			name := activeNameStyle.Render(paddedName)
			var detail string
			if j.lastLine != "" {
				detail = liveLineStyle.Render(smartTruncate(j.lastLine, detailWidth))
			} else {
				detail = dimStyle.Render("starting...")
			}
			line = fmt.Sprintf("  %s  %s  %s", icon, name, detail)

		case runner.StatusDone:
			icon := doneIconStyle.Render("✓")
			name := doneNameStyle.Render(paddedName)
			dur := durationStyle.Render(fmtDuration(j.duration))
			// Show the final stdout line so the user sees what the tool produced
			if j.lastLine != "" {
				finalWidth := detailWidth - len(fmtDuration(j.duration)) - 3
				if finalWidth < 10 {
					finalWidth = 10
				}
				detail := dimStyle.Render(smartTruncate(j.lastLine, finalWidth))
				line = fmt.Sprintf("  %s  %s  %s  %s", icon, name, detail, dur)
			} else {
				line = fmt.Sprintf("  %s  %s  %s", icon, name, dur)
			}

		case runner.StatusFailed:
			icon := failIconStyle.Render("✗")
			name := failNameStyle.Render(paddedName)
			dur := durationStyle.Render(fmtDuration(j.duration))
			if j.err != nil {
				errWidth := detailWidth - len(fmtDuration(j.duration)) - 3
				if errWidth < 10 {
					errWidth = 10
				}
				detail := failNameStyle.Render(smartTruncate(j.err.Error(), errWidth))
				line = fmt.Sprintf("  %s  %s  %s  %s", icon, name, detail, dur)
			} else {
				line = fmt.Sprintf("  %s  %s  %s", icon, name, dur)
			}

		case runner.StatusSkipped:
			icon := skipIconStyle.Render("⊘")
			name := skipNameStyle.Render(paddedName)
			detail := dimStyle.Render("skipped")
			if j.err != nil {
				detail = dimStyle.Render(smartTruncate(j.err.Error(), detailWidth))
			}
			line = fmt.Sprintf("  %s  %s  %s", icon, name, detail)
		}

		sb.WriteString(line)
		sb.WriteString("\n")
	}

	sb.WriteString("\n")
	return sb.String()
}

func waitForUpdate(ch <-chan runner.JobUpdate) tea.Cmd {
	return func() tea.Msg {
		update, ok := <-ch
		if !ok {
			return doneMsg{}
		}
		return update
	}
}

// ──────────────────────────────────────────────
// Verbose mode — charmbracelet/log per-tool
// ──────────────────────────────────────────────

// RunVerbose streams tool output as structured log messages.
// Each tool gets a unique color prefix for visual separation.
func RunVerbose(updates <-chan runner.JobUpdate) {
	loggers := make(map[string]*log.Logger)
	colorIdx := 0

	for update := range updates {
		if update.Status == runner.StatusRunning && update.Line == "" {
			continue
		}

		logger, ok := loggers[update.ToolName]
		if !ok {
			color := toolColors[colorIdx%len(toolColors)]
			colorIdx++

			logger = log.NewWithOptions(os.Stdout, log.Options{
				ReportTimestamp: true,
				TimeFormat:      "15:04:05",
				Prefix:          fmt.Sprintf("%-15s", strings.ToUpper(update.ToolName)),
			})

			styles := log.DefaultStyles()
			styles.Prefix = lipgloss.NewStyle().
				Foreground(color).
				Bold(true)
			styles.Timestamp = lipgloss.NewStyle().
				Foreground(gray)
			logger.SetStyles(styles)
			loggers[update.ToolName] = logger
		}

		switch {
		case update.Status == runner.StatusWaiting:
			dep := update.WaitingOn
			if dep == "" {
				dep = "dependency"
			}
			logger.Info("◷ waiting on " + dep)

		case update.Status == runner.StatusSkipped:
			if update.Err != nil {
				logger.Warn("⊘ " + update.Err.Error())
			} else {
				logger.Warn("⊘ skipped")
			}

		case update.Line != "" && update.Stream == runner.StreamStdout:
			logger.Info(update.Line)

		case update.Line != "" && update.Stream == runner.StreamStderr:
			logger.Warn(update.Line)

		case update.Status == runner.StatusDone:
			logger.Info("✓ completed", "duration", fmtDuration(update.Duration))

		case update.Status == runner.StatusFailed:
			logger.Error("✗ failed", "error", update.Err)
		}
	}
}

// --- helpers ---

// smartTruncate clips a string to max visible characters.
// If the string fits, it's returned as-is. Otherwise the tail is kept
// with a leading "…" so the user sees the most recent/relevant part.
func smartTruncate(s string, max int) string {
	if max <= 0 {
		return ""
	}
	if len(s) <= max {
		return s
	}
	// Keep the tail — the latest output is the most useful context
	if max <= 3 {
		return s[:max]
	}
	return "…" + s[len(s)-(max-1):]
}

func fmtDuration(d time.Duration) string {
	if d < time.Second {
		return fmt.Sprintf("%dms", d.Milliseconds())
	}
	return fmt.Sprintf("%.1fs", d.Seconds())
}
