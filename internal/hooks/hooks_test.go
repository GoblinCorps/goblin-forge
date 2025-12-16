package hooks

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"testing"
	"time"
)

func TestNewWatcher(t *testing.T) {
	t.Run("requires session ID", func(t *testing.T) {
		_, err := NewWatcher(Config{})
		if err == nil {
			t.Error("expected error for empty session ID")
		}
	})

	t.Run("creates hooks directory", func(t *testing.T) {
		tmpDir := t.TempDir()
		cfg := Config{
			SessionID: "test-session",
			HooksDir:  tmpDir,
		}

		w, err := NewWatcher(cfg)
		if err != nil {
			t.Fatalf("NewWatcher failed: %v", err)
		}
		defer w.Cleanup()

		expectedDir := filepath.Join(tmpDir, "test-session")
		if _, err := os.Stat(expectedDir); os.IsNotExist(err) {
			t.Errorf("hooks directory not created: %s", expectedDir)
		}

		if w.HooksDir() != expectedDir {
			t.Errorf("HooksDir() = %q, want %q", w.HooksDir(), expectedDir)
		}
	})

	t.Run("uses default hooks dir", func(t *testing.T) {
		cfg := Config{
			SessionID: "default-test-" + time.Now().Format("20060102150405"),
		}

		w, err := NewWatcher(cfg)
		if err != nil {
			t.Fatalf("NewWatcher failed: %v", err)
		}
		defer w.Cleanup()

		expectedBase := filepath.Join(os.TempDir(), "gforge", "hooks")
		if !filepath.HasPrefix(w.HooksDir(), expectedBase) {
			t.Errorf("HooksDir() = %q, want prefix %q", w.HooksDir(), expectedBase)
		}
	})
}

func TestWatcherStartStop(t *testing.T) {
	tmpDir := t.TempDir()
	w, err := NewWatcher(Config{
		SessionID: "start-stop-test",
		HooksDir:  tmpDir,
	})
	if err != nil {
		t.Fatalf("NewWatcher failed: %v", err)
	}
	defer w.Cleanup()

	// Start should succeed
	if err := w.Start(); err != nil {
		t.Errorf("Start failed: %v", err)
	}

	// Double start should fail
	if err := w.Start(); err == nil {
		t.Error("expected error on double Start")
	}

	// Stop should succeed
	w.Stop()

	// Double stop should be safe
	w.Stop()
}

func TestEventHandling(t *testing.T) {
	tmpDir := t.TempDir()
	w, err := NewWatcher(Config{
		SessionID: "event-test",
		HooksDir:  tmpDir,
	})
	if err != nil {
		t.Fatalf("NewWatcher failed: %v", err)
	}
	defer w.Cleanup()

	// Track received events
	var mu sync.Mutex
	received := make([]Event, 0)

	w.OnEvent(func(e Event) {
		mu.Lock()
		received = append(received, e)
		mu.Unlock()
	})

	if err := w.Start(); err != nil {
		t.Fatalf("Start failed: %v", err)
	}
	defer w.Stop()

	// Write test events
	testEvents := []Event{
		{Type: EventSessionStart, Data: map[string]interface{}{"agent": "claude"}},
		{Type: EventPromptSubmit, Data: map[string]interface{}{"prompt": "hello"}},
		{Type: EventToolComplete, Data: map[string]interface{}{"tool": "read", "exit_code": 0}},
	}

	for _, e := range testEvents {
		if err := WriteEvent(w.HooksDir(), e); err != nil {
			t.Fatalf("WriteEvent failed: %v", err)
		}
	}

	// Wait for events to be processed
	time.Sleep(300 * time.Millisecond)

	mu.Lock()
	defer mu.Unlock()

	if len(received) != len(testEvents) {
		t.Errorf("received %d events, want %d", len(received), len(testEvents))
	}

	// Verify event types
	for i, e := range received {
		if e.Type != testEvents[i].Type {
			t.Errorf("event %d: Type = %q, want %q", i, e.Type, testEvents[i].Type)
		}
		if e.SessionID != "event-test" {
			t.Errorf("event %d: SessionID = %q, want %q", i, e.SessionID, "event-test")
		}
	}
}

