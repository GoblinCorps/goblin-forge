package tmux

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"sync"
	"testing"
	"time"
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

func TestEscapeTmuxContent(t *testing.T) {
	tests := []struct {
		name     string
		input    string
		expected string
	}{
		{
			name:     "no escaping needed",
			input:    "hello world",
			expected: "hello world",
		},
		{
			name:     "newline escaping",
			input:    "line1\nline2",
			expected: "line1\\nline2",
		},
		{
			name:     "backslash escaping",
			input:    "path\\to\\file",
			expected: "path\\\\to\\\\file",
		},
		{
			name:     "mixed escaping",
			input:    "path\\to\\file\nmore",
			expected: "path\\\\to\\\\file\\nmore",
		},
		{
			name:     "regex pattern",
			input:    `\d+\.\d+`,
			expected: `\\d+\\.\\d+`,
		},
		{
			name:     "empty string",
			input:    "",
			expected: "",
		},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			result := escapeTmuxContent(tc.input)
			if result != tc.expected {
				t.Errorf("escapeTmuxContent(%q) = %q, want %q", tc.input, result, tc.expected)
			}
		})
	}
}

func TestSendText(t *testing.T) {
	if !tmuxAvailable() {
		t.Skip("tmux not available")
	}

	tmpDir, _ := os.MkdirTemp("", "gforge-tmux-test-*")
	defer os.RemoveAll(tmpDir)

	mgr := NewManager(Config{
		SocketName: "gforge-test-sendtext",
		CaptureDir: tmpDir,
	})

	// Create session
	_, err := mgr.Create("sendtext-test", tmpDir)
	if err != nil {
		t.Fatalf("Failed to create session: %v", err)
	}
	defer mgr.Kill("sendtext-test")

	// Send literal text including special key names
	// Without -l flag, "Enter" would be interpreted as a key press
	err = mgr.SendText("sendtext-test", "This text contains Enter and C-c literally")
	if err != nil {
		t.Fatalf("Failed to send text: %v", err)
	}
}

func TestSendKey(t *testing.T) {
	if !tmuxAvailable() {
		t.Skip("tmux not available")
	}

	tmpDir, _ := os.MkdirTemp("", "gforge-tmux-test-*")
	defer os.RemoveAll(tmpDir)

	mgr := NewManager(Config{
		SocketName: "gforge-test-sendkey",
		CaptureDir: tmpDir,
	})

	// Create session
	_, err := mgr.Create("sendkey-test", tmpDir)
	if err != nil {
		t.Fatalf("Failed to create session: %v", err)
	}
	defer mgr.Kill("sendkey-test")

	// Send special keys
	err = mgr.SendKey("sendkey-test", "Enter")
	if err != nil {
		t.Fatalf("Failed to send Enter key: %v", err)
	}

	err = mgr.SendKey("sendkey-test", "C-c")
	if err != nil {
		t.Fatalf("Failed to send C-c key: %v", err)
	}
}

func TestSendTextNonexistentSession(t *testing.T) {
	mgr := NewManager(Config{
		SocketName: "gforge-test-noexist-text",
	})

	err := mgr.SendText("nonexistent", "hello")
	if err == nil {
		t.Error("Should fail for nonexistent session")
	}
}

func TestSendKeyNonexistentSession(t *testing.T) {
	mgr := NewManager(Config{
		SocketName: "gforge-test-noexist-key",
	})

	err := mgr.SendKey("nonexistent", "Enter")
	if err == nil {
		t.Error("Should fail for nonexistent session")
	}
}

func TestCalculatePostDelay(t *testing.T) {
	tests := []struct {
		name     string
		textLen  int
		expected time.Duration
	}{
		{
			name:     "empty string",
			textLen:  0,
			expected: DefaultTextDelay, // 50ms
		},
		{
			name:     "short text",
			textLen:  50,
			expected: DefaultTextDelay, // 50ms (50/100 = 0)
		},
		{
			name:     "100 chars",
			textLen:  100,
			expected: DefaultTextDelay + 1*time.Millisecond, // 51ms
		},
		{
			name:     "1000 chars",
			textLen:  1000,
			expected: DefaultTextDelay + 10*time.Millisecond, // 60ms
		},
		{
			name:     "10000 chars (large paste)",
			textLen:  10000,
			expected: DefaultTextDelay + 100*time.Millisecond, // 150ms
		},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			result := calculatePostDelay(tc.textLen)
			if result != tc.expected {
				t.Errorf("calculatePostDelay(%d) = %v, want %v", tc.textLen, result, tc.expected)
			}
		})
	}
}

func TestSendTextWithOptions(t *testing.T) {
	if !tmuxAvailable() {
		t.Skip("tmux not available")
	}

	tmpDir, _ := os.MkdirTemp("", "gforge-tmux-test-*")
	defer os.RemoveAll(tmpDir)

	mgr := NewManager(Config{
		SocketName: "gforge-test-sendopts",
		CaptureDir: tmpDir,
	})

	// Create session
	_, err := mgr.Create("sendopts-test", tmpDir)
	if err != nil {
		t.Fatalf("Failed to create session: %v", err)
	}
	defer mgr.Kill("sendopts-test")

	// Test with NoDelay option (should be fast)
	start := time.Now()
	err = mgr.SendTextWithOptions("sendopts-test", "hello", SendOptions{NoDelay: true})
	if err != nil {
		t.Fatalf("Failed to send text: %v", err)
	}
	elapsed := time.Since(start)

	// With NoDelay, should take less than 40ms (just tmux overhead)
	if elapsed > 40*time.Millisecond {
		t.Errorf("NoDelay took %v, expected < 40ms", elapsed)
	}

	// Test with default delay (should wait ~50ms)
	start = time.Now()
	err = mgr.SendTextWithOptions("sendopts-test", "hello", SendOptions{})
	if err != nil {
		t.Fatalf("Failed to send text: %v", err)
	}
	elapsed = time.Since(start)

	// With default delay, should take at least 50ms
	if elapsed < DefaultTextDelay {
		t.Errorf("Default delay took %v, expected >= %v", elapsed, DefaultTextDelay)
	}
}

func TestConcurrentSendsSameSession(t *testing.T) {
	if !tmuxAvailable() {
		t.Skip("tmux not available")
	}

	tmpDir, _ := os.MkdirTemp("", "gforge-tmux-test-*")
	defer os.RemoveAll(tmpDir)

	mgr := NewManager(Config{
		SocketName: "gforge-test-concurrent",
		CaptureDir: tmpDir,
	})

	// Create session
	_, err := mgr.Create("concurrent-test", tmpDir)
	if err != nil {
		t.Fatalf("Failed to create session: %v", err)
	}
	defer mgr.Kill("concurrent-test")

	// Send multiple texts concurrently
	// The mutex should prevent interleaved output
	var wg sync.WaitGroup
	errChan := make(chan error, 3)

	for i := 0; i < 3; i++ {
		wg.Add(1)
		go func(n int) {
			defer wg.Done()
			// Use NoDelay to speed up test
			err := mgr.SendTextWithOptions("concurrent-test", fmt.Sprintf("msg%d", n), SendOptions{NoDelay: true})
			if err != nil {
				errChan <- err
			}
		}(i)
	}

	wg.Wait()
	close(errChan)

	// Check for errors
	for err := range errChan {
		t.Errorf("Concurrent send failed: %v", err)
	}
}
