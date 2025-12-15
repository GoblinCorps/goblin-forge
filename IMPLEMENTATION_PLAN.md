# Goblin Forge — Strategic Implementation Plan

> Phased development roadmap with features, deliverables, and test criteria per phase.

---

## Executive Summary

| Metric | Target |
|--------|--------|
| Total Phases | 8 |
| Core MVP | Phase 4 (CLI + Agents + TUI) |
| Full Release | Phase 8 |
| Primary Language | Go 1.22+ |
| Voice Subsystem | Python 3.10+ |
| License | Apache-2.0 |

---

## Phase Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        IMPLEMENTATION ROADMAP                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  PHASE 1        PHASE 2        PHASE 3        PHASE 4                      │
│  Foundation     Isolation      Agents         TUI                          │
│  ──────────     ─────────      ──────         ───                          │
│  • CLI scaffold • tmux mgmt    • Registry     • Dashboard                  │
│  • Config       • git worktree • Discovery    • Goblin list                │
│  • Storage      • Session life • Adapters     • Output view                │
│  • Project init • Output capture• 5+ agents   • Keybindings                │
│                                                                             │
│       │              │              │              │                        │
│       ▼              ▼              ▼              ▼                        │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐                  │
│  │   v0.1  │───▶│   v0.2  │───▶│   v0.3  │───▶│   v0.4  │   MVP           │
│  └─────────┘    └─────────┘    └─────────┘    └─────────┘   RELEASE        │
│                                                                             │
│  PHASE 5        PHASE 6        PHASE 7        PHASE 8                      │
│  Templates      Voice          Integrations   Polish                       │
│  ─────────      ─────          ────────────   ──────                       │
│  • Engine       • Whisper STT  • GitHub       • Docs                       │
│  • 40+ builtin  • Hotkey daemon• Linear/Jira  • Packaging                  │
│  • Auto-detect  • Commands     • Editors      • Community                  │
│  • Custom       • IPC layer    • PR workflow  • v1.0 release               │
│                                                                             │
│       │              │              │              │                        │
│       ▼              ▼              ▼              ▼                        │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐                  │
│  │   v0.5  │───▶│   v0.6  │───▶│   v0.7  │───▶│   v1.0  │   STABLE        │
│  └─────────┘    └─────────┘    └─────────┘    └─────────┘   RELEASE        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Foundation

### Objective
Establish project structure, CLI framework, configuration system, and storage layer.

### Deliverables

| ID | Feature | Description | Priority |
|----|---------|-------------|----------|
| 1.1 | Project Scaffold | Go module, directory structure, Makefile | P0 |
| 1.2 | CLI Framework | Cobra-based CLI with subcommand structure | P0 |
| 1.3 | Configuration | Viper-based YAML config loading | P0 |
| 1.4 | SQLite Storage | Pure Go SQLite with migrations | P0 |
| 1.5 | Logging | Structured logging (zerolog) | P0 |
| 1.6 | Error Handling | Consistent error types and messages | P1 |
| 1.7 | Version Command | `gforge version` with build info | P1 |

### Implementation Details

```go
// cmd/gforge/main.go
package main

import (
    "github.com/spf13/cobra"
    "github.com/your-org/goblin-forge/internal/config"
    "github.com/your-org/goblin-forge/internal/storage"
)

func main() {
    rootCmd := &cobra.Command{
        Use:   "gforge",
        Short: "Multi-agent CLI orchestrator",
    }

    // Initialize config
    cfg := config.Load()

    // Initialize storage
    db := storage.NewSQLite(cfg.DatabasePath)

    // Register commands
    rootCmd.AddCommand(
        newVersionCmd(),
        newConfigCmd(cfg),
        // ... more commands added in later phases
    )

    rootCmd.Execute()
}
```

### Directory Structure (Phase 1)

```
goblin-forge/
├── cmd/gforge/main.go
├── internal/
│   ├── config/
│   │   ├── config.go
│   │   ├── defaults.go
│   │   └── validation.go
│   ├── storage/
│   │   ├── sqlite.go
│   │   ├── models.go
│   │   └── migrations/
│   │       └── 001_initial.sql
│   └── logging/
│       └── logger.go
├── configs/
│   └── default-config.yaml
├── go.mod
├── go.sum
├── Makefile
└── README.md
```

### Test Criteria

| Test ID | Test Case | Expected Result |
|---------|-----------|-----------------|
| T1.1 | `gforge version` | Displays version, commit, build date |
| T1.2 | `gforge config show` | Displays current configuration |
| T1.3 | Config file parsing | Loads YAML without errors |
| T1.4 | Missing config | Creates default config |
| T1.5 | SQLite connection | Opens/creates database |
| T1.6 | Migration run | Tables created successfully |
| T1.7 | Invalid config | Returns clear error message |

### Acceptance Criteria

- [ ] `go build` produces working binary
- [ ] `gforge version` outputs version info
- [ ] `gforge config show` displays configuration
- [ ] SQLite database created at configured path
- [ ] All migrations run successfully
- [ ] 100% test pass rate for Phase 1 tests
- [ ] No linting errors (`golangci-lint run`)

