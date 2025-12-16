package coordinator

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"time"

	"github.com/astoreyai/goblin-forge/internal/agents"
	"github.com/astoreyai/goblin-forge/internal/config"
	"github.com/astoreyai/goblin-forge/internal/logging"
	"github.com/astoreyai/goblin-forge/internal/storage"
	"github.com/astoreyai/goblin-forge/internal/util"
	"github.com/google/uuid"
)

// Coordinator manages goblin lifecycle
type Coordinator struct {
	db  *storage.DB
	cfg *config.Config
	log *logging.Logger
}

// New creates a new coordinator
func New(db *storage.DB, cfg *config.Config, log *logging.Logger) *Coordinator {
	return &Coordinator{
		db:  db,
		cfg: cfg,
		log: log,
	}
}

// SpawnOptions contains options for spawning a goblin
type SpawnOptions struct {
	Name        string
	Agent       *agents.Agent
	ProjectPath string
	Branch      string
	Task        string
}

// Goblin represents a running agent instance
type Goblin struct {
	ID           string
	Name         string
	Agent        string
	Status       string
	ProjectPath  string
	WorktreePath string
	Branch       string
	TmuxSession  string
	CreatedAt    time.Time
	UpdatedAt    time.Time
}

// Age returns a human-readable age string
func (g *Goblin) Age() string {
	duration := time.Since(g.CreatedAt)

	if duration < time.Minute {
		return fmt.Sprintf("%ds", int(duration.Seconds()))
	} else if duration < time.Hour {
		return fmt.Sprintf("%dm", int(duration.Minutes()))
	} else if duration < 24*time.Hour {
		h := int(duration.Hours())
		m := int(duration.Minutes()) % 60
		return fmt.Sprintf("%dh %dm", h, m)
	}
	return fmt.Sprintf("%dd", int(duration.Hours()/24))
}

// Spawn creates and starts a new goblin
func (c *Coordinator) Spawn(opts SpawnOptions) (*Goblin, error) {
	// Check if name already exists
	existing, err := c.db.GetGoblin(opts.Name)
	if err != nil {
		return nil, fmt.Errorf("failed to check existing goblin: %w", err)
	}
	if existing != nil {
		return nil, fmt.Errorf("goblin with name '%s' already exists", opts.Name)
	}

	// Generate IDs
	goblinID := uuid.New().String()[:8]
	tmuxSession := fmt.Sprintf("gforge-%s", goblinID)

	// Create git worktree
	worktreePath, err := c.createWorktree(opts.ProjectPath, goblinID, opts.Branch)
	if err != nil {
		return nil, fmt.Errorf("failed to create worktree: %w", err)
	}

	// Create tmux session
	if err := c.createTmuxSession(tmuxSession, worktreePath); err != nil {
		// Cleanup worktree on failure
		c.removeWorktree(worktreePath)
		return nil, fmt.Errorf("failed to create tmux session: %w", err)
	}

	// Start the agent in tmux
	if err := c.startAgent(tmuxSession, opts.Agent, worktreePath); err != nil {
		c.killTmuxSession(tmuxSession)
		c.removeWorktree(worktreePath)
		return nil, fmt.Errorf("failed to start agent: %w", err)
	}

	// Create goblin record
	goblin := &storage.Goblin{
		ID:           goblinID,
		Name:         opts.Name,
		Agent:        opts.Agent.Name,
		Status:       "running",
		ProjectPath:  opts.ProjectPath,
		WorktreePath: worktreePath,
		Branch:       opts.Branch,
		TmuxSession:  tmuxSession,
	}

	if err := c.db.CreateGoblin(goblin); err != nil {
		c.killTmuxSession(tmuxSession)
		c.removeWorktree(worktreePath)
		return nil, fmt.Errorf("failed to save goblin: %w", err)
	}

	if c.log != nil {
		c.log.Info("Spawned goblin",
			logging.String("name", opts.Name),
			logging.String("agent", opts.Agent.Name),
			logging.String("branch", opts.Branch))
	}

	return &Goblin{
		ID:           goblinID,
		Name:         opts.Name,
		Agent:        opts.Agent.Name,
		Status:       "running",
		ProjectPath:  opts.ProjectPath,
		WorktreePath: worktreePath,
		Branch:       opts.Branch,
		TmuxSession:  tmuxSession,
		CreatedAt:    time.Now(),
	}, nil
}

