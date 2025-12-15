package workspace

import (
	"os"
	"os/exec"
	"path/filepath"
	"testing"
)

func TestNewWorktreeManager(t *testing.T) {
	mgr := NewWorktreeManager(Config{})
	if mgr == nil {
		t.Fatal("Manager should not be nil")
	}

	if mgr.basePath == "" {
		t.Error("Base path should have default value")
	}
}

func TestNewWorktreeManagerCustomPath(t *testing.T) {
	tmpDir, _ := os.MkdirTemp("", "gforge-ws-test-*")
	defer os.RemoveAll(tmpDir)

	mgr := NewWorktreeManager(Config{
		BasePath: tmpDir,
	})

	if mgr.basePath != tmpDir {
		t.Errorf("Expected base path '%s', got '%s'", tmpDir, mgr.basePath)
	}
}

func TestGetBasePath(t *testing.T) {
	tmpDir, _ := os.MkdirTemp("", "gforge-ws-test-*")
	defer os.RemoveAll(tmpDir)

	mgr := NewWorktreeManager(Config{
		BasePath: tmpDir,
	})

	if mgr.GetBasePath() != tmpDir {
		t.Errorf("Expected '%s', got '%s'", tmpDir, mgr.GetBasePath())
	}
}

// Helper to check if git is available
func gitAvailable() bool {
	_, err := exec.LookPath("git")
	return err == nil
}

// Helper to create a test git repo
func createTestRepo(t *testing.T) (string, func()) {
	tmpDir, err := os.MkdirTemp("", "gforge-ws-repo-*")
	if err != nil {
		t.Fatalf("Failed to create temp dir: %v", err)
	}

	cleanup := func() {
		os.RemoveAll(tmpDir)
	}

	// Initialize git repo
	cmd := exec.Command("git", "init", tmpDir)
	if err := cmd.Run(); err != nil {
		cleanup()
		t.Fatalf("Failed to init git repo: %v", err)
	}

	// Configure git
	exec.Command("git", "-C", tmpDir, "config", "user.email", "test@test.com").Run()
	exec.Command("git", "-C", tmpDir, "config", "user.name", "Test").Run()

	// Create initial commit
	testFile := filepath.Join(tmpDir, "README.md")
	os.WriteFile(testFile, []byte("# Test\n"), 0644)
	exec.Command("git", "-C", tmpDir, "add", ".").Run()
	exec.Command("git", "-C", tmpDir, "commit", "-m", "Initial commit").Run()

	return tmpDir, cleanup
}

func TestIsGitRepo(t *testing.T) {
	if !gitAvailable() {
		t.Skip("git not available")
	}

	repoPath, cleanup := createTestRepo(t)
	defer cleanup()

	mgr := NewWorktreeManager(Config{})

	if !mgr.isGitRepo(repoPath) {
		t.Error("Should detect as git repo")
	}

	// Test non-repo
	tmpDir, _ := os.MkdirTemp("", "gforge-ws-nonrepo-*")
	defer os.RemoveAll(tmpDir)

	if mgr.isGitRepo(tmpDir) {
		t.Error("Should not detect non-repo as git repo")
	}
}

func TestCreateWorktree(t *testing.T) {
	if !gitAvailable() {
		t.Skip("git not available")
	}

	repoPath, cleanup := createTestRepo(t)
	defer cleanup()

	wtDir, _ := os.MkdirTemp("", "gforge-ws-worktrees-*")
	defer os.RemoveAll(wtDir)

	mgr := NewWorktreeManager(Config{
		BasePath: wtDir,
	})

	// Create worktree
	wt, err := mgr.Create(repoPath, "test-wt", "gforge/test-branch")
	if err != nil {
		t.Fatalf("Failed to create worktree: %v", err)
	}

	if wt.Branch != "gforge/test-branch" {
		t.Errorf("Expected branch 'gforge/test-branch', got '%s'", wt.Branch)
	}

	if wt.Path == "" {
		t.Error("Worktree path should not be empty")
	}

	// Verify worktree exists
	if _, err := os.Stat(wt.Path); os.IsNotExist(err) {
		t.Error("Worktree directory should exist")
	}
}

func TestCreateWorktreeNotGitRepo(t *testing.T) {
	tmpDir, _ := os.MkdirTemp("", "gforge-ws-nonrepo-*")
	defer os.RemoveAll(tmpDir)

	mgr := NewWorktreeManager(Config{
		BasePath: tmpDir,
	})

	_, err := mgr.Create(tmpDir, "test-wt", "test-branch")
	if err == nil {
		t.Error("Should fail for non-git repo")
	}
}