### Exit Criteria

```bash
# All must pass
gforge version                    # Shows version
gforge config show                # Shows config
go test ./internal/config/...     # Config tests pass
go test ./internal/storage/...    # Storage tests pass
```

---

## Phase 2: Isolation Layer

### Objective
Implement tmux session management and git worktree isolation for goblin sandboxing.

### Deliverables

| ID | Feature | Description | Priority |
|----|---------|-------------|----------|
| 2.1 | tmux Manager | Create/attach/kill tmux sessions | P0 |
| 2.2 | Session Lifecycle | Start, pause, resume, stop states | P0 |
| 2.3 | Output Capture | Capture goblin output via pipe-pane | P0 |
| 2.4 | Git Worktree | Create isolated worktrees per goblin | P0 |
| 2.5 | Branch Management | Auto-create feature branches | P0 |
| 2.6 | Cleanup | Remove worktrees/sessions on stop | P1 |
| 2.7 | Session Persistence | Survive gforge restart | P1 |

### Implementation Details

```go
// internal/tmux/manager.go
package tmux

type Manager struct {
    socketName string
    sessions   map[string]*Session
}

type Session struct {
    ID         string
    Name       string
    Status     SessionStatus
    WorktreePath string
    CreatedAt  time.Time
}

func (m *Manager) Create(name string, workdir string) (*Session, error) {
    sessionID := generateID()

    // Create tmux session
    cmd := exec.Command("tmux", "-L", m.socketName,
        "new-session", "-d", "-s", sessionID, "-c", workdir)

    if err := cmd.Run(); err != nil {
        return nil, fmt.Errorf("failed to create tmux session: %w", err)
    }

    // Setup output capture
    m.setupOutputCapture(sessionID)

    session := &Session{
        ID:        sessionID,
        Name:      name,
        Status:    StatusCreated,
        CreatedAt: time.Now(),
    }

    m.sessions[sessionID] = session
    return session, nil
}

func (m *Manager) Attach(sessionID string) error {
    return exec.Command("tmux", "-L", m.socketName,
        "attach-session", "-t", sessionID).Run()
}
```

```go
// internal/workspace/worktree.go
package workspace

type WorktreeManager struct {
    basePath string
    repo     *git.Repository
}

func (w *WorktreeManager) Create(goblinID, branchName string) (string, error) {
    worktreePath := filepath.Join(w.basePath, goblinID)

    // Create git worktree
    cmd := exec.Command("git", "worktree", "add",
        "-b", branchName, worktreePath)

    if err := cmd.Run(); err != nil {
        return "", fmt.Errorf("failed to create worktree: %w", err)
    }

    return worktreePath, nil
}

func (w *WorktreeManager) Remove(goblinID string) error {
    worktreePath := filepath.Join(w.basePath, goblinID)

    // Remove git worktree
    cmd := exec.Command("git", "worktree", "remove", worktreePath)
    return cmd.Run()
}
```

### CLI Commands Added

```bash
# Internal commands (used by later phases)
gforge session create <name> --workdir <path>
gforge session attach <id>
gforge session list
gforge session kill <id>
gforge worktree create <goblin-id> --branch <name>
gforge worktree remove <goblin-id>
```

### Test Criteria

| Test ID | Test Case | Expected Result |
|---------|-----------|-----------------|
| T2.1 | Create tmux session | Session created, listed in `tmux ls` |
| T2.2 | Attach to session | Terminal switches to session |
| T2.3 | Kill session | Session removed, cleanup complete |
| T2.4 | Output capture | Can read session output |
| T2.5 | Create worktree | Directory created, branch exists |
| T2.6 | Remove worktree | Directory removed, git worktree list updated |
| T2.7 | Concurrent sessions | Multiple sessions work independently |
| T2.8 | Session persistence | Sessions survive gforge restart |

### Acceptance Criteria

- [ ] Can create tmux session programmatically
- [ ] Can attach to running session
- [ ] Output capture works via pipe-pane
- [ ] Git worktrees created in configured location
- [ ] Branches auto-created with correct naming
- [ ] Cleanup removes both session and worktree
- [ ] Sessions persist across gforge restart
- [ ] 100% test pass rate for Phase 2 tests

### Exit Criteria

```bash
# All must pass
gforge session create test-session --workdir /tmp/test
gforge session list                        # Shows test-session
gforge session attach test-session         # Attaches successfully
# (detach with Ctrl+B D)
gforge session kill test-session           # Removes cleanly
go test ./internal/tmux/...                # tmux tests pass
go test ./internal/workspace/...           # workspace tests pass
```

---

## Phase 3: Agent System

### Objective
Implement agent registry, auto-discovery, and adapters for 5+ CLI agents.

### Deliverables

