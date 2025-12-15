package workspace

import (
	"bufio"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"
)

// WorktreeManager handles git worktree operations
type WorktreeManager struct {
	basePath string
}

// Worktree represents a git worktree
type Worktree struct {
	Path       string
	Branch     string
	CommitHash string
	IsMain     bool
	CreatedAt  time.Time
}

// Config holds worktree manager configuration
type Config struct {
	BasePath string
}

// NewWorktreeManager creates a new worktree manager
func NewWorktreeManager(cfg Config) *WorktreeManager {
	if cfg.BasePath == "" {
		home, _ := os.UserHomeDir()
		cfg.BasePath = filepath.Join(home, ".local", "share", "gforge", "worktrees")
	}

	// Ensure base path exists
	os.MkdirAll(cfg.BasePath, 0755)

	return &WorktreeManager{
		basePath: cfg.BasePath,
	}
}

// Create creates a new git worktree
func (m *WorktreeManager) Create(repoPath, worktreeID, branchName string) (*Worktree, error) {
	// Validate repo path
	if !m.isGitRepo(repoPath) {
		return nil, fmt.Errorf("not a git repository: %s", repoPath)
	}

	// Generate worktree path
	worktreePath := filepath.Join(m.basePath, worktreeID)

	// Check if worktree path already exists
	if _, err := os.Stat(worktreePath); err == nil {
		return nil, fmt.Errorf("worktree path already exists: %s", worktreePath)
	}

	// Fetch latest from remote (optional, ignore errors)
	m.gitFetch(repoPath)

	// Check if branch already exists
	branchExists := m.branchExists(repoPath, branchName)

	var cmd *exec.Cmd
	if branchExists {
		// Use existing branch
		cmd = exec.Command("git", "-C", repoPath, "worktree", "add", worktreePath, branchName)
	} else {
		// Create new branch
		cmd = exec.Command("git", "-C", repoPath, "worktree", "add", "-b", branchName, worktreePath)
	}

	output, err := cmd.CombinedOutput()
	if err != nil {
		return nil, fmt.Errorf("failed to create worktree: %w\nOutput: %s", err, string(output))
	}

	// Get commit hash
	commitHash := m.getHeadCommit(worktreePath)

	return &Worktree{
		Path:       worktreePath,
		Branch:     branchName,
		CommitHash: commitHash,
		IsMain:     false,
		CreatedAt:  time.Now(),
	}, nil
}

// Remove removes a git worktree
func (m *WorktreeManager) Remove(worktreePath string, force bool) error {
	// Check if path exists
	if _, err := os.Stat(worktreePath); os.IsNotExist(err) {
		return nil // Already removed
	}

	// Find the main repo for this worktree
	mainRepo := m.getMainRepo(worktreePath)
	if mainRepo == "" {
		// Not a worktree, just remove the directory
		return os.RemoveAll(worktreePath)
	}

	// Remove worktree using git
	args := []string{"-C", mainRepo, "worktree", "remove", worktreePath}
	if force {
		args = append(args, "--force")
	}

	cmd := exec.Command("git", args...)
	output, err := cmd.CombinedOutput()
	if err != nil {
		// Try force remove if regular remove fails
		if !force {
			return m.Remove(worktreePath, true)
		}
		// Last resort: remove directory manually
		os.RemoveAll(worktreePath)
		// Prune worktrees
		exec.Command("git", "-C", mainRepo, "worktree", "prune").Run()
		return nil
	}

	_ = output
	return nil
}

// List lists all worktrees for a repository
func (m *WorktreeManager) List(repoPath string) ([]*Worktree, error) {
	if !m.isGitRepo(repoPath) {
		return nil, fmt.Errorf("not a git repository: %s", repoPath)
	}

	cmd := exec.Command("git", "-C", repoPath, "worktree", "list", "--porcelain")
	output, err := cmd.Output()
	if err != nil {
		return nil, fmt.Errorf("failed to list worktrees: %w", err)
	}

	return m.parseWorktreeList(string(output))
}