func TestWriteEvent(t *testing.T) {
	tmpDir := t.TempDir()

	event := Event{
		Type:      EventToolComplete,
		SessionID: "write-test",
		Data: map[string]interface{}{
			"tool":      "bash",
			"exit_code": 0,
		},
	}

	if err := WriteEvent(tmpDir, event); err != nil {
		t.Fatalf("WriteEvent failed: %v", err)
	}

	// Find the written file
	entries, err := os.ReadDir(tmpDir)
	if err != nil {
		t.Fatalf("ReadDir failed: %v", err)
	}

	if len(entries) != 1 {
		t.Fatalf("expected 1 file, got %d", len(entries))
	}

	// Read and verify
	data, err := os.ReadFile(filepath.Join(tmpDir, entries[0].Name()))
	if err != nil {
		t.Fatalf("ReadFile failed: %v", err)
	}

	var readEvent Event
	if err := json.Unmarshal(data, &readEvent); err != nil {
		t.Fatalf("Unmarshal failed: %v", err)
	}

	if readEvent.Type != EventToolComplete {
		t.Errorf("Type = %q, want %q", readEvent.Type, EventToolComplete)
	}
	if readEvent.SessionID != "write-test" {
		t.Errorf("SessionID = %q, want %q", readEvent.SessionID, "write-test")
	}
	if readEvent.Timestamp.IsZero() {
		t.Error("Timestamp should be set")
	}
}

func TestMultipleHandlers(t *testing.T) {
	tmpDir := t.TempDir()
	w, err := NewWatcher(Config{
		SessionID: "multi-handler-test",
		HooksDir:  tmpDir,
	})
	if err != nil {
		t.Fatalf("NewWatcher failed: %v", err)
	}
	defer w.Cleanup()

	var count1, count2 int
	var mu sync.Mutex

	w.OnEvent(func(e Event) {
		mu.Lock()
		count1++
		mu.Unlock()
	})

	w.OnEvent(func(e Event) {
		mu.Lock()
		count2++
		mu.Unlock()
	})

	if err := w.Start(); err != nil {
		t.Fatalf("Start failed: %v", err)
	}
	defer w.Stop()

	WriteEvent(w.HooksDir(), Event{Type: EventHeartbeat})
	time.Sleep(200 * time.Millisecond)

	mu.Lock()
	defer mu.Unlock()

	if count1 != 1 || count2 != 1 {
		t.Errorf("handlers called %d and %d times, want 1 and 1", count1, count2)
	}
}

func TestIgnoresNonJSONFiles(t *testing.T) {
	tmpDir := t.TempDir()
	w, err := NewWatcher(Config{
		SessionID: "json-filter-test",
		HooksDir:  tmpDir,
	})
	if err != nil {
		t.Fatalf("NewWatcher failed: %v", err)
	}
	defer w.Cleanup()

	var received int
	var mu sync.Mutex

	w.OnEvent(func(e Event) {
		mu.Lock()
		received++
		mu.Unlock()
	})

	if err := w.Start(); err != nil {
		t.Fatalf("Start failed: %v", err)
	}
	defer w.Stop()

	// Write a non-JSON file
	os.WriteFile(filepath.Join(w.HooksDir(), "readme.txt"), []byte("ignore me"), 0644)

	// Write a valid JSON event
	WriteEvent(w.HooksDir(), Event{Type: EventSessionStart})

	time.Sleep(200 * time.Millisecond)

	mu.Lock()
	defer mu.Unlock()

	if received != 1 {
		t.Errorf("received %d events, want 1", received)
	}
}

func TestIgnoresInvalidJSON(t *testing.T) {
	tmpDir := t.TempDir()
	w, err := NewWatcher(Config{
		SessionID: "invalid-json-test",
		HooksDir:  tmpDir,
	})
	if err != nil {
		t.Fatalf("NewWatcher failed: %v", err)
	}
	defer w.Cleanup()

	var received int
	var mu sync.Mutex

	w.OnEvent(func(e Event) {
		mu.Lock()
		received++
		mu.Unlock()
	})

	if err := w.Start(); err != nil {
		t.Fatalf("Start failed: %v", err)
	}
	defer w.Stop()

	// Write invalid JSON
	os.WriteFile(filepath.Join(w.HooksDir(), "bad.json"), []byte("not json{"), 0644)

	// Write a valid event
	WriteEvent(w.HooksDir(), Event{Type: EventSessionStop})

	time.Sleep(200 * time.Millisecond)

	mu.Lock()
	defer mu.Unlock()

	if received != 1 {
		t.Errorf("received %d events, want 1 (should ignore invalid JSON)", received)
	}
}