func TestRemoveWorktree(t *testing.T) {
	if !gitAvailable() {
		t.Skip("git not available")
	}

	repoPath, cleanup := createTestRepo(t)
	defer cleanup()

	wtDir, _ := os.MkdirTemp("", "gforge-ws-worktrees-*")
	defer os.RemoveAll(wtDir)

	mgr := NewWorktreeManager(Config{
		BasePath: wtDir,
	})

	// Create worktree
	wt, err := mgr.Create(repoPath, "remove-test", "gforge/remove-branch")
	if err != nil {
		t.Fatalf("Failed to create worktree: %v", err)
	}

	// Remove worktree
	err = mgr.Remove(wt.Path, false)
	if err != nil {
		t.Fatalf("Failed to remove worktree: %v", err)
	}

	// Verify worktree is removed
	if _, err := os.Stat(wt.Path); !os.IsNotExist(err) {
		t.Error("Worktree directory should be removed")
	}
}

func TestListWorktrees(t *testing.T) {
	if !gitAvailable() {
		t.Skip("git not available")
	}

	repoPath, cleanup := createTestRepo(t)
	defer cleanup()

	wtDir, _ := os.MkdirTemp("", "gforge-ws-worktrees-*")
	defer os.RemoveAll(wtDir)

	mgr := NewWorktreeManager(Config{
		BasePath: wtDir,
	})

	// Create multiple worktrees
	_, err := mgr.Create(repoPath, "list-test-1", "gforge/list-branch-1")
	if err != nil {
		t.Fatalf("Failed to create worktree 1: %v", err)
	}

	_, err = mgr.Create(repoPath, "list-test-2", "gforge/list-branch-2")
	if err != nil {
		t.Fatalf("Failed to create worktree 2: %v", err)
	}

	// List worktrees
	worktrees, err := mgr.List(repoPath)
	if err != nil {
		t.Fatalf("Failed to list worktrees: %v", err)
	}

	// Should have main + 2 created = 3
	if len(worktrees) < 3 {
		t.Errorf("Expected at least 3 worktrees, got %d", len(worktrees))
	}
}

func TestGetWorktree(t *testing.T) {
	if !gitAvailable() {
		t.Skip("git not available")
	}

	repoPath, cleanup := createTestRepo(t)
	defer cleanup()

	wtDir, _ := os.MkdirTemp("", "gforge-ws-worktrees-*")
	defer os.RemoveAll(wtDir)

	mgr := NewWorktreeManager(Config{
		BasePath: wtDir,
	})

	// Create worktree
	created, err := mgr.Create(repoPath, "get-test", "gforge/get-branch")
	if err != nil {
		t.Fatalf("Failed to create worktree: %v", err)
	}

	// Get worktree
	wt, err := mgr.Get(created.Path)
	if err != nil {
		t.Fatalf("Failed to get worktree: %v", err)
	}

	if wt.Branch != "gforge/get-branch" {
		t.Errorf("Expected branch 'gforge/get-branch', got '%s'", wt.Branch)
	}
}

func TestGetChanges(t *testing.T) {
	if !gitAvailable() {
		t.Skip("git not available")
	}

	repoPath, cleanup := createTestRepo(t)
	defer cleanup()

	wtDir, _ := os.MkdirTemp("", "gforge-ws-worktrees-*")
	defer os.RemoveAll(wtDir)

	mgr := NewWorktreeManager(Config{
		BasePath: wtDir,
	})

	// Create worktree
	wt, err := mgr.Create(repoPath, "changes-test", "gforge/changes-branch")
	if err != nil {
		t.Fatalf("Failed to create worktree: %v", err)
	}

	// Initially no changes
	changes, err := mgr.GetChanges(wt.Path)
	if err != nil {
		t.Fatalf("Failed to get changes: %v", err)
	}

	if len(changes) != 0 {
		t.Errorf("Expected no changes, got %d", len(changes))
	}

	// Create a change
	testFile := filepath.Join(wt.Path, "new-file.txt")
	os.WriteFile(testFile, []byte("test content\n"), 0644)

	// Now should have changes
	changes, err = mgr.GetChanges(wt.Path)
	if err != nil {
		t.Fatalf("Failed to get changes: %v", err)
	}

	if len(changes) != 1 {
		t.Errorf("Expected 1 change, got %d", len(changes))
	}
}

func TestGetDiff(t *testing.T) {
	if !gitAvailable() {
		t.Skip("git not available")
	}

	repoPath, cleanup := createTestRepo(t)
	defer cleanup()

	wtDir, _ := os.MkdirTemp("", "gforge-ws-worktrees-*")
	defer os.RemoveAll(wtDir)

	mgr := NewWorktreeManager(Config{
		BasePath: wtDir,
	})

	// Create worktree
	wt, err := mgr.Create(repoPath, "diff-test", "gforge/diff-branch")
	if err != nil {
		t.Fatalf("Failed to create worktree: %v", err)
	}

	// Create a change
	testFile := filepath.Join(wt.Path, "README.md")
	os.WriteFile(testFile, []byte("# Modified\n"), 0644)

	// Get diff
	diff, err := mgr.GetDiff(wt.Path, false)
	if err != nil {
		t.Fatalf("Failed to get diff: %v", err)
	}

	if diff == "" {
		t.Error("Diff should not be empty")
	}
}

