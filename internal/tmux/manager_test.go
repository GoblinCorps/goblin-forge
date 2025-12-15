package tmux

import (
	"os"
	"os/exec"
	"path/filepath"
	"testing"
)

func TestNewManager(t *testing.T) {
	cfg := Config{
		SocketName: "gforge-test",
	}

	mgr := NewManager(cfg)
	if mgr == nil {
		t.Fatal("Manager should not be nil")
	}

	if mgr.socketName != "gforge-test" {
		t.Errorf("Expected socket name 'gforge-test', got '%s'", mgr.socketName)
	}
}

func TestNewManagerDefaults(t *testing.T) {
	mgr := NewManager(Config{})

	if mgr.socketName != "gforge" {
		t.Errorf("Expected default socket name 'gforge', got '%s'", mgr.socketName)
	}

	if mgr.captureDir == "" {
		t.Error("Capture directory should not be empty")
	}
}

func TestSessionStatus(t *testing.T) {
	tests := []struct {
		status SessionStatus
		str    string
	}{
		{StatusCreated, "created"},
		{StatusRunning, "running"},
		{StatusAttached, "attached"},
		{StatusDetached, "detached"},
		{StatusDead, "dead"},
	}

	for _, tc := range tests {
		if string(tc.status) != tc.str {
			t.Errorf("Expected '%s', got '%s'", tc.str, string(tc.status))
		}
	}
}

// Integration tests - only run if tmux is available
func tmuxAvailable() bool {
	_, err := exec.LookPath("tmux")
	return err == nil
}

func TestCreateSession(t *testing.T) {
	if !tmuxAvailable() {
		t.Skip("tmux not available")
	}

	// Create temp directory for capture
	tmpDir, err := os.MkdirTemp("", "gforge-tmux-test-*")
	if err != nil {
		t.Fatalf("Failed to create temp dir: %v", err)
	}
	defer os.RemoveAll(tmpDir)

	mgr := NewManager(Config{
		SocketName: "gforge-test-create",
		CaptureDir: tmpDir,
	})

	// Create session
	session, err := mgr.Create("test-session", tmpDir)
	if err != nil {
		t.Fatalf("Failed to create session: %v", err)
	}
	defer mgr.Kill("test-session")

	if session.Name != "test-session" {
		t.Errorf("Expected name 'test-session', got '%s'", session.Name)
	}

	if session.Status != StatusCreated {
		t.Errorf("Expected status 'created', got '%s'", session.Status)
	}

	// Verify session exists
	if !mgr.sessionExists("test-session") {
		t.Error("Session should exist in tmux")
	}
}

func TestCreateDuplicateSession(t *testing.T) {
	if !tmuxAvailable() {
		t.Skip("tmux not available")
	}

	tmpDir, _ := os.MkdirTemp("", "gforge-tmux-test-*")
	defer os.RemoveAll(tmpDir)

	mgr := NewManager(Config{
		SocketName: "gforge-test-dup",
		CaptureDir: tmpDir,
	})

	// Create first session
	_, err := mgr.Create("dup-session", tmpDir)
	if err != nil {
		t.Fatalf("Failed to create first session: %v", err)
	}
	defer mgr.Kill("dup-session")

	// Try to create duplicate
	_, err = mgr.Create("dup-session", tmpDir)
	if err == nil {
		t.Error("Should fail when creating duplicate session")
	}
}

func TestKillSession(t *testing.T) {
	if !tmuxAvailable() {
		t.Skip("tmux not available")
	}

	tmpDir, _ := os.MkdirTemp("", "gforge-tmux-test-*")
	defer os.RemoveAll(tmpDir)

	mgr := NewManager(Config{
		SocketName: "gforge-test-kill",
		CaptureDir: tmpDir,
	})

	// Create and kill session
	_, err := mgr.Create("kill-test", tmpDir)
	if err != nil {
		t.Fatalf("Failed to create session: %v", err)
	}

	err = mgr.Kill("kill-test")
	if err != nil {
		t.Fatalf("Failed to kill session: %v", err)
	}

	// Verify session is gone
	if mgr.sessionExists("kill-test") {
		t.Error("Session should not exist after kill")
	}
}

