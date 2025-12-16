package mcp

import (
	"fmt"

	mcp_golang "github.com/metoro-io/mcp-golang"
	"github.com/metoro-io/mcp-golang/transport/stdio"

	"github.com/astoreyai/goblin-forge/internal/agents"
	"github.com/astoreyai/goblin-forge/internal/coordinator"
	"github.com/astoreyai/goblin-forge/internal/tmux"
)

// Server is the MCP server for goblin-forge.
type Server struct {
	coord    *coordinator.Coordinator
	registry *agents.Registry
	tmuxMgr  *tmux.Manager
	server   *mcp_golang.Server
}

// Config contains configuration for the MCP server.
type Config struct {
	TmuxSocket string
}

// NewServer creates a new MCP server.
func NewServer(coord *coordinator.Coordinator, registry *agents.Registry, cfg Config) *Server {
	transport := stdio.NewStdioServerTransport()
	server := mcp_golang.NewServer(transport)

	s := &Server{
		coord:    coord,
		registry: registry,
		tmuxMgr: tmux.NewManager(tmux.Config{
			SocketName: cfg.TmuxSocket,
		}),
		server: server,
	}

	s.registerTools()
	return s
}

// Serve starts the MCP server and blocks until done.
func (s *Server) Serve() error {
	return s.server.Serve()
}

// registerTools registers all goblin-forge MCP tools.
func (s *Server) registerTools() {
	// gforge_spawn - Spawn a new goblin
	s.server.RegisterTool(
		"gforge_spawn",
		"Spawn a new goblin (isolated agent instance) with its own tmux session and git worktree",
		s.handleSpawn,
	)

	// gforge_list - List all goblins
	s.server.RegisterTool(
		"gforge_list",
		"List all goblins with their status, agent type, and branch",
		s.handleList,
	)

	// gforge_status - Get detailed goblin status
	s.server.RegisterTool(
		"gforge_status",
		"Get detailed status of a specific goblin including its tmux session and worktree path",
		s.handleStatus,
	)

	// gforge_send - Send text/command to a goblin
	s.server.RegisterTool(
		"gforge_send",
		"Send text or a command to a goblin's tmux session",
		s.handleSend,
	)

	// gforge_output - Get recent output from a goblin
	s.server.RegisterTool(
		"gforge_output",
		"Get recent terminal output from a goblin's tmux session",
		s.handleOutput,
	)

	// gforge_stop - Stop a goblin
	s.server.RegisterTool(
		"gforge_stop",
		"Stop a running goblin (keeps worktree for review)",
		s.handleStop,
	)

	// gforge_kill - Kill a goblin and cleanup
	s.server.RegisterTool(
		"gforge_kill",
		"Kill a goblin and remove its tmux session and worktree",
		s.handleKill,
	)

	// gforge_stats - Get aggregate statistics
	s.server.RegisterTool(
		"gforge_stats",
		"Get aggregate statistics about all goblins",
		s.handleStats,
	)
}

// === Tool Argument Structs ===

// SpawnArgs are the arguments for gforge_spawn.
type SpawnArgs struct {
	Name        string `json:"name" jsonschema:"required,description=Unique name for the goblin"`
	Agent       string `json:"agent" jsonschema:"required,description=Agent to use (claude, crush, codex, gemini, ollama)"`
	ProjectPath string `json:"project_path" jsonschema:"description=Path to the project directory (defaults to current directory)"`
	Branch      string `json:"branch" jsonschema:"description=Git branch name (auto-generated if empty)"`
	Task        string `json:"task" jsonschema:"description=Initial task to send to the agent after spawning"`
}

// ListArgs are the arguments for gforge_list.
type ListArgs struct {
	StatusFilter string `json:"status_filter" jsonschema:"description=Filter by status (running, stopped, all). Defaults to all"`
}

