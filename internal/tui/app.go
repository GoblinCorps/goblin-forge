package tui

import (
	"fmt"
	"strings"
	"time"

	"github.com/astoreyai/goblin-forge/internal/coordinator"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

// Version info
const (
	AppVersion = "0.4.0"
)

// ViewType represents the active view
type ViewType int

const (
	ViewDashboard ViewType = iota
	ViewHelp
	ViewSpawn
)

// App is the main TUI application
type App struct {
	coordinator *coordinator.Coordinator

	// State
	activeView    ViewType
	goblins       []*coordinator.Goblin
	selectedIndex int
	output        []string
	width         int
	height        int
	voiceEnabled  bool
	err           error

	// Timing
	lastUpdate time.Time
}

// New creates a new TUI application
func New(coord *coordinator.Coordinator) *App {
	return &App{
		coordinator:   coord,
		activeView:    ViewDashboard,
		goblins:       []*coordinator.Goblin{},
		selectedIndex: 0,
		output:        []string{},
		lastUpdate:    time.Now(),
	}
}

// Init implements tea.Model
func (a *App) Init() tea.Cmd {
	return tea.Batch(
		a.tickCmd(),
		a.refreshGoblins(),
	)
}

// tickCmd returns a command that ticks every 500ms
func (a *App) tickCmd() tea.Cmd {
	return tea.Tick(500*time.Millisecond, func(t time.Time) tea.Msg {
		return tickMsg(t)
	})
}

// refreshGoblins fetches the current goblin list
func (a *App) refreshGoblins() tea.Cmd {
	return func() tea.Msg {
		if a.coordinator == nil {
			return goblinListMsg{goblins: []*coordinator.Goblin{}}
		}
		goblins, err := a.coordinator.List()
		if err != nil {
			return errMsg{err}
		}
		return goblinListMsg{goblins: goblins}
	}
}

// Message types
type tickMsg time.Time
type goblinListMsg struct {
	goblins []*coordinator.Goblin
}
type errMsg struct {
	err error
}
type outputMsg struct {
	lines []string
}

// Update implements tea.Model
func (a *App) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.KeyMsg:
		return a.handleKeyPress(msg)

	case tea.WindowSizeMsg:
		a.width = msg.Width
		a.height = msg.Height
		return a, nil

	case tickMsg:
		a.lastUpdate = time.Time(msg)
		return a, tea.Batch(a.tickCmd(), a.refreshGoblins())

	case goblinListMsg:
		a.goblins = msg.goblins
		// Bounds check
		if a.selectedIndex >= len(a.goblins) {
			a.selectedIndex = max(0, len(a.goblins)-1)
		}
		return a, nil

	case errMsg:
		a.err = msg.err
		return a, nil

	case outputMsg:
		a.output = msg.lines
		return a, nil
	}

	return a, nil
}

// handleKeyPress processes keyboard input
func (a *App) handleKeyPress(msg tea.KeyMsg) (tea.Model, tea.Cmd) {
	// Handle based on active view
	if a.activeView == ViewHelp {
		// Any key exits help
		a.activeView = ViewDashboard
		return a, nil
	}

	switch msg.String() {
	case "q", "ctrl+c":
		return a, tea.Quit

	case "?":
		a.activeView = ViewHelp
		return a, nil

	case "j", "down":
		if len(a.goblins) > 0 {
			a.selectedIndex = (a.selectedIndex + 1) % len(a.goblins)
		}
		return a, nil

	case "k", "up":
		if len(a.goblins) > 0 {
			a.selectedIndex = (a.selectedIndex - 1 + len(a.goblins)) % len(a.goblins)
		}
		return a, nil

	case "a", "enter":
		return a, a.attachToSelected()

	case "s":
		return a, a.stopSelected()

	case "K": // Shift+K for kill
		return a, a.killSelected()

	case "p":
		return a, a.pauseSelected()

	case "r":
		return a, a.refreshGoblins()

	case "d":
		return a, a.showDiff()
	}

	return a, nil
}

