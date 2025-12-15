# Goblin Forge

> "Where code is forged by many small minds."

**Goblin Forge** (`gforge`) is a multi-agent command-line orchestrator designed to coordinate and execute multiple coding-focused CLI agents in parallel. It functions as a lightweight process supervisor, workflow router, and capability hub for specialized command-line AI tools.

```
     ╔═══════════════════════════════════════════════════════════════╗
     ║                                                               ║
     ║   ░██████╗░░█████╗░██████╗░██╗░░░░░██╗███╗░░██╗               ║
     ║   ██╔════╝░██╔══██╗██╔══██╗██║░░░░░██║████╗░██║               ║
     ║   ██║░░██╗░██║░░██║██████╦╝██║░░░░░██║██╔██╗██║               ║
     ║   ██║░░╚██╗██║░░██║██╔══██╗██║░░░░░██║██║╚████║               ║
     ║   ╚██████╔╝╚█████╔╝██████╦╝███████╗██║██║░╚███║               ║
     ║   ░╚═════╝░░╚════╝░╚═════╝░╚══════╝╚═╝╚═╝░░╚══╝               ║
     ║                                                               ║
     ║   ███████╗░█████╗░██████╗░░██████╗░███████╗                   ║
     ║   ██╔════╝██╔══██╗██╔══██╗██╔════╝░██╔════╝                   ║
     ║   █████╗░░██║░░██║██████╔╝██║░░██╗░█████╗░░                   ║
     ║   ██╔══╝░░██║░░██║██╔══██╗██║░░╚██╗██╔══╝░░                   ║
     ║   ██║░░░░░╚█████╔╝██║░░██║╚██████╔╝███████╗                   ║
     ║   ╚═╝░░░░░░╚════╝░╚═╝░░╚═╝░╚═════╝░╚══════╝                   ║
     ║                                                               ║
     ║           Multi-Agent CLI Orchestrator for Linux              ║
     ║                                                               ║
     ╚═══════════════════════════════════════════════════════════════╝
```

---

## Quick Reference