| ID | Feature | Description | Priority |
|----|---------|-------------|----------|
| 3.1 | Agent Registry | Central registry for agent definitions | P0 |
| 3.2 | Auto-Discovery | Scan PATH for known agents | P0 |
| 3.3 | Claude Adapter | Full Claude Code CLI integration | P0 |
| 3.4 | Aider Adapter | Aider CLI integration | P0 |
| 3.5 | Codex Adapter | OpenAI Codex CLI integration | P1 |
| 3.6 | Gemini Adapter | Google Gemini CLI integration | P1 |
| 3.7 | Generic Adapter | Support custom CLI agents | P1 |
| 3.8 | Capability System | Track agent capabilities | P1 |
| 3.9 | Spawn Command | `gforge spawn` implementation | P0 |
| 3.10 | List Command | `gforge list` implementation | P0 |

### Implementation Details

```go
// internal/agents/registry.go
package agents

type Registry struct {
    agents   map[string]*AgentDefinition
    detected map[string]*DetectedAgent
}

type AgentDefinition struct {
    Name         string
    Command      string
    Args         []string
    Env          map[string]string
    Capabilities []string
    Detection    DetectionConfig
}

type DetectionConfig struct {
    Binary     string
    VersionCmd string
    ConfigPaths []string
}

func (r *Registry) Scan() ([]DetectedAgent, error) {
    var detected []DetectedAgent

    for name, def := range r.agents {
        path, err := exec.LookPath(def.Detection.Binary)
        if err != nil {
            continue // Not installed
        }

        version := r.getVersion(def)

        detected = append(detected, DetectedAgent{
            Name:    name,
            Path:    path,
            Version: version,
        })
    }

    return detected, nil
}
```

```go
// internal/agents/claude.go
package agents

type ClaudeAdapter struct {
    definition *AgentDefinition
}

func NewClaudeAdapter() *ClaudeAdapter {
    return &ClaudeAdapter{
        definition: &AgentDefinition{
            Name:    "claude",
            Command: "claude",
            Args:    []string{},
            Capabilities: []string{"code", "git", "fs", "web", "mcp"},
            Detection: DetectionConfig{
                Binary:     "claude",
                VersionCmd: "claude --version",
                ConfigPaths: []string{"~/.claude", "~/.config/claude"},
            },
        },
    }
}

func (a *ClaudeAdapter) Spawn(session *tmux.Session, task string) error {
    // Send command to tmux session
    cmd := fmt.Sprintf("%s %s", a.definition.Command,
        strings.Join(a.definition.Args, " "))

    return session.SendKeys(cmd)
}
```

```go
// internal/coordinator/goblin.go
package coordinator

type Goblin struct {
    ID           string
    Name         string
    Agent        string
    Status       GoblinStatus
    Session      *tmux.Session
    Worktree     string
    Branch       string
    Capabilities []string
    CreatedAt    time.Time
    UpdatedAt    time.Time
}

type GoblinStatus string

const (
    StatusCreated  GoblinStatus = "created"
    StatusRunning  GoblinStatus = "running"
    StatusPaused   GoblinStatus = "paused"
    StatusComplete GoblinStatus = "complete"
)
```

### CLI Commands Added

```bash
# Agent management
gforge agents scan           # Auto-discover installed agents
gforge agents list           # List available agents
gforge agents add <name>     # Add custom agent

# Goblin management
gforge spawn <name> --agent <agent> [--project <path>] [--branch <name>]
gforge list                  # List all goblins
gforge stop <name>           # Stop goblin
gforge kill <name>           # Force kill
gforge attach <name>         # Attach to goblin session
gforge rename <name> <new>   # Rename goblin
```

### Test Criteria

| Test ID | Test Case | Expected Result |
|---------|-----------|-----------------|
| T3.1 | Agent scan | Discovers installed agents |
| T3.2 | Agent list | Shows all available agents |
| T3.3 | Spawn Claude | Creates goblin with Claude |
| T3.4 | Spawn Aider | Creates goblin with Aider |
| T3.5 | Spawn custom | Creates goblin with custom agent |
| T3.6 | List goblins | Shows all active goblins |
| T3.7 | Stop goblin | Goblin stops cleanly |
| T3.8 | Attach goblin | Attaches to goblin session |
| T3.9 | Rename goblin | Name updated in list |
| T3.10 | Missing agent | Clear error message |

### Acceptance Criteria

- [ ] `gforge agents scan` discovers installed agents
- [ ] `gforge spawn` creates isolated goblin
- [ ] Claude adapter works correctly
- [ ] Aider adapter works correctly
- [ ] At least 3 additional agents supported
- [ ] Custom agent definition works
- [ ] Capabilities tracked per agent
- [ ] 100% test pass rate for Phase 3 tests

### Exit Criteria

```bash
# All must pass
gforge agents scan                              # Shows detected agents
gforge spawn coder --agent claude --project .   # Creates goblin
gforge list                                     # Shows coder goblin
gforge attach coder                             # Attaches successfully
gforge stop coder                               # Stops cleanly
go test ./internal/agents/...                   # Agent tests pass
go test ./internal/coordinator/...              # Coordinator tests pass
```

---

## Phase 4: TUI Dashboard (MVP)