// parseWorktreeList parses the porcelain output of git worktree list
func (m *WorktreeManager) parseWorktreeList(output string) ([]*Worktree, error) {
	var worktrees []*Worktree
	var current *Worktree

	scanner := bufio.NewScanner(strings.NewReader(output))
	for scanner.Scan() {
		line := scanner.Text()

		if strings.HasPrefix(line, "worktree ") {
			if current != nil {
				worktrees = append(worktrees, current)
			}
			current = &Worktree{
				Path: strings.TrimPrefix(line, "worktree "),
			}
		} else if strings.HasPrefix(line, "HEAD ") {
			if current != nil {
				current.CommitHash = strings.TrimPrefix(line, "HEAD ")
			}
		} else if strings.HasPrefix(line, "branch ") {
			if current != nil {
				branch := strings.TrimPrefix(line, "branch ")
				// Remove refs/heads/ prefix
				branch = strings.TrimPrefix(branch, "refs/heads/")
				current.Branch = branch
			}
		} else if line == "bare" {
			// Main worktree indicator for bare repos
			if current != nil {
				current.IsMain = true
			}
		}
	}

	// Don't forget the last one
	if current != nil {
		worktrees = append(worktrees, current)
	}

	return worktrees, nil
}

// Get retrieves a worktree by path
func (m *WorktreeManager) Get(worktreePath string) (*Worktree, error) {
	if _, err := os.Stat(worktreePath); os.IsNotExist(err) {
		return nil, fmt.Errorf("worktree not found: %s", worktreePath)
	}

	if !m.isGitRepo(worktreePath) {
		return nil, fmt.Errorf("not a git worktree: %s", worktreePath)
	}

	branch := m.getCurrentBranch(worktreePath)
	commitHash := m.getHeadCommit(worktreePath)

	return &Worktree{
		Path:       worktreePath,
		Branch:     branch,
		CommitHash: commitHash,
	}, nil
}

// GetChanges returns the list of changed files in a worktree
func (m *WorktreeManager) GetChanges(worktreePath string) ([]string, error) {
	cmd := exec.Command("git", "-C", worktreePath, "status", "--porcelain")
	output, err := cmd.Output()
	if err != nil {
		return nil, fmt.Errorf("failed to get changes: %w", err)
	}

	var changes []string
	scanner := bufio.NewScanner(strings.NewReader(string(output)))
	for scanner.Scan() {
		line := scanner.Text()
		if len(line) > 3 {
			changes = append(changes, strings.TrimSpace(line[3:]))
		}
	}

	return changes, nil
}

// GetDiff returns the diff for a worktree
func (m *WorktreeManager) GetDiff(worktreePath string, staged bool) (string, error) {
	args := []string{"-C", worktreePath, "diff"}
	if staged {
		args = append(args, "--staged")
	}

	cmd := exec.Command("git", args...)
	output, err := cmd.Output()
	if err != nil {
		return "", fmt.Errorf("failed to get diff: %w", err)
	}

	return string(output), nil
}

// Commit commits changes in a worktree
func (m *WorktreeManager) Commit(worktreePath, message string) (string, error) {
	// Stage all changes
	stageCmd := exec.Command("git", "-C", worktreePath, "add", "-A")
	if output, err := stageCmd.CombinedOutput(); err != nil {
		return "", fmt.Errorf("failed to stage changes: %w\nOutput: %s", err, string(output))
	}

	// Commit
	commitCmd := exec.Command("git", "-C", worktreePath, "commit", "-m", message)
	output, err := commitCmd.CombinedOutput()
	if err != nil {
		// Check if there's nothing to commit
		if strings.Contains(string(output), "nothing to commit") {
			return "", fmt.Errorf("nothing to commit")
		}
		return "", fmt.Errorf("failed to commit: %w\nOutput: %s", err, string(output))
	}

	// Get the new commit hash
	hash := m.getHeadCommit(worktreePath)
	return hash, nil
}

// Push pushes the worktree branch to remote
func (m *WorktreeManager) Push(worktreePath string, force bool) error {
	branch := m.getCurrentBranch(worktreePath)

	args := []string{"-C", worktreePath, "push", "-u", "origin", branch}
	if force {
		args = append(args[:len(args)-2], "--force", args[len(args)-2], args[len(args)-1])
	}

	cmd := exec.Command("git", args...)
	output, err := cmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("failed to push: %w\nOutput: %s", err, string(output))
	}

	return nil
}