func TestSendKeys(t *testing.T) {
	if !tmuxAvailable() {
		t.Skip("tmux not available")
	}

	tmpDir, _ := os.MkdirTemp("", "gforge-tmux-test-*")
	defer os.RemoveAll(tmpDir)

	mgr := NewManager(Config{
		SocketName: "gforge-test-keys",
		CaptureDir: tmpDir,
	})

	// Create session
	_, err := mgr.Create("keys-test", tmpDir)
	if err != nil {
		t.Fatalf("Failed to create session: %v", err)
	}
	defer mgr.Kill("keys-test")

	// Send keys
	err = mgr.SendKeys("keys-test", "echo hello", "Enter")
	if err != nil {
		t.Fatalf("Failed to send keys: %v", err)
	}
}

func TestSendCommand(t *testing.T) {
	if !tmuxAvailable() {
		t.Skip("tmux not available")
	}

	tmpDir, _ := os.MkdirTemp("", "gforge-tmux-test-*")
	defer os.RemoveAll(tmpDir)

	mgr := NewManager(Config{
		SocketName: "gforge-test-cmd",
		CaptureDir: tmpDir,
	})

	// Create session
	_, err := mgr.Create("cmd-test", tmpDir)
	if err != nil {
		t.Fatalf("Failed to create session: %v", err)
	}
	defer mgr.Kill("cmd-test")

	// Send command
	err = mgr.SendCommand("cmd-test", "pwd")
	if err != nil {
		t.Fatalf("Failed to send command: %v", err)
	}
}

func TestListSessions(t *testing.T) {
	if !tmuxAvailable() {
		t.Skip("tmux not available")
	}

	tmpDir, _ := os.MkdirTemp("", "gforge-tmux-test-*")
	defer os.RemoveAll(tmpDir)

	mgr := NewManager(Config{
		SocketName: "gforge-test-list",
		CaptureDir: tmpDir,
	})

	// Create sessions
	_, err := mgr.Create("list-test-1", tmpDir)
	if err != nil {
		t.Fatalf("Failed to create session 1: %v", err)
	}
	defer mgr.Kill("list-test-1")

	_, err = mgr.Create("list-test-2", tmpDir)
	if err != nil {
		t.Fatalf("Failed to create session 2: %v", err)
	}
	defer mgr.Kill("list-test-2")

	// List sessions
	sessions := mgr.List()
	if len(sessions) < 2 {
		t.Errorf("Expected at least 2 sessions, got %d", len(sessions))
	}
}

func TestCapturePane(t *testing.T) {
	if !tmuxAvailable() {
		t.Skip("tmux not available")
	}

	tmpDir, _ := os.MkdirTemp("", "gforge-tmux-test-*")
	defer os.RemoveAll(tmpDir)

	mgr := NewManager(Config{
		SocketName: "gforge-test-capture",
		CaptureDir: tmpDir,
	})

	// Create session
	_, err := mgr.Create("capture-test", tmpDir)
	if err != nil {
		t.Fatalf("Failed to create session: %v", err)
	}
	defer mgr.Kill("capture-test")

	// Capture pane
	output, err := mgr.CapturePane("capture-test", 100)
	if err != nil {
		t.Fatalf("Failed to capture pane: %v", err)
	}

	// Output might be empty for a fresh session, that's okay
	_ = output
}

func TestGetSession(t *testing.T) {
	if !tmuxAvailable() {
		t.Skip("tmux not available")
	}

	tmpDir, _ := os.MkdirTemp("", "gforge-tmux-test-*")
	defer os.RemoveAll(tmpDir)

	mgr := NewManager(Config{
		SocketName: "gforge-test-get",
		CaptureDir: tmpDir,
	})

	// Create session
	created, err := mgr.Create("get-test", tmpDir)
	if err != nil {
		t.Fatalf("Failed to create session: %v", err)
	}
	defer mgr.Kill("get-test")

	// Get session
	session := mgr.Get("get-test")
	if session == nil {
		t.Fatal("Session should be found")
	}

	if session.ID != created.ID {
		t.Errorf("Session ID mismatch")
	}
}

func TestGetNonexistentSession(t *testing.T) {
	mgr := NewManager(Config{
		SocketName: "gforge-test-noexist",
	})

	session := mgr.Get("nonexistent")
	if session != nil {
		t.Error("Should return nil for nonexistent session")
	}
}

func TestCaptureDirectory(t *testing.T) {
	tmpDir, _ := os.MkdirTemp("", "gforge-tmux-test-*")
	defer os.RemoveAll(tmpDir)

	captureDir := filepath.Join(tmpDir, "captures")

	mgr := NewManager(Config{
		SocketName: "gforge-test-capdir",
		CaptureDir: captureDir,
	})

	// Capture directory should be created
	if _, err := os.Stat(captureDir); os.IsNotExist(err) {
		t.Error("Capture directory should be created")
	}

	_ = mgr
}