### Objective
Implement terminal user interface with dashboard, goblin list, output view, and keybindings.

### Deliverables

| ID | Feature | Description | Priority |
|----|---------|-------------|----------|
| 4.1 | TUI Framework | Bubble Tea app structure | P0 |
| 4.2 | Dashboard View | Main htop-like overview | P0 |
| 4.3 | Goblin List | Navigable goblin list | P0 |
| 4.4 | Output Panel | Real-time agent output | P0 |
| 4.5 | Keybindings | Full keyboard navigation | P0 |
| 4.6 | Status Bar | System status display | P1 |
| 4.7 | Help View | Keybinding reference | P1 |
| 4.8 | Theme Support | Dark/light themes | P2 |

### Implementation Details

```go
// internal/tui/app.go
package tui

import (
    tea "github.com/charmbracelet/bubbletea"
    "github.com/charmbracelet/lipgloss"
)

type App struct {
    coordinator *coordinator.Coordinator

    // Views
    dashboard   *DashboardView
    goblinList  *GoblinListView
    outputPanel *OutputPanelView

    // State
    activeView  ViewType
    selectedID  string
    width       int
    height      int
}

func (a *App) Init() tea.Cmd {
    return tea.Batch(
        a.tickCmd(),
        a.subscribeToEvents(),
    )
}

func (a *App) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
    switch msg := msg.(type) {
    case tea.KeyMsg:
        return a.handleKeyPress(msg)
    case tea.WindowSizeMsg:
        a.width = msg.Width
        a.height = msg.Height
        return a, nil
    case GoblinUpdateMsg:
        return a.handleGoblinUpdate(msg)
    }
    return a, nil
}

func (a *App) handleKeyPress(msg tea.KeyMsg) (tea.Model, tea.Cmd) {
    switch msg.String() {
    case "q", "ctrl+c":
        return a, tea.Quit
    case "n":
        return a, a.showSpawnDialog()
    case "a", "enter":
        return a, a.attachToSelected()
    case "d":
        return a, a.showDiff()
    case "k":
        return a, a.killSelected()
    case "p":
        return a, a.pauseSelected()
    case "j", "down":
        a.goblinList.SelectNext()
    case "k", "up":
        a.goblinList.SelectPrev()
    case "tab":
        a.cycleView()
    case "?":
        return a, a.showHelp()
    }
    return a, nil
}

func (a *App) View() string {
    // Layout:
    // ┌────────────────────────────────────────┐
    // │ Header                                 │
    // ├─────────────────┬──────────────────────┤
    // │ Goblin List     │ Output Panel         │
    // │                 │                      │
    // │                 │                      │
    // ├─────────────────┴──────────────────────┤
    // │ Status Bar / Keybindings              │
    // └────────────────────────────────────────┘

    header := a.renderHeader()
    body := lipgloss.JoinHorizontal(
        lipgloss.Top,
        a.goblinList.View(),
        a.outputPanel.View(),
    )
    footer := a.renderFooter()

    return lipgloss.JoinVertical(
        lipgloss.Left,
        header,
        body,
        footer,
    )
}
```