// createWorktree creates a git worktree for isolation
func (c *Coordinator) createWorktree(projectPath, goblinID, branch string) (string, error) {
	worktreePath := filepath.Join(c.cfg.WorktreeBase, goblinID)

	// Check if project is a git repo
	gitDir := filepath.Join(projectPath, ".git")
	if _, err := os.Stat(gitDir); os.IsNotExist(err) {
		// Not a git repo, just create a symlink or copy
		if err := os.MkdirAll(worktreePath, 0755); err != nil {
			return "", err
		}
		// For non-git projects, we'll work in the original directory
		return projectPath, nil
	}

	// Create worktree with new branch
	cmd := exec.Command("git", "-C", projectPath, "worktree", "add", "-b", branch, worktreePath)
	output, err := cmd.CombinedOutput()
	if err != nil {
		// Branch might already exist, try without -b
		cmd = exec.Command("git", "-C", projectPath, "worktree", "add", worktreePath, branch)
		output, err = cmd.CombinedOutput()
		if err != nil {
			return "", fmt.Errorf("git worktree add failed: %s\n%s", err, string(output))
		}
	}

	return worktreePath, nil
}

// removeWorktree removes a git worktree
func (c *Coordinator) removeWorktree(worktreePath string) error {
	// Find the main repo to run git worktree remove
	cmd := exec.Command("git", "-C", worktreePath, "worktree", "remove", worktreePath, "--force")
	cmd.Run() // Ignore errors

	// Also try to remove the directory if it still exists
	os.RemoveAll(worktreePath)
	return nil
}

// createTmuxSession creates a new tmux session
func (c *Coordinator) createTmuxSession(sessionName, workdir string) error {
	socketName := c.cfg.Tmux.SocketName

	cmd := exec.Command("tmux", "-L", socketName,
		"new-session", "-d", "-s", sessionName, "-c", workdir)

	output, err := cmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("tmux new-session failed: %s\n%s", err, string(output))
	}

	return nil
}

// killTmuxSession kills a tmux session
func (c *Coordinator) killTmuxSession(sessionName string) error {
	socketName := c.cfg.Tmux.SocketName

	cmd := exec.Command("tmux", "-L", socketName, "kill-session", "-t", sessionName)
	cmd.Run() // Ignore errors
	return nil
}

// startAgent starts the agent CLI in the tmux session
func (c *Coordinator) startAgent(sessionName string, agent *agents.Agent, workdir string) error {
	socketName := c.cfg.Tmux.SocketName

	// Build command string with proper shell escaping
	cmdParts := agent.GetCommand()
	cmdStr := util.ShellJoin(cmdParts)

	// Send the command to tmux using literal mode (-l) to avoid key interpretation
	cmd := exec.Command("tmux", "-L", socketName,
		"send-keys", "-t", sessionName, "-l", cmdStr)

	output, err := cmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("tmux send-keys failed: %s\n%s", err, string(output))
	}

	// Send Enter separately (not literal)
	cmd = exec.Command("tmux", "-L", socketName,
		"send-keys", "-t", sessionName, "Enter")

	output, err = cmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("tmux send-keys Enter failed: %s\n%s", err, string(output))
	}

	return nil
}

// List returns all goblins
func (c *Coordinator) List() ([]*Goblin, error) {
	dbGoblins, err := c.db.ListGoblins()
	if err != nil {
		return nil, err
	}

	goblins := make([]*Goblin, len(dbGoblins))
	for i, g := range dbGoblins {
		goblins[i] = &Goblin{
			ID:           g.ID,
			Name:         g.Name,
			Agent:        g.Agent,
			Status:       g.Status,
			ProjectPath:  g.ProjectPath,
			WorktreePath: g.WorktreePath,
			Branch:       g.Branch,
			TmuxSession:  g.TmuxSession,
			CreatedAt:    g.CreatedAt,
			UpdatedAt:    g.UpdatedAt,
		}
	}

	return goblins, nil
}