// attachToSelected attaches to the selected goblin's tmux session
func (a *App) attachToSelected() tea.Cmd {
	if len(a.goblins) == 0 || a.coordinator == nil {
		return nil
	}
	goblin := a.goblins[a.selectedIndex]

	return tea.ExecProcess(
		tea.Command("tmux", "-L", "gforge", "attach-session", "-t", goblin.TmuxSession),
		func(err error) tea.Msg {
			return a.refreshGoblins()()
		},
	)
}

// stopSelected stops the selected goblin
func (a *App) stopSelected() tea.Cmd {
	if len(a.goblins) == 0 || a.coordinator == nil {
		return nil
	}
	goblin := a.goblins[a.selectedIndex]

	return func() tea.Msg {
		err := a.coordinator.Stop(goblin.Name)
		if err != nil {
			return errMsg{err}
		}
		return a.refreshGoblins()()
	}
}

// killSelected kills the selected goblin
func (a *App) killSelected() tea.Cmd {
	if len(a.goblins) == 0 || a.coordinator == nil {
		return nil
	}
	goblin := a.goblins[a.selectedIndex]

	return func() tea.Msg {
		err := a.coordinator.Kill(goblin.Name)
		if err != nil {
			return errMsg{err}
		}
		return a.refreshGoblins()()
	}
}

// pauseSelected pauses the selected goblin (placeholder)
func (a *App) pauseSelected() tea.Cmd {
	// TODO: Implement pause functionality
	return nil
}

// showDiff shows the diff for the selected goblin (placeholder)
func (a *App) showDiff() tea.Cmd {
	// TODO: Implement diff view
	return nil
}

// View implements tea.Model
func (a *App) View() string {
	if a.width == 0 {
		return "Loading..."
	}

	if a.activeView == ViewHelp {
		return a.renderHelp()
	}

	return a.renderDashboard()
}

// renderDashboard renders the main dashboard view
func (a *App) renderDashboard() string {
	// Calculate dimensions
	headerHeight := 3
	footerHeight := 2
	bodyHeight := a.height - headerHeight - footerHeight

	if bodyHeight < 5 {
		bodyHeight = 5
	}

	// Render sections
	header := a.renderHeader()
	body := a.renderBody(bodyHeight)
	footer := a.renderFooter()

	return lipgloss.JoinVertical(
		lipgloss.Left,
		header,
		body,
		footer,
	)
}

// renderHeader renders the top header bar
func (a *App) renderHeader() string {
	titleStyle := lipgloss.NewStyle().
		Bold(true).
		Foreground(lipgloss.Color("#7D56F4")).
		Padding(0, 1)

	versionStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("#666666"))

	voiceStatus := "OFF"
	voiceColor := lipgloss.Color("#666666")
	if a.voiceEnabled {
		voiceStatus = "ON"
		voiceColor = lipgloss.Color("#04B575")
	}

	voiceStyle := lipgloss.NewStyle().
		Foreground(voiceColor)

	title := titleStyle.Render("GOBLIN FORGE")
	version := versionStyle.Render(fmt.Sprintf("v%s", AppVersion))
	voice := voiceStyle.Render(fmt.Sprintf("Voice: %s", voiceStatus))
	quit := lipgloss.NewStyle().Foreground(lipgloss.Color("#666666")).Render("q: quit")

	// Calculate spacing
	leftPart := title + " " + version
	rightPart := voice + "  " + quit

	spacer := strings.Repeat(" ", max(0, a.width-lipgloss.Width(leftPart)-lipgloss.Width(rightPart)-2))

	headerContent := leftPart + spacer + rightPart

	headerStyle := lipgloss.NewStyle().
		BorderStyle(lipgloss.NormalBorder()).
		BorderBottom(true).
		BorderForeground(lipgloss.Color("#333333")).
		Width(a.width)

	return headerStyle.Render(headerContent)
}

// renderBody renders the main body with goblin list and output panel
func (a *App) renderBody(height int) string {
	// Split width: 40% goblin list, 60% output
	listWidth := a.width * 40 / 100
	outputWidth := a.width - listWidth - 1

	goblinList := a.renderGoblinList(listWidth, height)
	outputPanel := a.renderOutputPanel(outputWidth, height)

	return lipgloss.JoinHorizontal(
		lipgloss.Top,
		goblinList,
		outputPanel,
	)
}