### TUI Layout

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  GOBLIN FORGE v0.4.0                              🎤 Voice: OFF   q: quit  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  GOBLINS (3)                           │  OUTPUT: coder [Claude]           │
│  ─────────────────────────────────────  │  ─────────────────────────────────│
│  ▶ 1. coder        [Claude]   RUNNING  │  │ Analyzing the authentication   │
│    2. reviewer     [Aider]    PAUSED   │  │ module for potential issues... │
│    3. tester       [Codex]    IDLE     │  │                                │
│                                        │  │ Found 3 issues:                │
│                                        │  │ 1. JWT not validated properly  │
│                                        │  │ 2. Session timeout too long    │
│                                        │  │ 3. Missing rate limiting       │
│                                        │  │                                │
│                                        │  │ Starting fix for issue 1...    │
│                                        │  │ ████████████░░░░░░░░ 60%       │
│                                        │  │                                │
│                                        │  └──────────────────────────────── │
│                                                                             │
│  n:spawn  a:attach  d:diff  k:kill  p:pause  r:resume  tab:switch  ?:help │
└─────────────────────────────────────────────────────────────────────────────┘
```

### CLI Commands Added

```bash
gforge top            # Launch TUI dashboard
gforge top --minimal  # Minimal view
```

### Test Criteria

| Test ID | Test Case | Expected Result |
|---------|-----------|-----------------|
| T4.1 | Launch TUI | Dashboard renders correctly |
| T4.2 | Goblin list | Shows all active goblins |
| T4.3 | Selection | Arrow keys navigate list |
| T4.4 | Output panel | Shows selected goblin output |
| T4.5 | Spawn from TUI | 'n' opens spawn dialog |
| T4.6 | Attach from TUI | 'a' attaches to selected |
| T4.7 | Kill from TUI | 'k' kills selected goblin |
| T4.8 | Quit | 'q' exits cleanly |
| T4.9 | Resize | Layout adapts to terminal size |
| T4.10 | Help | '?' shows keybindings |

### Acceptance Criteria

- [ ] `gforge top` launches TUI dashboard
- [ ] Goblin list shows all active goblins
- [ ] Output panel shows real-time output
- [ ] All keybindings functional
- [ ] Status bar shows system state
- [ ] Help view accessible
- [ ] TUI handles terminal resize
- [ ] 100% test pass rate for Phase 4 tests

### Exit Criteria

```bash
# All must pass
gforge top                           # Launches TUI
# (navigate with arrow keys, spawn with 'n', etc.)
go test ./internal/tui/...           # TUI tests pass
```

### MVP Release Checklist

At the end of Phase 4, the MVP (v0.4.0) should support:

- [x] CLI with all core commands
- [x] Configuration management
- [x] SQLite persistence
- [x] tmux session isolation
- [x] Git worktree isolation
- [x] 5+ agent adapters
- [x] Agent auto-discovery
- [x] TUI dashboard
- [x] Basic documentation

---

## Phase 5: Template System

### Objective
Implement template engine with 40+ built-in templates and auto-detection.

### Deliverables

| ID | Feature | Description | Priority |
|----|---------|-------------|----------|
| 5.1 | Template Engine | YAML-based template processing | P0 |
| 5.2 | Auto-Detection | Detect project type from files | P0 |
| 5.3 | Node.js Templates | nodejs, pnpm, bun, nextjs, vite | P0 |
| 5.4 | Python Templates | python, uv, poetry, fastapi, django | P0 |
| 5.5 | Rust Templates | rust, cargo | P0 |
| 5.6 | Go Templates | golang | P0 |
| 5.7 | Other Languages | ruby, java, dotnet, elixir, c++ | P1 |
| 5.8 | Workflow Templates | pr-review, release, security | P1 |
| 5.9 | Custom Templates | User-defined templates | P1 |
| 5.10 | Template Commands | Run build/test/dev via templates | P0 |

### Implementation Details

```go
// internal/template/engine.go
package template

type Engine struct {
    builtin  map[string]*Template
    custom   map[string]*Template
    detector *Detector
}

type Template struct {
    Name        string              `yaml:"name"`
    Description string              `yaml:"description"`
    Extends     string              `yaml:"extends"`
    Detect      DetectionRules      `yaml:"detect"`
    Variables   map[string]string   `yaml:"variables"`
    Setup       []SetupStep         `yaml:"setup"`
    Commands    map[string]string   `yaml:"commands"`
    Ports       []int               `yaml:"ports"`
    AgentContext string             `yaml:"agent_context"`
}

type DetectionRules struct {
    Files   []string        `yaml:"files"`
    Content []ContentMatch  `yaml:"content"`
}

func (e *Engine) Detect(projectPath string) (*Template, error) {
    // Check for marker files
    for name, tmpl := range e.builtin {
        if e.matchesDetection(projectPath, tmpl.Detect) {
            return tmpl, nil
        }
    }
    return nil, ErrNoTemplateMatch
}

func (e *Engine) Apply(tmpl *Template, goblin *Goblin) error {
    // Resolve variables
    vars := e.resolveVariables(tmpl, goblin)

    // Run setup steps
    for _, step := range tmpl.Setup {
        if err := e.runSetupStep(step, vars, goblin); err != nil {
            return err
        }
    }

    // Register commands
    goblin.Commands = e.resolveCommands(tmpl.Commands, vars)

    return nil
}
```

### Built-in Templates (40+)

```
templates/builtin/
├── languages/
│   ├── nodejs.yaml
│   ├── nodejs-pnpm.yaml
│   ├── nodejs-bun.yaml
│   ├── python.yaml
│   ├── python-uv.yaml
│   ├── python-poetry.yaml
│   ├── rust.yaml
│   ├── golang.yaml
│   ├── ruby.yaml
│   ├── java-maven.yaml
│   ├── java-gradle.yaml
│   ├── dotnet.yaml
│   ├── elixir.yaml
│   ├── c-cpp.yaml
│   └── zig.yaml
├── frameworks/
│   ├── nextjs.yaml
│   ├── vite.yaml
│   ├── remix.yaml
│   ├── astro.yaml
│   ├── fastapi.yaml
│   ├── django.yaml
│   ├── flask.yaml
│   ├── rails.yaml
│   ├── phoenix.yaml
│   ├── gin.yaml
│   └── actix.yaml
├── build/
│   ├── npm-build.yaml
│   ├── npm-test.yaml
│   ├── cargo-build.yaml
│   ├── cargo-test.yaml
│   ├── go-build.yaml
│   ├── go-test.yaml
│   ├── pytest.yaml
│   └── jest.yaml
└── workflows/
    ├── pr-review.yaml
    ├── conflict-resolve.yaml
    ├── release.yaml
    ├── security-audit.yaml
    └── refactor.yaml