// Get retrieves a goblin by name or ID
func (c *Coordinator) Get(nameOrID string) (*Goblin, error) {
	g, err := c.db.GetGoblin(nameOrID)
	if err != nil {
		return nil, err
	}
	if g == nil {
		return nil, nil
	}

	return &Goblin{
		ID:           g.ID,
		Name:         g.Name,
		Agent:        g.Agent,
		Status:       g.Status,
		ProjectPath:  g.ProjectPath,
		WorktreePath: g.WorktreePath,
		Branch:       g.Branch,
		TmuxSession:  g.TmuxSession,
		CreatedAt:    g.CreatedAt,
		UpdatedAt:    g.UpdatedAt,
	}, nil
}

// Stop stops a running goblin
func (c *Coordinator) Stop(nameOrID string) error {
	goblin, err := c.Get(nameOrID)
	if err != nil {
		return err
	}
	if goblin == nil {
		return fmt.Errorf("goblin not found: %s", nameOrID)
	}

	// Kill tmux session
	c.killTmuxSession(goblin.TmuxSession)

	// Remove worktree (optional - could keep for review)
	// c.removeWorktree(goblin.WorktreePath)

	// Update status
	if err := c.db.UpdateGoblinStatus(goblin.ID, "stopped"); err != nil {
		return err
	}

	if c.log != nil {
		c.log.Info("Stopped goblin",
			logging.String("name", goblin.Name),
			logging.String("id", goblin.ID))
	}

	return nil
}

// Kill forcefully kills a goblin and cleans up
func (c *Coordinator) Kill(nameOrID string) error {
	goblin, err := c.Get(nameOrID)
	if err != nil {
		return err
	}
	if goblin == nil {
		return fmt.Errorf("goblin not found: %s", nameOrID)
	}

	// Kill tmux session
	c.killTmuxSession(goblin.TmuxSession)

	// Remove worktree
	c.removeWorktree(goblin.WorktreePath)

	// Delete from database
	if err := c.db.DeleteGoblin(goblin.ID); err != nil {
		return err
	}

	if c.log != nil {
		c.log.Info("Killed goblin",
			logging.String("name", goblin.Name),
			logging.String("id", goblin.ID))
	}

	return nil
}

// Attach attaches to a goblin's tmux session
func (c *Coordinator) Attach(nameOrID string) error {
	goblin, err := c.Get(nameOrID)
	if err != nil {
		return err
	}
	if goblin == nil {
		return fmt.Errorf("goblin not found: %s", nameOrID)
	}

	socketName := c.cfg.Tmux.SocketName

	// Attach to tmux session (this replaces the current process)
	cmd := exec.Command("tmux", "-L", socketName, "attach-session", "-t", goblin.TmuxSession)
	cmd.Stdin = os.Stdin
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	return cmd.Run()
}

// Stats returns aggregate statistics
type Stats struct {
	Total     int
	Running   int
	Paused    int
	Completed int
}

// Stats returns goblin statistics
func (c *Coordinator) Stats() (*Stats, error) {
	dbStats, err := c.db.GetStats()
	if err != nil {
		return nil, err
	}

	return &Stats{
		Total:     dbStats.Total,
		Running:   dbStats.Running,
		Paused:    dbStats.Paused,
		Completed: dbStats.Completed,
	}, nil
}

// SendTask sends a task to a goblin
func (c *Coordinator) SendTask(nameOrID, task string) error {
	goblin, err := c.Get(nameOrID)
	if err != nil {
		return err
	}
	if goblin == nil {
		return fmt.Errorf("goblin not found: %s", nameOrID)
	}

	socketName := c.cfg.Tmux.SocketName

	// Send the task as literal text to avoid shell interpretation
	cmd := exec.Command("tmux", "-L", socketName,
		"send-keys", "-t", goblin.TmuxSession, "-l", task)

	output, err := cmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("failed to send task: %s\n%s", err, string(output))
	}

	// Send Enter separately
	cmd = exec.Command("tmux", "-L", socketName,
		"send-keys", "-t", goblin.TmuxSession, "Enter")

	output, err = cmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("failed to send Enter: %s\n%s", err, string(output))
	}

	if c.log != nil {
		c.log.Info("Sent task to goblin",
			logging.String("goblin", goblin.Name),
			logging.String("task", task))
	}

	return nil
}