// renderGoblinList renders the goblin list panel
func (a *App) renderGoblinList(width, height int) string {
	titleStyle := lipgloss.NewStyle().
		Bold(true).
		Foreground(lipgloss.Color("#FAFAFA")).
		MarginBottom(1)

	title := titleStyle.Render(fmt.Sprintf("GOBLINS (%d)", len(a.goblins)))

	var lines []string
	lines = append(lines, title)
	lines = append(lines, strings.Repeat("-", width-2))

	if len(a.goblins) == 0 {
		emptyStyle := lipgloss.NewStyle().
			Foreground(lipgloss.Color("#666666")).
			Italic(true)
		lines = append(lines, emptyStyle.Render("No active goblins"))
		lines = append(lines, "")
		lines = append(lines, emptyStyle.Render("Press 'n' to spawn one"))
	} else {
		for i, g := range a.goblins {
			line := a.renderGoblinLine(i, g, width-4)
			lines = append(lines, line)
		}
	}

	content := strings.Join(lines, "\n")

	panelStyle := lipgloss.NewStyle().
		Width(width).
		Height(height).
		BorderStyle(lipgloss.NormalBorder()).
		BorderRight(true).
		BorderForeground(lipgloss.Color("#333333")).
		Padding(0, 1)

	return panelStyle.Render(content)
}

// renderGoblinLine renders a single goblin entry
func (a *App) renderGoblinLine(index int, g *coordinator.Goblin, width int) string {
	isSelected := index == a.selectedIndex

	// Status indicator
	var statusIcon string
	var statusColor lipgloss.Color
	switch g.Status {
	case "running":
		statusIcon = "▶"
		statusColor = lipgloss.Color("#04B575")
	case "paused":
		statusIcon = "⏸"
		statusColor = lipgloss.Color("#FFCC00")
	case "stopped":
		statusIcon = "■"
		statusColor = lipgloss.Color("#666666")
	default:
		statusIcon = "○"
		statusColor = lipgloss.Color("#666666")
	}

	// Build line
	prefix := "  "
	if isSelected {
		prefix = "▶ "
	}

	nameStyle := lipgloss.NewStyle()
	if isSelected {
		nameStyle = nameStyle.Bold(true).Foreground(lipgloss.Color("#FAFAFA"))
	} else {
		nameStyle = nameStyle.Foreground(lipgloss.Color("#AAAAAA"))
	}

	agentStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("#7D56F4"))

	statusStyle := lipgloss.NewStyle().
		Foreground(statusColor)

	ageStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("#666666"))

	name := nameStyle.Render(truncate(g.Name, 12))
	agent := agentStyle.Render(fmt.Sprintf("[%s]", truncate(g.Agent, 8)))
	status := statusStyle.Render(statusIcon)
	age := ageStyle.Render(g.Age())

	return fmt.Sprintf("%s%d. %s %s %s %s", prefix, index+1, name, agent, status, age)
}

// renderOutputPanel renders the output panel
func (a *App) renderOutputPanel(width, height int) string {
	var selectedName, selectedAgent string
	if len(a.goblins) > 0 && a.selectedIndex < len(a.goblins) {
		g := a.goblins[a.selectedIndex]
		selectedName = g.Name
		selectedAgent = g.Agent
	}

	titleStyle := lipgloss.NewStyle().
		Bold(true).
		Foreground(lipgloss.Color("#FAFAFA")).
		MarginBottom(1)

	title := "OUTPUT"
	if selectedName != "" {
		title = fmt.Sprintf("OUTPUT: %s [%s]", selectedName, selectedAgent)
	}

	var lines []string
	lines = append(lines, titleStyle.Render(title))
	lines = append(lines, strings.Repeat("-", width-4))

	if len(a.output) == 0 {
		emptyStyle := lipgloss.NewStyle().
			Foreground(lipgloss.Color("#666666")).
			Italic(true)
		lines = append(lines, emptyStyle.Render("No output yet"))
		lines = append(lines, "")
		lines = append(lines, emptyStyle.Render("Select a goblin and press 'a' to attach"))
	} else {
		for _, line := range a.output {
			lines = append(lines, truncate(line, width-4))
		}
	}

	content := strings.Join(lines, "\n")

	panelStyle := lipgloss.NewStyle().
		Width(width).
		Height(height).
		Padding(0, 1)

	return panelStyle.Render(content)
}