```

### CLI Commands Added

```bash
gforge templates list              # List all templates
gforge templates list --category   # Filter by category
gforge templates show <name>       # Show template details
gforge templates create <name>     # Create custom template
gforge run <cmd> [goblin]          # Run template command
```

### Test Criteria

| Test ID | Test Case | Expected Result |
|---------|-----------|-----------------|
| T5.1 | Template list | Shows all 40+ templates |
| T5.2 | Auto-detect Node | Detects package.json → nodejs |
| T5.3 | Auto-detect Python | Detects pyproject.toml → python |
| T5.4 | Auto-detect Rust | Detects Cargo.toml → rust |
| T5.5 | Template setup | Runs setup steps correctly |
| T5.6 | Template commands | `run build` executes template command |
| T5.7 | Template inheritance | `extends` works correctly |
| T5.8 | Custom template | User template loads and works |
| T5.9 | Variable resolution | Variables replaced correctly |
| T5.10 | Missing template | Clear error message |

### Acceptance Criteria

- [ ] 40+ built-in templates included
- [ ] Auto-detection works for major project types
- [ ] Template setup steps execute correctly
- [ ] `gforge run build/test/dev` works
- [ ] Custom templates supported
- [ ] Template inheritance (`extends`) works
- [ ] 100% test pass rate for Phase 5 tests

---

## Phase 6: Voice Subsystem

### Objective
Implement local voice control via Whisper STT with hotkey activation and command parsing.

### Deliverables

| ID | Feature | Description | Priority |
|----|---------|-------------|----------|
| 6.1 | Voice Daemon | Python daemon for voice processing | P0 |
| 6.2 | Whisper Integration | faster-whisper for local STT | P0 |
| 6.3 | Hotkey Listener | Global hotkey via evdev | P0 |
| 6.4 | Command Parser | Parse voice to gforge commands | P0 |
| 6.5 | IPC Layer | Unix socket Go↔Python communication | P0 |
| 6.6 | Wake Word | Optional "Hey Forge" activation | P1 |
| 6.7 | Audio Feedback | Sound on start/stop recording | P2 |
| 6.8 | Model Selection | tiny/small/medium/large models | P1 |

### Implementation Details

```python
# voice/daemon.py
import asyncio
from faster_whisper import WhisperModel
from evdev import InputDevice, ecodes
import socket

class VoiceDaemon:
    def __init__(self, config):
        self.config = config
        self.model = WhisperModel(config['model'])
        self.socket_path = config['socket_path']
        self.recording = False

    async def start(self):
        # Start IPC server
        asyncio.create_task(self.ipc_server())

        # Start hotkey listener
        asyncio.create_task(self.hotkey_listener())

        # Run forever
        await asyncio.Event().wait()

    async def hotkey_listener(self):
        device = InputDevice('/dev/input/eventX')  # Keyboard

        async for event in device.async_read_loop():
            if self.is_hotkey(event):
                if not self.recording:
                    await self.start_recording()
                else:
                    await self.stop_recording()

    async def start_recording(self):
        self.recording = True
        self.audio_buffer = []
        # Start capturing audio

    async def stop_recording(self):
        self.recording = False

        # Transcribe
        segments, _ = self.model.transcribe(self.audio_buffer)
        text = " ".join([s.text for s in segments])

        # Parse command
        command = self.parse_command(text)

        # Send to Go via IPC
        await self.send_command(command)

    def parse_command(self, text):
        # Pattern matching for commands
        patterns = {
            r"spawn.*?(\w+).*?for (.+)": ("spawn", {"name": 1, "task": 2}),
            r"attach.*?(\w+)": ("attach", {"name": 1}),
            r"show diff": ("diff", {}),
            r"commit.*?with message (.+)": ("commit", {"message": 1}),
            # ... more patterns
        }

        for pattern, (action, groups) in patterns.items():
            match = re.match(pattern, text.lower())
            if match:
                return {"action": action, "params": extract_groups(match, groups)}

        return {"action": "unknown", "raw": text}
```

```go
// internal/ipc/client.go
package ipc

type VoiceClient struct {
    socketPath string
    conn       net.Conn
}

func (c *VoiceClient) Listen(handler func(VoiceCommand)) error {
    for {
        // Read from socket
        var cmd VoiceCommand
        if err := json.NewDecoder(c.conn).Decode(&cmd); err != nil {
            return err
        }

        handler(cmd)
    }
}

