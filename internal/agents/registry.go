package agents

import (
	"os/exec"
	"strings"
)

// Registry manages agent definitions
type Registry struct {
	agents map[string]*Agent
}

// Agent represents a CLI agent definition
type Agent struct {
	Name         string
	Command      string
	Args         []string
	Description  string
	Capabilities []string
	Detection    Detection
	InstallHint  string
	Env          map[string]string
	AutoAccept   bool
}

// Detection defines how to detect if an agent is installed
type Detection struct {
	Binary      string
	VersionCmd  string
	VersionArgs []string
	ConfigPaths []string
}

// DetectedAgent represents a discovered agent installation
type DetectedAgent struct {
	Name    string
	Path    string
	Version string
}

// NewRegistry creates a new agent registry with built-in agents
func NewRegistry() *Registry {
	r := &Registry{
		agents: make(map[string]*Agent),
	}

	// Register built-in agents
	r.registerBuiltinAgents()

	return r
}

// registerBuiltinAgents adds the core supported agents
func (r *Registry) registerBuiltinAgents() {
	// Claude Code - Primary agent
	r.agents["claude"] = &Agent{
		Name:        "claude",
		Command:     "claude",
		Args:        []string{},
		Description: "Anthropic Claude Code CLI - AI coding assistant",
		Capabilities: []string{
			"code",     // Code generation and editing
			"git",      // Git operations
			"fs",       // Filesystem operations
			"web",      // Web browsing/fetching
			"mcp",      // Model Context Protocol
			"terminal", // Terminal commands
		},
		Detection: Detection{
			Binary:      "claude",
			VersionCmd:  "claude",
			VersionArgs: []string{"--version"},
		},
		InstallHint: "Visit https://claude.ai/code or install via: npm install -g @anthropic/claude-code",
		AutoAccept:  false,
	}

	// Claude with auto-accept (dangerous mode)
	r.agents["claude-auto"] = &Agent{
		Name:        "claude-auto",
		Command:     "claude",
		Args:        []string{"--dangerously-skip-permissions"},
		Description: "Claude Code with auto-accept mode (use with caution)",
		Capabilities: []string{
			"code", "git", "fs", "web", "mcp", "terminal",
		},
		Detection: Detection{
			Binary:      "claude",
			VersionCmd:  "claude",
			VersionArgs: []string{"--version"},
		},
		InstallHint: "Same as claude - uses dangerous auto-accept flag",
		AutoAccept:  true,
	}

	// OpenAI Codex CLI
	r.agents["codex"] = &Agent{
		Name:        "codex",
		Command:     "codex",
		Args:        []string{},
		Description: "OpenAI Codex CLI - Code generation agent",
		Capabilities: []string{
			"code",
			"terminal",
		},
		Detection: Detection{
			Binary:      "codex",
			VersionCmd:  "codex",
			VersionArgs: []string{"--version"},
		},
		InstallHint: "Install via: npm install -g @openai/codex",
		AutoAccept:  false,
	}

	// Google Gemini CLI
	r.agents["gemini"] = &Agent{
		Name:        "gemini",
		Command:     "gemini",
		Args:        []string{},
		Description: "Google Gemini CLI - Multimodal AI assistant",
		Capabilities: []string{
			"code",
			"web",
			"multimodal",
		},
		Detection: Detection{
			Binary:      "gemini",
			VersionCmd:  "gemini",
			VersionArgs: []string{"--version"},
		},
		InstallHint: "Install via: pip install google-generativeai or npm install -g @google/gemini-cli",
		AutoAccept:  false,
	}

	// Ollama - Local LLM runner
	r.agents["ollama"] = &Agent{
		Name:        "ollama",
		Command:     "ollama",
		Args:        []string{"run", "codellama"},
		Description: "Ollama - Run local LLMs (CodeLlama, DeepSeek, etc.)",
		Capabilities: []string{
			"code",
			"local", // Runs locally, no API needed
		},
		Detection: Detection{
			Binary:      "ollama",
			VersionCmd:  "ollama",
			VersionArgs: []string{"--version"},
		},
		InstallHint: "Install from https://ollama.ai or: curl -fsSL https://ollama.ai/install.sh | sh",
		AutoAccept:  false,
		Env: map[string]string{
			"OLLAMA_HOST": "127.0.0.1:11434",
		},
	}

	// Ollama with DeepSeek Coder
	r.agents["ollama-deepseek"] = &Agent{
		Name:        "ollama-deepseek",
		Command:     "ollama",
		Args:        []string{"run", "deepseek-coder:6.7b"},
		Description: "Ollama with DeepSeek Coder model",
		Capabilities: []string{
			"code",
			"local",
		},
		Detection: Detection{
			Binary:      "ollama",
			VersionCmd:  "ollama",
			VersionArgs: []string{"--version"},
		},
		InstallHint: "Install ollama, then: ollama pull deepseek-coder:6.7b",
		AutoAccept:  false,
	}

	// Ollama with Qwen Coder
	r.agents["ollama-qwen"] = &Agent{
		Name:        "ollama-qwen",
		Command:     "ollama",
		Args:        []string{"run", "qwen2.5-coder:7b"},
		Description: "Ollama with Qwen 2.5 Coder model",
		Capabilities: []string{
			"code",
			"local",
		},
		Detection: Detection{
			Binary:      "ollama",
			VersionCmd:  "ollama",
			VersionArgs: []string{"--version"},
		},
		InstallHint: "Install ollama, then: ollama pull qwen2.5-coder:7b",
		AutoAccept:  false,
	}

	// Charmbracelet Crush - TUI AI coding assistant
	r.agents["crush"] = &Agent{
		Name:        "crush",
		Command:     "crush",
		Args:        []string{},
		Description: "Charmbracelet Crush - TUI AI coding assistant with LSP support",
		Capabilities: []string{
			"code",     // Code generation and editing
			"git",      // Git operations
			"fs",       // Filesystem operations
			"web",      // Web fetching
			"mcp",      // Model Context Protocol
			"terminal", // Terminal commands
			"lsp",      // Language Server Protocol integration
		},
		Detection: Detection{
			Binary:      "crush",
			VersionCmd:  "crush",
			VersionArgs: []string{"--version"},
		},
		InstallHint: "Install via: brew install charmbracelet/tap/crush",
		AutoAccept:  false,
	}

	// Crush with --yolo mode (auto-accept all tool calls)
	r.agents["crush-yolo"] = &Agent{
		Name:        "crush-yolo",
		Command:     "crush",
		Args:        []string{"--yolo"},
		Description: "Crush with auto-accept mode (use with caution)",
		Capabilities: []string{
			"code", "git", "fs", "web", "mcp", "terminal", "lsp",
		},
		Detection: Detection{
			Binary:      "crush",
			VersionCmd:  "crush",
			VersionArgs: []string{"--version"},
		},
		InstallHint: "Same as crush - uses --yolo flag for auto-accept",
		AutoAccept:  true,
	}
}