func TestCommit(t *testing.T) {
	if !gitAvailable() {
		t.Skip("git not available")
	}

	repoPath, cleanup := createTestRepo(t)
	defer cleanup()

	wtDir, _ := os.MkdirTemp("", "gforge-ws-worktrees-*")
	defer os.RemoveAll(wtDir)

	mgr := NewWorktreeManager(Config{
		BasePath: wtDir,
	})

	// Create worktree
	wt, err := mgr.Create(repoPath, "commit-test", "gforge/commit-branch")
	if err != nil {
		t.Fatalf("Failed to create worktree: %v", err)
	}

	// Create a change
	testFile := filepath.Join(wt.Path, "new-file.txt")
	os.WriteFile(testFile, []byte("test content\n"), 0644)

	// Commit
	hash, err := mgr.Commit(wt.Path, "Test commit")
	if err != nil {
		t.Fatalf("Failed to commit: %v", err)
	}

	if hash == "" {
		t.Error("Commit hash should not be empty")
	}

	// Should have no changes now
	changes, _ := mgr.GetChanges(wt.Path)
	if len(changes) != 0 {
		t.Errorf("Expected no changes after commit, got %d", len(changes))
	}
}

func TestCommitNoChanges(t *testing.T) {
	if !gitAvailable() {
		t.Skip("git not available")
	}

	repoPath, cleanup := createTestRepo(t)
	defer cleanup()

	wtDir, _ := os.MkdirTemp("", "gforge-ws-worktrees-*")
	defer os.RemoveAll(wtDir)

	mgr := NewWorktreeManager(Config{
		BasePath: wtDir,
	})

	// Create worktree
	wt, err := mgr.Create(repoPath, "nochange-test", "gforge/nochange-branch")
	if err != nil {
		t.Fatalf("Failed to create worktree: %v", err)
	}

	// Try to commit with no changes
	_, err = mgr.Commit(wt.Path, "No changes commit")
	if err == nil {
		t.Error("Should fail when there are no changes")
	}
}

func TestStash(t *testing.T) {
	if !gitAvailable() {
		t.Skip("git not available")
	}

	repoPath, cleanup := createTestRepo(t)
	defer cleanup()

	wtDir, _ := os.MkdirTemp("", "gforge-ws-worktrees-*")
	defer os.RemoveAll(wtDir)

	mgr := NewWorktreeManager(Config{
		BasePath: wtDir,
	})

	// Create worktree
	wt, err := mgr.Create(repoPath, "stash-test", "gforge/stash-branch")
	if err != nil {
		t.Fatalf("Failed to create worktree: %v", err)
	}

	// Create a change
	testFile := filepath.Join(wt.Path, "stash-file.txt")
	os.WriteFile(testFile, []byte("stash content\n"), 0644)

	// Stash
	err = mgr.Stash(wt.Path, "Test stash")
	if err != nil {
		t.Fatalf("Failed to stash: %v", err)
	}

	// Should have no changes now
	changes, _ := mgr.GetChanges(wt.Path)
	if len(changes) != 0 {
		t.Errorf("Expected no changes after stash, got %d", len(changes))
	}
}

func TestPrune(t *testing.T) {
	if !gitAvailable() {
		t.Skip("git not available")
	}

	repoPath, cleanup := createTestRepo(t)
	defer cleanup()

	mgr := NewWorktreeManager(Config{})

	// Prune should not error
	err := mgr.Prune(repoPath)
	if err != nil {
		t.Fatalf("Failed to prune: %v", err)
	}
}

func TestParseWorktreeList(t *testing.T) {
	mgr := NewWorktreeManager(Config{})

	input := `worktree /home/user/project
HEAD abc123def456
branch refs/heads/main

worktree /home/user/project-wt
HEAD def456abc123
branch refs/heads/feature/test

`

	worktrees, err := mgr.parseWorktreeList(input)
	if err != nil {
		t.Fatalf("Failed to parse: %v", err)
	}

	if len(worktrees) != 2 {
		t.Fatalf("Expected 2 worktrees, got %d", len(worktrees))
	}

	if worktrees[0].Path != "/home/user/project" {
		t.Errorf("Expected path '/home/user/project', got '%s'", worktrees[0].Path)
	}

	if worktrees[0].Branch != "main" {
		t.Errorf("Expected branch 'main', got '%s'", worktrees[0].Branch)
	}

	if worktrees[1].Branch != "feature/test" {
		t.Errorf("Expected branch 'feature/test', got '%s'", worktrees[1].Branch)
	}
}