type VoiceCommand struct {
    Action string            `json:"action"`
    Params map[string]string `json:"params"`
    Raw    string            `json:"raw"`
}
```

### CLI Commands Added

```bash
gforge voice setup      # Install voice dependencies
gforge voice start      # Start voice daemon
gforge voice stop       # Stop voice daemon
gforge voice status     # Show voice status
gforge voice test       # Test microphone
```

### Test Criteria

| Test ID | Test Case | Expected Result |
|---------|-----------|-----------------|
| T6.1 | Daemon start | Voice daemon starts successfully |
| T6.2 | Daemon stop | Daemon stops cleanly |
| T6.3 | Hotkey detection | Hotkey triggers recording |
| T6.4 | Transcription | Audio transcribed accurately |
| T6.5 | Command parsing | "spawn coder" → spawn command |
| T6.6 | IPC communication | Commands reach Go process |
| T6.7 | Model loading | Whisper model loads |
| T6.8 | Error handling | Graceful handling of errors |

### Acceptance Criteria

- [ ] Voice daemon starts/stops correctly
- [ ] Hotkey activates recording
- [ ] Whisper transcribes accurately
- [ ] Commands parsed and executed
- [ ] IPC communication works
- [ ] Multiple model sizes supported
- [ ] 100% test pass rate for Phase 6 tests

---

## Phase 7: Integrations

### Objective
Implement GitHub, Linear, Jira integrations and editor launching.

### Deliverables

| ID | Feature | Description | Priority |
|----|---------|-------------|----------|
| 7.1 | GitHub Issues | Import issues as tasks | P0 |
| 7.2 | GitHub PRs | Create PRs from goblin changes | P0 |
| 7.3 | Linear Integration | Import/sync Linear tickets | P1 |
| 7.4 | Jira Integration | Import/sync Jira issues | P1 |
| 7.5 | Editor Launch | Open editor at worktree | P0 |
| 7.6 | Port Tracking | Track dev server ports | P1 |
| 7.7 | Diff Command | Show goblin changes | P0 |
| 7.8 | Commit Command | Commit with smart messages | P0 |
| 7.9 | PR Command | Create PR with template | P0 |

### Implementation Details

```go
// internal/integrations/github.go
package integrations

type GitHubClient struct {
    // Uses gh CLI under the hood
}

func (g *GitHubClient) ImportIssue(ref string) (*Issue, error) {
    // Parse ref: "gh:owner/repo#123"
    owner, repo, number := parseIssueRef(ref)

    // Use gh CLI
    cmd := exec.Command("gh", "issue", "view",
        fmt.Sprintf("%d", number),
        "--repo", fmt.Sprintf("%s/%s", owner, repo),
        "--json", "title,body,labels")

    output, err := cmd.Output()
    if err != nil {
        return nil, err
    }

    var issue Issue
    json.Unmarshal(output, &issue)
    return &issue, nil
}

func (g *GitHubClient) CreatePR(goblin *Goblin, opts PROptions) (*PR, error) {
    // Generate PR body from commits
    body := g.generatePRBody(goblin, opts)

    cmd := exec.Command("gh", "pr", "create",
        "--title", opts.Title,
        "--body", body,
        "--head", goblin.Branch)

    return cmd.Output()
}
```

### CLI Commands Added

```bash
# Issue integration
gforge spawn coder --from-issue gh:owner/repo#123
gforge spawn coder --from-issue linear:PROJ-456
gforge spawn coder --from-issue jira:PROJ-789

# Git operations
gforge diff <goblin>              # Show changes
gforge commit <goblin> -m "msg"   # Commit changes
gforge push <goblin>              # Push branch
gforge pr <goblin>                # Create PR
gforge merge <goblin>             # Merge to main

# Editor
gforge edit <goblin>              # Open in $EDITOR
gforge edit <goblin> --editor code
```

### Test Criteria

| Test ID | Test Case | Expected Result |
|---------|-----------|-----------------|
| T7.1 | Import GH issue | Issue imported as task |
| T7.2 | Create PR | PR created with template |
| T7.3 | Linear import | Linear ticket imported |
| T7.4 | Diff command | Shows goblin changes |
| T7.5 | Commit command | Commits with message |
| T7.6 | Editor launch | Opens correct directory |
| T7.7 | Port tracking | Shows active ports |
| T7.8 | PR linking | PR linked to issue |

### Acceptance Criteria

- [ ] GitHub issue import works
- [ ] PR creation works with template
- [ ] Linear integration works (if configured)
- [ ] Jira integration works (if configured)
- [ ] Editor launching works
- [ ] Diff/commit/push/pr flow complete
- [ ] 100% test pass rate for Phase 7 tests

---

## Phase 8: Polish & Release

### Objective
Documentation, packaging, community setup, and v1.0 release.

### Deliverables

| ID | Feature | Description | Priority |
|----|---------|-------------|----------|
| 8.1 | Documentation | Complete user documentation | P0 |
| 8.2 | Installation Script | curl-based installer | P0 |
| 8.3 | Package: Homebrew | Linux Homebrew formula | P0 |
| 8.4 | Package: AUR | Arch Linux AUR package | P1 |
| 8.5 | Package: Deb | Debian/Ubuntu package | P1 |
| 8.6 | Package: Nix | Nix flake | P1 |
| 8.7 | Shell Completions | Bash/Zsh/Fish completions | P0 |
| 8.8 | CI/CD | GitHub Actions pipeline | P0 |
| 8.9 | Release Automation | Goreleaser setup | P0 |
| 8.10 | Community | Discord, contributing guide | P1 |

### Documentation Structure

```
docs/
├── README.md              # Quick start
├── installation.md        # Installation guide
├── configuration.md       # Configuration reference
├── cli-reference.md       # Full CLI documentation
├── agents.md              # Agent configuration
├── templates.md           # Template system
├── workflows.md           # Workflow authoring
├── voice.md               # Voice setup
├── integrations.md        # GitHub/Linear/Jira
├── troubleshooting.md     # Common issues
└── contributing.md        # Contribution guide
```

### Installation Methods

```bash
# Quick install (recommended)
curl -fsSL https://goblinforge.dev/install.sh | bash