// renderFooter renders the bottom keybinding bar
func (a *App) renderFooter() string {
	keyStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("#7D56F4")).
		Bold(true)

	descStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("#666666"))

	bindings := []struct {
		key  string
		desc string
	}{
		{"a", "attach"},
		{"s", "stop"},
		{"K", "kill"},
		{"d", "diff"},
		{"r", "refresh"},
		{"?", "help"},
	}

	var parts []string
	for _, b := range bindings {
		parts = append(parts, keyStyle.Render(b.key)+":"+descStyle.Render(b.desc))
	}

	content := strings.Join(parts, "  ")

	footerStyle := lipgloss.NewStyle().
		BorderStyle(lipgloss.NormalBorder()).
		BorderTop(true).
		BorderForeground(lipgloss.Color("#333333")).
		Width(a.width).
		Padding(0, 1)

	return footerStyle.Render(content)
}

// renderHelp renders the help view
func (a *App) renderHelp() string {
	titleStyle := lipgloss.NewStyle().
		Bold(true).
		Foreground(lipgloss.Color("#7D56F4")).
		MarginBottom(2)

	sectionStyle := lipgloss.NewStyle().
		Bold(true).
		Foreground(lipgloss.Color("#FAFAFA")).
		MarginTop(1)

	keyStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("#7D56F4")).
		Width(15)

	descStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("#AAAAAA"))

	var lines []string
	lines = append(lines, titleStyle.Render("GOBLIN FORGE - KEYBINDINGS"))
	lines = append(lines, "")

	lines = append(lines, sectionStyle.Render("Navigation"))
	lines = append(lines, keyStyle.Render("j / Down")+"  "+descStyle.Render("Select next goblin"))
	lines = append(lines, keyStyle.Render("k / Up")+"  "+descStyle.Render("Select previous goblin"))
	lines = append(lines, keyStyle.Render("Enter / a")+"  "+descStyle.Render("Attach to selected goblin"))
	lines = append(lines, "")

	lines = append(lines, sectionStyle.Render("Actions"))
	lines = append(lines, keyStyle.Render("s")+"  "+descStyle.Render("Stop selected goblin"))
	lines = append(lines, keyStyle.Render("K (Shift+k)")+"  "+descStyle.Render("Kill selected goblin"))
	lines = append(lines, keyStyle.Render("p")+"  "+descStyle.Render("Pause selected goblin"))
	lines = append(lines, keyStyle.Render("d")+"  "+descStyle.Render("Show diff for selected goblin"))
	lines = append(lines, keyStyle.Render("r")+"  "+descStyle.Render("Refresh goblin list"))
	lines = append(lines, "")

	lines = append(lines, sectionStyle.Render("General"))
	lines = append(lines, keyStyle.Render("?")+"  "+descStyle.Render("Toggle this help"))
	lines = append(lines, keyStyle.Render("q / Ctrl+C")+"  "+descStyle.Render("Quit"))
	lines = append(lines, "")
	lines = append(lines, "")

	footerStyle := lipgloss.NewStyle().
		Foreground(lipgloss.Color("#666666")).
		Italic(true)
	lines = append(lines, footerStyle.Render("Press any key to return to dashboard"))

	content := strings.Join(lines, "\n")

	boxStyle := lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(lipgloss.Color("#7D56F4")).
		Padding(2, 4).
		Width(60)

	// Center the help box
	helpBox := boxStyle.Render(content)

	return lipgloss.Place(
		a.width,
		a.height,
		lipgloss.Center,
		lipgloss.Center,
		helpBox,
	)
}

// Helper functions
func truncate(s string, maxLen int) string {
	if len(s) <= maxLen {
		return s
	}
	if maxLen <= 3 {
		return s[:maxLen]
	}
	return s[:maxLen-3] + "..."
}

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}

// Run starts the TUI application
func Run(coord *coordinator.Coordinator) error {
	app := New(coord)
	p := tea.NewProgram(app, tea.WithAltScreen())
	_, err := p.Run()
	return err
}