```bash
# Spawn agents
gforge spawn coder --agent claude
gforge spawn reviewer --agent aider

# Run tasks
gforge task "refactor auth module" --goblin coder
gforge run build

# Monitor
gforge top                    # htop-like view
gforge logs coder --tail 100

# Voice control
gforge voice start
# "Hey Forge, spawn a Claude agent for testing"
```

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Core Concepts](#core-concepts)
4. [CLI Reference](#cli-reference)
5. [Configuration](#configuration)
6. [Templates](#templates)
7. [Voice Control](#voice-control)
8. [Development](#development)
9. [Testing](#testing)
10. [Project Structure](#project-structure)

---

## Project Overview

### What is Goblin Forge?

Goblin Forge is a **terminal-native multi-agent orchestrator** that:

- **Spawns** multiple AI coding agents (Claude Code, Aider, Codex, Gemini, etc.)
- **Isolates** each agent in its own tmux session + git worktree
- **Routes** tasks to specialized agents based on capability
- **Observes** all agent activity through unified logging
- **Executes** declarative workflows across multiple agents
- **Listens** for voice commands via local Whisper STT

### Core Philosophy

| Principle | Description |
|-----------|-------------|
| **Forge** | A place where many small expert "goblins" craft code |
| **Goblin** | Small, clever, chaotic but highly efficient workers |
| **CLI-first** | Integrates naturally with tmux, terminals, Unix tools |
| **Local-first** | All processing on-device, privacy by default |
| **Provider-agnostic** | Support 15+ CLI agents, pluggable architecture |

### Key Metaphors

```
┌─────────────────────────────────────────────────────────────────────┐
│                        THE FORGE                                    │
│                                                                     │
│   ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐           │
│   │ GOBLIN  │   │ GOBLIN  │   │ GOBLIN  │   │ GOBLIN  │           │
│   │ "coder" │   │"reviewer│   │ "tester"│   │ "docs"  │           │
│   │         │   │         │   │         │   │         │           │
│   │ Claude  │   │ Aider   │   │ Codex   │   │ Gemini  │           │
│   │ Code    │   │         │   │         │   │         │           │
│   └────┬────┘   └────┬────┘   └────┬────┘   └────┬────┘           │
│        │             │             │             │                 │
│        └─────────────┴──────┬──────┴─────────────┘                 │
│                             │                                       │
│                    ┌────────▼────────┐                             │
│                    │   FORGE CORE    │                             │
│                    │   (Coordinator) │                             │
│                    └────────┬────────┘                             │
│                             │                                       │
│              ┌──────────────┼──────────────┐                       │
│              │              │              │                       │
│         ┌────▼────┐   ┌─────▼─────┐  ┌────▼────┐                  │
│         │ Workflow│   │ Capability│  │ Voice   │                  │
│         │ Engine  │   │ Router    │  │ Daemon  │                  │
│         └─────────┘   └───────────┘  └─────────┘                  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Architecture

### System Components

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                         GOBLIN FORGE ARCHITECTURE                            │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                         USER INTERFACES                              │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐    │    │
│  │  │   CLI    │  │   TUI    │  │  Voice   │  │  Config Files    │    │    │
│  │  │ gforge   │  │ gforge   │  │  Daemon  │  │  goblinforge.yaml│    │    │
│  │  │ <cmd>    │  │ top      │  │  Whisper │  │  agents.yaml     │    │    │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────────┬─────────┘    │    │
│  └───────┼─────────────┼─────────────┼─────────────────┼────────────────┘    │
│          │             │             │                 │                     │
│          └─────────────┴──────┬──────┴─────────────────┘                     │
│                               │                                              │
│  ┌────────────────────────────▼────────────────────────────────────────┐    │
│  │                        FORGE CORE (Go)                               │    │
│  │                                                                      │    │
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐        │    │
│  │  │   Coordinator  │  │  Task Router   │  │  Workflow      │        │    │
│  │  │                │  │                │  │  Engine        │        │    │
│  │  │  • Agent pool  │  │  • Capability  │  │  • DAG exec    │        │    │
│  │  │  • Lifecycle   │  │    matching    │  │  • Steps       │        │    │
│  │  │  • Health      │  │  • Load balance│  │  • Recovery    │        │    │
│  │  └────────────────┘  └────────────────┘  └────────────────┘        │    │
│  │                                                                      │    │
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐        │    │
│  │  │   Discovery    │  │  Template      │  │  Project       │        │    │
│  │  │   Engine       │  │  Engine        │  │  Manager       │        │    │
│  │  │                │  │                │  │                │        │    │
│  │  │  • Agent scan  │  │  • 40+ built-in│  │  • Git repos   │        │    │
│  │  │  • Project scan│  │  • Auto-detect │  │  • Worktrees   │        │    │
│  │  │  • Tool detect │  │  • Custom      │  │  • Branches    │        │    │
│  │  └────────────────┘  └────────────────┘  └────────────────┘        │    │
│  │                                                                      │    │
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐        │    │
│  │  │   Storage      │  │  IPC Layer     │  │  Integrations  │        │    │
│  │  │   (SQLite)     │  │  (Unix Socket) │  │                │        │    │
│  │  │                │  │                │  │  • GitHub      │        │    │
│  │  │  • Sessions    │  │  • Go ↔ Python │  │  • Linear      │        │    │
│  │  │  • History     │  │  • Agent comms │  │  • Jira        │        │    │
│  │  │  • Config      │  │  • Events      │  │  • Editors     │        │    │
│  │  └────────────────┘  └────────────────┘  └────────────────┘        │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                               │                                              │
│  ┌────────────────────────────▼────────────────────────────────────────┐    │
│  │                      ISOLATION LAYER                                 │    │
│  │                                                                      │    │
│  │  ┌──────────────────────────────────────────────────────────────┐   │    │
│  │  │                    tmux Server                                │   │    │
│  │  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐         │   │    │
│  │  │  │ Session │  │ Session │  │ Session │  │ Session │   ...   │   │    │
│  │  │  │ goblin-1│  │ goblin-2│  │ goblin-3│  │ goblin-4│         │   │    │
│  │  │  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘         │   │    │
│  │  └───────┼────────────┼────────────┼────────────┼───────────────┘   │    │
│  │          │            │            │            │                   │    │
│  │  ┌───────▼────┐ ┌─────▼──────┐ ┌───▼────────┐ ┌─▼──────────┐      │    │
│  │  │ Worktree   │ │ Worktree   │ │ Worktree   │ │ Worktree   │      │    │
│  │  │ /task-1    │ │ /task-2    │ │ /task-3    │ │ /task-4    │      │    │
│  │  │            │ │            │ │            │ │            │      │    │
│  │  │ ┌────────┐ │ │ ┌────────┐ │ │ ┌────────┐ │ │ ┌────────┐ │      │    │
│  │  │ │ Claude │ │ │ │ Aider  │ │ │ │ Codex  │ │ │ │ Gemini │ │      │    │
│  │  │ │ Code   │ │ │ │        │ │ │ │        │ │ │ │        │ │      │    │
│  │  │ └────────┘ │ │ └────────┘ │ │ └────────┘ │ │ └────────┘ │      │    │
│  │  └────────────┘ └────────────┘ └────────────┘ └────────────┘      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                      VOICE SUBSYSTEM (Python)                        │    │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐    │    │
│  │  │  Whisper   │  │  Hotkey    │  │  Command   │  │    IPC     │    │    │
│  │  │  (faster-  │  │  Listener  │  │  Parser    │  │  (Socket)  │    │    │
│  │  │  whisper)  │  │  (evdev)   │  │            │  │            │    │    │
│  │  └────────────┘  └────────────┘  └────────────┘  └────────────┘    │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Technology Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| **Core** | Go 1.22+ | Fast, single binary, excellent concurrency |
| **CLI** | Cobra + Viper | Industry standard Go CLI framework |
| **TUI** | Bubble Tea + Lip Gloss | Modern, composable TUI framework |
| **Voice** | Python + faster-whisper | Best local STT ecosystem |
| **IPC** | Unix Domain Socket + gRPC | Fast, typed Go↔Python communication |
| **Database** | SQLite (modernc.org/sqlite) | Pure Go, no CGO required |
| **Config** | YAML | Human-readable, standard |
| **Sessions** | tmux | Battle-tested terminal multiplexer |
| **Isolation** | git worktrees | Native git, no overhead |

### Data Flow

```
User Input (CLI/Voice/TUI)
         │
         ▼
┌─────────────────┐
│  Command Parser │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│   Coordinator   │────▶│  Agent Registry │
└────────┬────────┘     └─────────────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│  Task Router    │────▶│ Capability Graph│
└────────┬────────┘     └─────────────────┘
         │
         ▼
┌─────────────────┐
│ Workflow Engine │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│ tmux + Worktree │────▶│  Agent Process  │
└────────┬────────┘     └─────────────────┘
         │
         ▼
┌─────────────────┐
│  Output/Logs    │
└─────────────────┘
```

---

## Core Concepts

### Goblins (Agents)

A **Goblin** is an instance of a CLI coding agent running in isolation:

```yaml
# Each goblin has:
goblin:
  id: "goblin-abc123"           # Unique identifier
  name: "coder"                  # User-friendly name
  agent: "claude"                # Underlying agent (claude, aider, etc.)
  status: "running"              # created|running|paused|complete
  tmux_session: "gforge-abc123"  # tmux session name
  worktree: "/path/to/worktree"  # Isolated git worktree
  branch: "feat/auth-fix"        # Git branch
  capabilities: ["code", "git"]  # What this goblin can do
  memory_shard: "shard-1"        # Optional persistent memory
```

### Supported Agents

| Agent | Command | Auto-Detected | Capabilities |
|-------|---------|---------------|--------------|
| Claude Code | `claude` | ✅ | code, git, fs, web |
| Aider | `aider` | ✅ | code, git |
| Codex CLI | `codex` | ✅ | code |
| Gemini CLI | `gemini` | ✅ | code, web |
| GitHub Copilot | `gh copilot` | ✅ | code |
| Cursor CLI | `cursor` | ✅ | code, git |
| Qwen Code | `qwen-code` | ✅ | code |
| OpenHands | `openhands` | ✅ | code, git, web |
| Cline | `cline` | ✅ | code |
| Goose | `goose` | ✅ | code |
| Amp | `amp` | ✅ | code |
| Continue | `continue` | ✅ | code |
| Ollama (local) | `ollama` | ✅ | code (configurable) |
| LM Studio | `lms` | ✅ | code (configurable) |
| **Custom** | User-defined | Plugin | Configurable |

### Workflows

A **Workflow** is a DAG of tasks executed across multiple goblins:

```yaml
workflows:
  full-review:
    name: "Full Code Review"
    steps:
      - id: analyze
        goblin: coder
        task: "Analyze codebase structure and identify issues"

      - id: refactor
        goblin: coder
        task: "Refactor identified issues"
        depends_on: [analyze]

      - id: test
        goblin: tester
        task: "Write and run tests for refactored code"
        depends_on: [refactor]

      - id: review
        goblin: reviewer
        task: "Review all changes and provide feedback"
        depends_on: [test]
        parallel: true  # Can run alongside other independent steps
```

### Templates

**Templates** auto-configure environments based on project type:

```bash
$ gforge spawn coder --project ./my-rust-app

Detected: Rust project (Cargo.toml)
Template: rust
Setup:
  ✓ rustup default stable
  ✓ cargo fetch

Commands available:
  gforge run build    → cargo build
  gforge run test     → cargo test
  gforge run check    → cargo clippy
```

### Projects

**Projects** are tracked git repositories:

```bash
$ gforge projects list
┌─────┬───────────────────┬──────────────┬─────────┬──────────┐
│ ID  │ Name              │ Path         │ Type    │ Goblins  │
├─────┼───────────────────┼──────────────┼─────────┼──────────┤
│ 1   │ my-saas-app       │ ~/code/saas  │ nextjs  │ 3 active │
│ 2   │ cli-tools         │ ~/code/cli   │ rust    │ 1 paused │
│ 3   │ ml-pipeline       │ ~/code/ml    │ python  │ 0        │
└─────┴───────────────────┴──────────────┴─────────┴──────────┘
```

---

## CLI Reference

### Binary Name

```
gforge
```

Alternatives: `forge`, `gf` (alias recommended)

### Command Overview

```bash
gforge <command> [subcommand] [flags]

GOBLIN MANAGEMENT
  spawn       Create and start a new goblin (agent instance)
  list, ls    List all goblins
  attach, a   Attach to goblin's tmux session
  detach      Detach from current session
  stop        Stop a running goblin
  kill        Force kill a goblin
  pause       Pause goblin execution
  resume      Resume paused goblin
  rename      Rename a goblin

TASK EXECUTION
  task        Send a task to a specific goblin
  run         Run a template command (build, test, dev)
  workflow    Execute a multi-step workflow

OBSERVABILITY
  top         htop-like multi-goblin dashboard
  logs        View goblin logs
  status      Show system status
  diff        Show changes made by goblin
  review      Interactive diff review

GIT OPERATIONS
  commit      Commit goblin changes
  push        Push to remote
  pr          Create pull request
  merge       Merge worktree to main branch

VOICE CONTROL
  voice       Voice subsystem commands
    start     Start voice daemon
    stop      Stop voice daemon
    status    Voice system status
    test      Test microphone

DISCOVERY
  agents      Manage agent definitions
    scan      Auto-discover installed agents
    list      List available agents
    add       Add custom agent
  projects    Manage projects
    scan      Scan for git repositories
    list      List tracked projects
    add       Add project manually
  templates   Manage templates
    list      List available templates
    show      Show template details

CONFIGURATION
  config      View/edit configuration
  init        Initialize gforge in current directory

SYSTEM
  version     Show version
  upgrade     Check for updates
  clean       Clean up old sessions/worktrees
```

### Detailed Command Reference

#### `gforge spawn`

Create and start a new goblin:

```bash
gforge spawn <name> [flags]

FLAGS:
  -a, --agent <agent>       Agent to use (claude, aider, etc.)
  -p, --project <path>      Project directory
  -b, --branch <name>       Git branch name
  -t, --template <name>     Force specific template
  -m, --memory <shard>      Attach memory shard
  --from-issue <ref>        Import from issue (gh:owner/repo#123)
  --auto-accept             Enable auto-accept mode
  --capabilities <list>     Override capabilities

EXAMPLES:
  gforge spawn coder --agent claude
  gforge spawn reviewer --agent aider --project ./api
  gforge spawn tester --agent codex --from-issue gh:myorg/repo#42
  gforge spawn "Auth Expert" --agent claude --branch feat/auth
```

#### `gforge task`

Send a task to a goblin:

```bash
gforge task "<task description>" [flags]

FLAGS:
  -g, --goblin <name>       Target goblin (required)
  --wait                    Wait for completion
  --timeout <duration>      Task timeout

EXAMPLES:
  gforge task "refactor the auth module" --goblin coder
  gforge task "write unit tests for UserService" --goblin tester --wait
  gforge task "review PR #123" --goblin reviewer
```

#### `gforge run`

Run template commands:

```bash
gforge run <command> [goblin] [flags]

COMMANDS:
  build       Run build command
  test        Run tests
  dev         Start dev server
  lint        Run linter
  fmt         Format code
  check       Run checks (clippy, mypy, etc.)

EXAMPLES:
  gforge run build coder
  gforge run test --all           # Run on all goblins
  gforge run dev frontend         # Start dev server
```

#### `gforge top`

htop-like dashboard:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  GOBLIN FORGE v1.0.0                              🎤 Voice: ON    q: quit  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  GOBLINS (4)                           CPU    MEM    STATUS                 │
│  ─────────────────────────────────────────────────────────────────────────  │
│  ▶ 1. coder        [Claude]   2h 15m   12%    245M   ████████░░ WORKING    │
│    2. reviewer     [Aider]    45m       0%    120M   ░░░░░░░░░░ IDLE       │
│    3. tester       [Codex]    30m       8%    180M   ██████░░░░ TESTING    │
│    4. docs         [Gemini]   10m       0%     95M   ░░░░░░░░░░ PAUSED     │
│                                                                             │
│  ACTIVE TASK: coder                                                         │
│  ─────────────────────────────────────────────────────────────────────────  │
│  │ Analyzing auth middleware for security vulnerabilities...                │
│  │ Found 3 potential issues in src/auth/jwt.ts                             │
│  │ Fixing issue 1/3: Token expiration not validated                        │
│  │ ████████████████████░░░░░░░░░░ 65%                                      │
│                                                                             │
│  RECENT VOICE COMMANDS                                                      │
│  ─────────────────────────────────────────────────────────────────────────  │
│  "spawn a new goblin for testing"                                          │
│  "show diff for coder"                                                     │
│                                                                             │
│  KEYBINDS: n:new  a:attach  d:diff  k:kill  p:pause  v:voice  ?:help      │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### `gforge workflow`

Execute multi-step workflows:

```bash
gforge workflow <name> [flags]

FLAGS:
  -p, --project <path>      Project directory
  --dry-run                 Show steps without executing
  --resume                  Resume interrupted workflow
  --from-step <id>          Start from specific step

EXAMPLES:
  gforge workflow full-review
  gforge workflow build --project ./api
  gforge workflow release --dry-run
```

---

## Configuration

### Main Configuration

Location: `~/.config/gforge/config.yaml`

```yaml
# Goblin Forge Configuration

general:
  default_agent: claude
  worktree_base: ~/.local/share/gforge/worktrees
  auto_cleanup_days: 7
  max_concurrent_goblins: 10

# tmux settings
tmux:
  socket_name: gforge
  default_shell: $SHELL
  history_limit: 50000

# Voice subsystem
voice:
  enabled: true
  model: small                    # tiny|base|small|medium|large-v3
  hotkey: super+shift+g           # Global hotkey
  language: auto                  # Auto-detect or specific (en, es, etc.)
  wake_word: "hey forge"          # Optional wake word
  feedback_sound: true

  # Voice command patterns
  commands:
    spawn: ["spawn", "create", "new goblin", "start"]
    stop: ["stop", "kill", "terminate"]
    attach: ["attach", "connect", "enter"]
    diff: ["show diff", "what changed", "changes"]
    commit: ["commit", "save changes"]

# TUI settings
tui:
  theme: dark                     # dark|light|kymera
  refresh_rate_ms: 500
  show_timestamps: true
  max_output_lines: 1000

# Git defaults
git:
  branch_prefix: "gforge/"
  branch_style: kebab-case        # kebab-case|snake_case|camelCase
  auto_fetch: true
  auto_stash: true

  commit_template: |
    {type}: {description}

    Goblin: {goblin_name}
    Agent: {agent}

  pr_template: |
    ## Summary
    {auto_summary}

    ## Changes
    {file_list}

    ## Testing
    - [ ] Tests pass
    - [ ] Manual testing done

    Resolves: {linked_issue}

# Issue tracker integrations
integrations:
  github:
    enabled: true
    # Uses gh CLI auth

  linear:
    enabled: false
    api_key: ${LINEAR_API_KEY}

  jira:
    enabled: false
    url: https://company.atlassian.net
    email: ${JIRA_EMAIL}
    token: ${JIRA_TOKEN}

# Editor integration
editors:
  default: ${EDITOR:-nvim}
  auto_detect: true              # Detect from .vscode, .idea, etc.

  shortcuts:
    e: "nvim"
    c: "cursor"
    v: "code"
    z: "zed"

# Project discovery
projects:
  auto_scan: true
  scan_paths:
    - ~/code
    - ~/work
    - ~/projects
  ignore:
    - "**/node_modules"
    - "**/vendor"
    - "**/.git"

# Environment auto-detection
environments:
  auto_detect: true
  dotfiles:
    - .nvmrc
    - .node-version
    - .python-version
    - .ruby-version
    - .tool-versions
    - .envrc
```

### Agent Definitions

Location: `~/.config/gforge/agents.yaml`

```yaml
# Agent Definitions

agents:
  # Claude Code (primary)
  claude:
    command: claude
    args: []
    description: "Anthropic Claude Code CLI"
    auto_accept: false
    capabilities: [code, git, fs, web, mcp]
    detect:
      binary: claude
      version_cmd: "claude --version"
      config_paths: ["~/.claude", "~/.config/claude"]

  # Claude with auto-accept
  claude-auto:
    command: claude
    args: ["--dangerously-skip-permissions"]
    description: "Claude Code (auto-accept mode)"
    auto_accept: true
    capabilities: [code, git, fs, web, mcp]

  # Aider
  aider:
    command: aider
    args: ["--no-auto-commits", "--dark-mode"]
    description: "Aider AI pair programming"
    capabilities: [code, git]
    env:
      AIDER_MODEL: "claude-3-5-sonnet-20241022"
    detect:
      binary: aider
      version_cmd: "aider --version"
      config_paths: ["~/.aider.conf.yml"]

  # OpenAI Codex
  codex:
    command: codex
    args: []
    description: "OpenAI Codex CLI"
    capabilities: [code]
    detect:
      binary: codex
      version_cmd: "codex --version"

  # Google Gemini
  gemini:
    command: gemini
    args: []
    description: "Google Gemini CLI"
    capabilities: [code, web]
    detect:
      binary: gemini
      version_cmd: "gemini --version"

  # GitHub Copilot
  gh-copilot:
    command: gh
    args: ["copilot"]
    description: "GitHub Copilot via gh CLI"
    capabilities: [code]
    detect:
      binary: gh
      check_cmd: "gh extension list | grep -q copilot"

  # Local models via Ollama
  ollama:
    command: ollama
    args: ["run", "codellama:34b"]
    description: "Local CodeLlama via Ollama"
    capabilities: [code]
    env:
      OLLAMA_HOST: "127.0.0.1:11434"
    detect:
      binary: ollama
      version_cmd: "ollama --version"

  # Custom template for user agents
  # custom-example:
  #   command: my-agent
  #   args: ["--mode", "code"]
  #   description: "My custom coding agent"
  #   capabilities: [code]
  #   env:
  #     MY_API_KEY: ${MY_API_KEY}
```

### Workflow Definitions

Location: `~/.config/gforge/workflows.yaml`

```yaml
# Workflow Definitions

workflows:
  # Full code review workflow
  full-review:
    name: "Full Code Review"
    description: "Analyze, refactor, test, and review code"
    steps:
      - id: analyze
        goblin: coder
        agent: claude
        task: "Analyze the codebase and identify areas for improvement"
        timeout: 10m

      - id: refactor
        goblin: coder
        task: "Refactor the identified issues"
        depends_on: [analyze]
        timeout: 30m

      - id: test
        goblin: tester
        agent: codex
        task: "Write comprehensive tests for the changes"
        depends_on: [refactor]
        timeout: 20m

      - id: review
        goblin: reviewer
        agent: aider
        task: "Review all changes and provide feedback"
        depends_on: [test]
        timeout: 15m

  # Quick fix workflow
  quick-fix:
    name: "Quick Bug Fix"
    description: "Fast bug fix with minimal review"
    steps:
      - id: fix
        goblin: coder
        task: "Fix the reported bug"
        timeout: 15m

      - id: test
        goblin: coder
        task: "Ensure existing tests pass"
        depends_on: [fix]
        run: test
        timeout: 10m

  # Security audit workflow
  security-audit:
    name: "Security Audit"
    description: "Comprehensive security review"
    steps:
      - id: scan
        goblin: security
        agent: claude
        task: "Scan codebase for security vulnerabilities (OWASP Top 10)"
        timeout: 20m

      - id: fix
        goblin: security
        task: "Fix identified vulnerabilities"
        depends_on: [scan]
        timeout: 30m

      - id: verify
        goblin: security
        task: "Verify fixes and generate security report"
        depends_on: [fix]
        timeout: 15m

  # Release workflow
  release:
    name: "Prepare Release"
    description: "Full release preparation"
    steps:
      - id: changelog
        goblin: docs
        agent: claude
        task: "Generate changelog from commits since last release"
        timeout: 10m

      - id: version
        goblin: coder
        task: "Bump version numbers appropriately"
        depends_on: [changelog]
        timeout: 5m

      - id: test
        goblin: tester
        task: "Run full test suite"
        depends_on: [version]
        run: test
        timeout: 30m

      - id: build
        goblin: coder
        task: "Build release artifacts"
        depends_on: [test]
        run: build-release
        timeout: 15m
```

---

## Templates

### Built-in Templates (40+)

```bash
$ gforge templates list

ENVIRONMENT SETUP (15)
  nodejs          Node.js with auto-detected package manager
  nodejs-pnpm     Node.js with pnpm enforced
  nodejs-bun      Node.js with Bun runtime
  python          Python with auto-detected tooling
  python-uv       Python with uv (10-100x faster)
  python-poetry   Python with Poetry
  rust            Rust with cargo
  golang          Go modules
  ruby            Ruby with bundler
  java-maven      Java with Maven
  java-gradle     Java with Gradle
  dotnet          .NET projects
  elixir          Elixir with Mix
  c-cpp           C/C++ with CMake/Make
  zig             Zig projects

FRAMEWORKS (12)
  nextjs          Next.js dev server
  vite            Vite dev server
  remix           Remix dev server
  astro           Astro dev server
  fastapi         FastAPI with uvicorn
  django          Django runserver
  flask           Flask dev server
  rails           Ruby on Rails
  phoenix         Elixir Phoenix
  gin             Go Gin framework
  actix           Rust Actix-web
  spring          Spring Boot

BUILD & TEST (8)
  npm-build       npm install && npm run build
  npm-test        npm test
  cargo-build     cargo build
  cargo-test      cargo test
  go-build        go build ./...
  go-test         go test ./...
  pytest          pytest with coverage
  jest            Jest test runner

WORKFLOWS (5)
  pr-review       Review pull request
  conflict-resolve Resolve merge conflicts
  release         Prepare release
  security-audit  Security scan
  refactor        Code refactoring
```

### Template Structure

```yaml
# ~/.config/gforge/templates/custom-template.yaml

name: custom-template
description: "My custom project template"
version: "1.0.0"

# Auto-detection rules
detect:
  files: ["custom.config.js", "custom.yaml"]
  content:
    - pattern: "import.*from.*'custom-lib'"
      files: ["*.ts", "*.js"]

# Variables with defaults
variables:
  runtime_version: "auto"
  package_manager: "auto"

# Setup steps run when goblin spawns
setup:
  - name: "Check prerequisites"
    run: "command -v custom-cli"

  - name: "Install dependencies"
    run: "${PKG_MGR} install"
    optional: true
    prompt: "Install dependencies?"

# Available commands
commands:
  build: "${PKG_MGR} run build"
  test: "${PKG_MGR} test"
  dev: "${PKG_MGR} run dev"
  lint: "${PKG_MGR} run lint"
  fmt: "${PKG_MGR} run format"

# Ports to track
ports:
  - 3000
  - 8080

# Context passed to agent
agent_context: |
  This is a custom project.
  Runtime: ${runtime_version}
  Package manager: ${package_manager}

  Available scripts:
  ${npm_scripts}
```

---

## Voice Control

### Setup

```bash
# Install voice dependencies
gforge voice setup

# Test microphone
gforge voice test

# Start daemon
gforge voice start

# Check status
gforge voice status
Voice daemon: RUNNING (PID 12345)
Model: whisper-small (244MB)
Hotkey: Super+Shift+G
Wake word: "hey forge"
Last command: "spawn coder" (2m ago)
```

### Voice Commands

| Command | Voice Phrase | Action |
|---------|--------------|--------|
| Spawn | "spawn/create/new [agent] for [task]" | `gforge spawn` |
| List | "list/show goblins" | `gforge list` |
| Attach | "attach/connect to [name]" | `gforge attach` |
| Stop | "stop/kill [name]" | `gforge stop` |
| Diff | "show diff/changes for [name]" | `gforge diff` |
| Commit | "commit [name] with message [msg]" | `gforge commit` |
| Task | "task [name] to [description]" | `gforge task` |
| Run | "run build/test/dev" | `gforge run` |
| Status | "status/what's running" | `gforge status` |

### Voice Examples

```
"Hey Forge, spawn a Claude goblin for the authentication bug"
→ gforge spawn auth-bug --agent claude

"Show me what coder changed"
→ gforge diff coder

"Commit coder's changes with message 'fixed JWT validation'"
→ gforge commit coder -m "fixed JWT validation"

"Tell reviewer to check the API endpoints"
→ gforge task "check the API endpoints" --goblin reviewer

"Run tests on all goblins"
→ gforge run test --all
```

---

## Development

### Prerequisites

```bash
# Go 1.22+
go version

# Python 3.10+ (for voice)
python3 --version

# tmux
tmux -V

# git
git --version

# Optional: gh CLI (for GitHub integration)
gh --version
```

### Building

```bash
# Clone repository
git clone https://github.com/your-org/goblin-forge
cd goblin-forge

# Build
make build

# Or with Go directly
go build -o gforge ./cmd/gforge

# Install locally
make install  # Installs to ~/.local/bin/gforge

# Build with voice support
make build-full  # Includes Python voice daemon
```

### Development Mode

```bash
# Run in development mode
make dev

# Run with hot reload
make watch

# Run specific component
go run ./cmd/gforge <command>
```

---

## Testing

### Running Tests

```bash
# All tests
make test

# Unit tests only
make test-unit

# Integration tests
make test-integration

# With coverage
make test-coverage

# Specific package
go test ./internal/orchestrator/...
```

### Test Categories

| Category | Command | Description |
|----------|---------|-------------|
| Unit | `make test-unit` | Core logic tests |
| Integration | `make test-integration` | Component integration |
| E2E | `make test-e2e` | Full workflow tests |
| Voice | `make test-voice` | Voice subsystem tests |
| TUI | `make test-tui` | TUI component tests |

---

## Project Structure

```
goblin-forge/
├── cmd/
│   └── gforge/
│       └── main.go                  # CLI entrypoint
├── internal/
│   ├── coordinator/
│   │   ├── coordinator.go           # Core orchestration
│   │   ├── goblin.go                # Goblin lifecycle
│   │   ├── pool.go                  # Goblin pool management
│   │   └── router.go                # Task routing
│   ├── agents/
│   │   ├── registry.go              # Agent plugin registry
│   │   ├── discovery.go             # Auto-discovery
│   │   ├── claude.go                # Claude adapter
│   │   ├── aider.go                 # Aider adapter
│   │   └── generic.go               # Generic CLI adapter
│   ├── tmux/
│   │   ├── manager.go               # tmux session management
│   │   ├── capture.go               # Output capture
│   │   └── layout.go                # Terminal layouts
│   ├── workspace/
│   │   ├── worktree.go              # Git worktree management
│   │   ├── project.go               # Project tracking
│   │   └── branch.go                # Branch operations
│   ├── workflow/
│   │   ├── engine.go                # Workflow execution
│   │   ├── dag.go                   # DAG processing
│   │   └── step.go                  # Step execution
│   ├── template/
│   │   ├── engine.go                # Template processing
│   │   ├── detect.go                # Auto-detection
│   │   ├── builtin/                 # Built-in templates
│   │   │   ├── nodejs.yaml
│   │   │   ├── python.yaml
│   │   │   ├── rust.yaml
│   │   │   └── ...
│   │   └── loader.go                # Template loading
│   ├── tui/
│   │   ├── app.go                   # Bubble Tea app
│   │   ├── views/
│   │   │   ├── dashboard.go         # Main dashboard
│   │   │   ├── goblins.go           # Goblin list
│   │   │   ├── output.go            # Agent output
│   │   │   └── diff.go              # Diff viewer
│   │   └── components/
│   │       ├── table.go
│   │       ├── progress.go
│   │       └── ...
│   ├── integrations/
│   │   ├── github.go                # GitHub Issues/PRs
│   │   ├── linear.go                # Linear tickets
│   │   └── jira.go                  # Jira integration
│   ├── storage/
│   │   ├── sqlite.go                # SQLite database
│   │   ├── models.go                # Data models
│   │   └── migrations/              # DB migrations
│   ├── config/
│   │   ├── config.go                # Configuration
│   │   ├── defaults.go              # Default values
│   │   └── validation.go            # Config validation
│   └── ipc/
│       ├── server.go                # IPC server
│       ├── client.go                # IPC client
│       └── protocol.go              # Protocol definitions
├── voice/                           # Python voice subsystem
│   ├── __init__.py
│   ├── daemon.py                    # Voice daemon
│   ├── transcriber.py               # Whisper integration
│   ├── hotkey.py                    # Hotkey listener
│   ├── commands.py                  # Command parser
│   ├── ipc.py                       # Go communication
│   └── requirements.txt
├── scripts/
│   ├── install.sh                   # Installation script
│   ├── setup-voice.sh               # Voice setup
│   └── completions/                 # Shell completions
│       ├── gforge.bash
│       ├── gforge.zsh
│       └── gforge.fish
├── configs/
│   ├── default-config.yaml          # Default config
│   ├── default-agents.yaml          # Default agents
│   └── default-workflows.yaml       # Default workflows
├── docs/
│   ├── README.md
│   ├── VOICE.md
│   ├── TEMPLATES.md
│   ├── WORKFLOWS.md
│   └── AGENTS.md
├── test/
│   ├── unit/
│   ├── integration/
│   ├── e2e/
│   └── fixtures/
├── go.mod
├── go.sum
├── Makefile
├── CLAUDE.md                        # This file
├── CHANGELOG.md
├── LICENSE                          # Apache-2.0
└── README.md
```

---

## Security Model

```
┌─────────────────────────────────────────────────────────────────────┐
│                      SECURITY BOUNDARIES                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  VOICE DATA                                                         │
│  ─────────────────────────────────────────────────────────────────  │
│  • Audio: RAM only → Whisper → immediately discarded               │
│  • Never written to disk                                           │
│  • Never transmitted over network                                  │
│  • Local Whisper models only                                       │
│                                                                     │
│  GOBLIN ISOLATION                                                   │
│  ─────────────────────────────────────────────────────────────────  │
│  • Each goblin in separate tmux session                            │
│  • Each goblin in separate git worktree                            │
│  • No shared mutable state between goblins                         │
│  • File access scoped to worktree directory                        │
│                                                                     │
│  CREDENTIALS                                                        │
│  ─────────────────────────────────────────────────────────────────  │
│  • No credential storage in gforge                                 │
│  • Delegates to: gh CLI, git credential helpers                    │
│  • API keys via environment variables only                         │
│  • Unix sockets in XDG_RUNTIME_DIR                                 │
│                                                                     │
│  NETWORK                                                            │
│  ─────────────────────────────────────────────────────────────────  │
│  • Voice: Zero network (local Whisper)                             │
│  • Agents: Follow their own network policies                       │
│  • Integrations: HTTPS only, user-initiated                        │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Quick Start

```bash
# 1. Install gforge
curl -fsSL https://goblinforge.dev/install.sh | bash

# 2. Scan for installed agents
gforge agents scan

# 3. Scan for projects
gforge projects scan

# 4. Spawn your first goblin
gforge spawn coder --agent claude --project ./my-app

# 5. Attach and watch it work
gforge attach coder

# 6. Or use the dashboard
gforge top

# 7. Enable voice (optional)
gforge voice setup
gforge voice start
# "Hey Forge, spawn a reviewer for code review"
```

---

## License

Apache-2.0

---

## Links

- GitHub: https://github.com/your-org/goblin-forge
- Documentation: https://goblinforge.dev/docs
- Discord: https://discord.gg/goblinforge