func TestCleanup(t *testing.T) {
	tmpDir := t.TempDir()
	w, err := NewWatcher(Config{
		SessionID: "cleanup-test",
		HooksDir:  tmpDir,
	})
	if err != nil {
		t.Fatalf("NewWatcher failed: %v", err)
	}

	hooksDir := w.HooksDir()

	// Verify directory exists
	if _, err := os.Stat(hooksDir); os.IsNotExist(err) {
		t.Fatal("hooks directory should exist before cleanup")
	}

	// Cleanup
	if err := w.Cleanup(); err != nil {
		t.Errorf("Cleanup failed: %v", err)
	}

	// Verify directory is removed
	if _, err := os.Stat(hooksDir); !os.IsNotExist(err) {
		t.Error("hooks directory should be removed after cleanup")
	}
}

func TestGenerateClaudeCodeConfig(t *testing.T) {
	cfg := GenerateClaudeCodeConfig("/tmp/gforge/hooks/abc123", "abc123")

	// Verify all hooks are present
	expectedHooks := []string{"SessionStart", "UserPromptSubmit", "ToolUse", "ToolComplete", "Stop"}
	for _, hook := range expectedHooks {
		if _, ok := cfg.Hooks[hook]; !ok {
			t.Errorf("missing hook: %s", hook)
		}
	}

	// Verify command contains session ID and hooks dir
	sessionStartCmd := cfg.Hooks["SessionStart"][0].Command
	if !strings.Contains(sessionStartCmd, "abc123") {
		t.Errorf("SessionStart command missing session ID: %s", sessionStartCmd)
	}
	if !strings.Contains(sessionStartCmd, "/tmp/gforge/hooks/abc123") {
		t.Errorf("SessionStart command missing hooks dir: %s", sessionStartCmd)
	}
}

func TestWriteClaudeCodeConfig(t *testing.T) {
	tmpDir := t.TempDir()
	configPath := filepath.Join(tmpDir, ".claude", "hooks.json")

	cfg := GenerateClaudeCodeConfig("/tmp/test", "test-session")

	if err := WriteClaudeCodeConfig(configPath, cfg); err != nil {
		t.Fatalf("WriteClaudeCodeConfig failed: %v", err)
	}

	// Verify file exists
	if _, err := os.Stat(configPath); os.IsNotExist(err) {
		t.Fatal("config file not created")
	}

	// Verify content is valid JSON
	data, err := os.ReadFile(configPath)
	if err != nil {
		t.Fatalf("ReadFile failed: %v", err)
	}

	var readCfg ClaudeCodeConfig
	if err := json.Unmarshal(data, &readCfg); err != nil {
		t.Fatalf("Unmarshal failed: %v", err)
	}

	if len(readCfg.Hooks) != 5 {
		t.Errorf("expected 5 hooks, got %d", len(readCfg.Hooks))
	}
}

func TestSetupClaudeCodeHooks(t *testing.T) {
	tmpDir := t.TempDir()
	workdir := filepath.Join(tmpDir, "project")
	os.MkdirAll(workdir, 0755)

	configPath, watcher, err := SetupClaudeCodeHooks("setup-test", workdir, Config{
		SessionID: "setup-test",
		HooksDir:  filepath.Join(tmpDir, "hooks"),
	})
	if err != nil {
		t.Fatalf("SetupClaudeCodeHooks failed: %v", err)
	}
	defer watcher.Cleanup()

	// Verify config path
	expectedPath := filepath.Join(workdir, ".claude", "hooks.json")
	if configPath != expectedPath {
		t.Errorf("configPath = %q, want %q", configPath, expectedPath)
	}

	// Verify config file exists
	if _, err := os.Stat(configPath); os.IsNotExist(err) {
		t.Error("config file not created")
	}

	// Verify hooks directory exists
	if _, err := os.Stat(watcher.HooksDir()); os.IsNotExist(err) {
		t.Error("hooks directory not created")
	}
}