# Homebrew (Linux)
brew install goblin-forge/tap/gforge

# AUR (Arch Linux)
yay -S gforge

# Debian/Ubuntu
sudo apt install gforge

# Nix
nix profile install github:your-org/goblin-forge

# From source
go install github.com/your-org/goblin-forge/cmd/gforge@latest
```

### Release Checklist

```markdown
## v1.0.0 Release Checklist

### Code Complete
- [ ] All Phase 1-7 features implemented
- [ ] All tests passing (>90% coverage)
- [ ] No critical bugs open
- [ ] Performance benchmarks acceptable

### Documentation
- [ ] README complete and accurate
- [ ] All CLI commands documented
- [ ] Configuration reference complete
- [ ] Troubleshooting guide written
- [ ] Contributing guide written

### Packaging
- [ ] Installation script tested
- [ ] Homebrew formula working
- [ ] AUR package submitted
- [ ] Deb package built
- [ ] Nix flake working
- [ ] Shell completions included

### Infrastructure
- [ ] CI/CD pipeline green
- [ ] Release automation tested
- [ ] Website deployed
- [ ] Discord server created

### Launch
- [ ] Changelog written
- [ ] Release notes drafted
- [ ] Social media posts prepared
- [ ] HN/Reddit posts drafted
```

### Test Criteria

| Test ID | Test Case | Expected Result |
|---------|-----------|-----------------|
| T8.1 | Install script | Installs correctly |
| T8.2 | Homebrew install | Package installs |
| T8.3 | Shell completions | Completions work |
| T8.4 | Documentation | All links valid |
| T8.5 | CI pipeline | All jobs pass |
| T8.6 | Release build | Artifacts produced |

### Acceptance Criteria

- [ ] All documentation complete
- [ ] Installation works on major platforms
- [ ] Shell completions for bash/zsh/fish
- [ ] CI/CD fully automated
- [ ] Release process documented
- [ ] Community channels created

---

## Success Metrics

### Technical Metrics

| Metric | Target |
|--------|--------|
| Binary size | < 25 MB |
| Startup time (CLI) | < 100ms |
| Startup time (TUI) | < 500ms |
| Voice latency | < 500ms |
| Memory (base) | < 100 MB |
| Memory (per goblin) | < 50 MB |
| Test coverage | > 90% |

### User Metrics (Post-Launch)

| Metric | Target (6 months) |
|--------|-------------------|
| GitHub stars | 1,000+ |
| Weekly active users | 500+ |
| Discord members | 200+ |
| Package downloads | 5,000+ |

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| tmux compatibility | High | Test on multiple tmux versions |
| Agent CLI changes | Medium | Abstract adapter layer |
| Whisper accuracy | Medium | Support multiple models |
| Platform differences | Medium | CI matrix testing |
| Performance issues | High | Continuous benchmarking |

---

## Timeline Summary

| Phase | Duration | Cumulative | Version |
|-------|----------|------------|---------|
| Phase 1: Foundation | 1-2 weeks | 2 weeks | v0.1 |
| Phase 2: Isolation | 1-2 weeks | 4 weeks | v0.2 |
| Phase 3: Agents | 2 weeks | 6 weeks | v0.3 |
| Phase 4: TUI (MVP) | 2 weeks | 8 weeks | v0.4 |
| Phase 5: Templates | 2 weeks | 10 weeks | v0.5 |
| Phase 6: Voice | 2-3 weeks | 13 weeks | v0.6 |
| Phase 7: Integrations | 2 weeks | 15 weeks | v0.7 |
| Phase 8: Polish | 2-3 weeks | 18 weeks | v1.0 |

**Total: ~18 weeks to v1.0**

---

## Appendix: Phase Dependency Graph

```
Phase 1 (Foundation)
    │
    ▼
Phase 2 (Isolation) ──────────────────────┐
    │                                     │
    ▼                                     │
Phase 3 (Agents)                          │
    │                                     │
    ├─────────────────┐                   │
    ▼                 ▼                   │
Phase 4 (TUI)    Phase 5 (Templates)      │
    │                 │                   │
    │                 │                   │
    ▼                 ▼                   │
    └────────┬────────┘                   │
             │                            │
             ▼                            │
      Phase 6 (Voice) ◀───────────────────┘
             │
             ▼
      Phase 7 (Integrations)
             │
             ▼
      Phase 8 (Polish & Release)
```

---

## Next Steps

1. **Initialize repository** with Phase 1 structure
2. **Set up CI/CD** pipeline
3. **Begin Phase 1** implementation
4. **Weekly progress reviews**
5. **Community feedback** integration at MVP (Phase 4)