// Stash stashes changes in a worktree
func (m *WorktreeManager) Stash(worktreePath, message string) error {
	args := []string{"-C", worktreePath, "stash", "push"}
	if message != "" {
		args = append(args, "-m", message)
	}

	cmd := exec.Command("git", args...)
	output, err := cmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("failed to stash: %w\nOutput: %s", err, string(output))
	}

	return nil
}

// StashPop pops the latest stash
func (m *WorktreeManager) StashPop(worktreePath string) error {
	cmd := exec.Command("git", "-C", worktreePath, "stash", "pop")
	output, err := cmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("failed to pop stash: %w\nOutput: %s", err, string(output))
	}

	return nil
}

// Prune removes stale worktree entries
func (m *WorktreeManager) Prune(repoPath string) error {
	cmd := exec.Command("git", "-C", repoPath, "worktree", "prune")
	output, err := cmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("failed to prune: %w\nOutput: %s", err, string(output))
	}

	return nil
}

// CleanupOld removes worktrees older than the specified duration
func (m *WorktreeManager) CleanupOld(maxAge time.Duration) ([]string, error) {
	var removed []string

	entries, err := os.ReadDir(m.basePath)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, nil
		}
		return nil, err
	}

	for _, entry := range entries {
		if !entry.IsDir() {
			continue
		}

		path := filepath.Join(m.basePath, entry.Name())
		info, err := entry.Info()
		if err != nil {
			continue
		}

		if time.Since(info.ModTime()) > maxAge {
			if err := m.Remove(path, true); err == nil {
				removed = append(removed, path)
			}
		}
	}

	return removed, nil
}

// Helper functions

func (m *WorktreeManager) isGitRepo(path string) bool {
	gitDir := filepath.Join(path, ".git")
	if info, err := os.Stat(gitDir); err == nil {
		// .git can be a directory or a file (for worktrees)
		return info.IsDir() || info.Mode().IsRegular()
	}
	return false
}

func (m *WorktreeManager) branchExists(repoPath, branch string) bool {
	cmd := exec.Command("git", "-C", repoPath, "rev-parse", "--verify", branch)
	return cmd.Run() == nil
}

func (m *WorktreeManager) gitFetch(repoPath string) {
	cmd := exec.Command("git", "-C", repoPath, "fetch", "--all", "--prune")
	cmd.Run() // Ignore errors
}

func (m *WorktreeManager) getHeadCommit(worktreePath string) string {
	cmd := exec.Command("git", "-C", worktreePath, "rev-parse", "--short", "HEAD")
	output, err := cmd.Output()
	if err != nil {
		return ""
	}
	return strings.TrimSpace(string(output))
}

func (m *WorktreeManager) getCurrentBranch(worktreePath string) string {
	cmd := exec.Command("git", "-C", worktreePath, "rev-parse", "--abbrev-ref", "HEAD")
	output, err := cmd.Output()
	if err != nil {
		return ""
	}
	return strings.TrimSpace(string(output))
}

func (m *WorktreeManager) getMainRepo(worktreePath string) string {
	// Read .git file to find the main repo
	gitFile := filepath.Join(worktreePath, ".git")
	content, err := os.ReadFile(gitFile)
	if err != nil {
		return ""
	}

	// Parse "gitdir: /path/to/main/.git/worktrees/name"
	line := strings.TrimSpace(string(content))
	if strings.HasPrefix(line, "gitdir: ") {
		gitdir := strings.TrimPrefix(line, "gitdir: ")
		// Go up from .git/worktrees/name to main repo
		parts := strings.Split(gitdir, string(os.PathSeparator))
		for i, part := range parts {
			if part == "worktrees" && i > 0 {
				// Found it - reconstruct path to main repo
				mainGitDir := strings.Join(parts[:i], string(os.PathSeparator))
				return filepath.Dir(mainGitDir)
			}
		}
	}

	return ""
}

// GetBasePath returns the base path for worktrees
func (m *WorktreeManager) GetBasePath() string {
	return m.basePath
}