// Get retrieves an agent by name
func (r *Registry) Get(name string) *Agent {
	return r.agents[name]
}

// List returns all registered agents
func (r *Registry) List() []*Agent {
	agents := make([]*Agent, 0, len(r.agents))
	for _, a := range r.agents {
		agents = append(agents, a)
	}
	return agents
}

// Scan discovers which agents are installed on the system
func (r *Registry) Scan() []DetectedAgent {
	var detected []DetectedAgent
	seen := make(map[string]bool) // Track by binary to avoid duplicates

	for _, agent := range r.agents {
		// Skip if we've already checked this binary
		if seen[agent.Detection.Binary] {
			continue
		}
		seen[agent.Detection.Binary] = true

		// Check if binary exists in PATH
		path, err := exec.LookPath(agent.Detection.Binary)
		if err != nil {
			continue // Not installed
		}

		// Get version
		version := r.getVersion(agent)

		detected = append(detected, DetectedAgent{
			Name:    agent.Name,
			Path:    path,
			Version: version,
		})
	}

	return detected
}

// getVersion runs the version command and extracts version string
func (r *Registry) getVersion(agent *Agent) string {
	if agent.Detection.VersionCmd == "" {
		return "unknown"
	}

	args := agent.Detection.VersionArgs
	cmd := exec.Command(agent.Detection.VersionCmd, args...)
	output, err := cmd.CombinedOutput()
	if err != nil {
		return "unknown"
	}

	// Extract first line and clean it up
	lines := strings.Split(string(output), "\n")
	if len(lines) > 0 {
		version := strings.TrimSpace(lines[0])
		// Try to extract just the version number
		parts := strings.Fields(version)
		for _, p := range parts {
			if strings.ContainsAny(p, "0123456789.") && !strings.HasPrefix(p, "-") {
				return p
			}
		}
		return version
	}

	return "unknown"
}

// NotInstalled returns agent names that are not installed
func (r *Registry) NotInstalled(detected []DetectedAgent) []string {
	installed := make(map[string]bool)
	for _, d := range detected {
		installed[d.Name] = true
		// Also mark variants as installed if base is installed
		if d.Name == "claude" {
			installed["claude-auto"] = true
		}
		if d.Name == "crush" {
			installed["crush-yolo"] = true
		}
		if d.Name == "ollama" {
			installed["ollama-deepseek"] = true
			installed["ollama-qwen"] = true
		}
	}

	var notInstalled []string
	seen := make(map[string]bool)

	for name, agent := range r.agents {
		// Skip variants
		if strings.Contains(name, "-") && !strings.HasPrefix(name, "ollama-") {
			continue
		}
		if seen[agent.Detection.Binary] {
			continue
		}
		seen[agent.Detection.Binary] = true

		if !installed[name] {
			notInstalled = append(notInstalled, name)
		}
	}

	return notInstalled
}

// Register adds a custom agent to the registry
func (r *Registry) Register(agent *Agent) {
	r.agents[agent.Name] = agent
}

// HasCapability checks if an agent has a specific capability
func (a *Agent) HasCapability(cap string) bool {
	for _, c := range a.Capabilities {
		if c == cap {
			return true
		}
	}
	return false
}

// GetCommand returns the full command to run the agent
func (a *Agent) GetCommand() []string {
	cmd := []string{a.Command}
	cmd = append(cmd, a.Args...)
	return cmd
}