// GoblinIDArgs are the arguments for tools that take a goblin ID.
type GoblinIDArgs struct {
	GoblinID string `json:"goblin_id" jsonschema:"required,description=Name or ID of the goblin"`
}

// SendArgs are the arguments for gforge_send.
type SendArgs struct {
	GoblinID string `json:"goblin_id" jsonschema:"required,description=Name or ID of the goblin"`
	Text     string `json:"text" jsonschema:"required,description=Text to send to the goblin's terminal"`
}

// OutputArgs are the arguments for gforge_output.
type OutputArgs struct {
	GoblinID string `json:"goblin_id" jsonschema:"required,description=Name or ID of the goblin"`
	Lines    int    `json:"lines" jsonschema:"description=Number of lines to retrieve (default 50)"`
}

// === Tool Handlers ===

func (s *Server) handleSpawn(args SpawnArgs) (*mcp_golang.ToolResponse, error) {
	// Validate agent
	agent := s.registry.Get(args.Agent)
	if agent == nil {
		return nil, fmt.Errorf("unknown agent: %s", args.Agent)
	}

	// Default project path
	projectPath := args.ProjectPath
	if projectPath == "" {
		projectPath = "."
	}

	// Default branch
	branch := args.Branch
	if branch == "" {
		branch = fmt.Sprintf("gforge/%s", args.Name)
	}

	// Spawn the goblin
	goblin, err := s.coord.Spawn(coordinator.SpawnOptions{
		Name:        args.Name,
		Agent:       agent,
		ProjectPath: projectPath,
		Branch:      branch,
	})
	if err != nil {
		return nil, fmt.Errorf("failed to spawn goblin: %w", err)
	}

	// Send initial task if provided
	if args.Task != "" {
		if err := s.coord.SendTask(goblin.Name, args.Task); err != nil {
			// Log but don't fail - goblin is already spawned
			return mcp_golang.NewToolResponse(mcp_golang.NewTextContent(
				fmt.Sprintf("Spawned goblin '%s' (ID: %s) with agent '%s' on branch '%s'. Warning: failed to send initial task: %v",
					goblin.Name, goblin.ID, goblin.Agent, goblin.Branch, err),
			)), nil
		}
	}

	return mcp_golang.NewToolResponse(mcp_golang.NewTextContent(
		fmt.Sprintf("Spawned goblin '%s' (ID: %s) with agent '%s' on branch '%s'. Worktree: %s",
			goblin.Name, goblin.ID, goblin.Agent, goblin.Branch, goblin.WorktreePath),
	)), nil
}

func (s *Server) handleList(args ListArgs) (*mcp_golang.ToolResponse, error) {
	goblins, err := s.coord.List()
	if err != nil {
		return nil, fmt.Errorf("failed to list goblins: %w", err)
	}

	if len(goblins) == 0 {
		return mcp_golang.NewToolResponse(mcp_golang.NewTextContent("No goblins found.")), nil
	}

	// Filter by status if specified
	var filtered []*coordinator.Goblin
	for _, g := range goblins {
		if args.StatusFilter == "" || args.StatusFilter == "all" || g.Status == args.StatusFilter {
			filtered = append(filtered, g)
		}
	}

	if len(filtered) == 0 {
		return mcp_golang.NewToolResponse(mcp_golang.NewTextContent(
			fmt.Sprintf("No goblins with status '%s'.", args.StatusFilter),
		)), nil
	}

	// Build response
	result := fmt.Sprintf("Found %d goblin(s):\n\n", len(filtered))
	for _, g := range filtered {
		result += fmt.Sprintf("- %s (ID: %s)\n  Agent: %s | Status: %s | Branch: %s | Age: %s\n",
			g.Name, g.ID, g.Agent, g.Status, g.Branch, g.Age())
	}

	return mcp_golang.NewToolResponse(mcp_golang.NewTextContent(result)), nil
}

func (s *Server) handleStatus(args GoblinIDArgs) (*mcp_golang.ToolResponse, error) {
	goblin, err := s.coord.Get(args.GoblinID)
	if err != nil {
		return nil, fmt.Errorf("failed to get goblin: %w", err)
	}
	if goblin == nil {
		return nil, fmt.Errorf("goblin not found: %s", args.GoblinID)
	}

	result := fmt.Sprintf(`Goblin: %s
ID: %s
Agent: %s
Status: %s
Branch: %s
Project: %s
Worktree: %s
Tmux Session: %s
Age: %s`,
		goblin.Name, goblin.ID, goblin.Agent, goblin.Status,
		goblin.Branch, goblin.ProjectPath, goblin.WorktreePath,
		goblin.TmuxSession, goblin.Age())

	return mcp_golang.NewToolResponse(mcp_golang.NewTextContent(result)), nil
}

func (s *Server) handleSend(args SendArgs) (*mcp_golang.ToolResponse, error) {
	goblin, err := s.coord.Get(args.GoblinID)
	if err != nil {
		return nil, fmt.Errorf("failed to get goblin: %w", err)
	}
	if goblin == nil {
		return nil, fmt.Errorf("goblin not found: %s", args.GoblinID)
	}

	if err := s.coord.SendTask(args.GoblinID, args.Text); err != nil {
		return nil, fmt.Errorf("failed to send to goblin: %w", err)
	}

	return mcp_golang.NewToolResponse(mcp_golang.NewTextContent(
		fmt.Sprintf("Sent to '%s': %s", goblin.Name, args.Text),
	)), nil
}

func (s *Server) handleOutput(args OutputArgs) (*mcp_golang.ToolResponse, error) {
	goblin, err := s.coord.Get(args.GoblinID)
	if err != nil {
		return nil, fmt.Errorf("failed to get goblin: %w", err)
	}
	if goblin == nil {
		return nil, fmt.Errorf("goblin not found: %s", args.GoblinID)
	}

	lines := args.Lines
	if lines <= 0 {
		lines = 50
	}

	output, err := s.tmuxMgr.CapturePane(goblin.TmuxSession, lines)
	if err != nil {
		return nil, fmt.Errorf("failed to capture output: %w", err)
	}

	return mcp_golang.NewToolResponse(mcp_golang.NewTextContent(
		fmt.Sprintf("=== Output from %s (last %d lines) ===\n\n%s", goblin.Name, lines, output),
	)), nil
}

func (s *Server) handleStop(args GoblinIDArgs) (*mcp_golang.ToolResponse, error) {
	if err := s.coord.Stop(args.GoblinID); err != nil {
		return nil, fmt.Errorf("failed to stop goblin: %w", err)
	}

	return mcp_golang.NewToolResponse(mcp_golang.NewTextContent(
		fmt.Sprintf("Stopped goblin: %s", args.GoblinID),
	)), nil
}

func (s *Server) handleKill(args GoblinIDArgs) (*mcp_golang.ToolResponse, error) {
	if err := s.coord.Kill(args.GoblinID); err != nil {
		return nil, fmt.Errorf("failed to kill goblin: %w", err)
	}

	return mcp_golang.NewToolResponse(mcp_golang.NewTextContent(
		fmt.Sprintf("Killed goblin: %s (tmux session terminated, worktree removed)", args.GoblinID),
	)), nil
}

func (s *Server) handleStats(args struct{}) (*mcp_golang.ToolResponse, error) {
	stats, err := s.coord.Stats()
	if err != nil {
		return nil, fmt.Errorf("failed to get stats: %w", err)
	}

	result := fmt.Sprintf(`Goblin Forge Statistics:
- Running:   %d
- Paused:    %d
- Completed: %d
- Total:     %d`,
		stats.Running, stats.Paused, stats.Completed, stats.Total)

	return mcp_golang.NewToolResponse(mcp_golang.NewTextContent(result)), nil
}
