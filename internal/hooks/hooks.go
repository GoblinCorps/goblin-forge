// Package hooks provides structured event handling for agents that support hooks/callbacks.
//
// # Background
//
// The default output capture (pipe-pane) captures raw terminal output including escape
// sequences, which is difficult to parse for semantic meaning. For agents that support
// hooks (like Claude Code), we can get structured events instead.
//
// # Supported Agents
//
// | Agent       | Hooks Support | Notes                                    |
// |-------------|---------------|------------------------------------------|
// | Claude Code | Yes           | Uses ~/.claude/hooks/ JSON config        |
// | Crush       | Unknown       | May support MCP-based callbacks          |
// | Codex       | No            | No known hook mechanism                  |
// | Gemini      | No            | No known hook mechanism                  |
// | Ollama      | No            | No known hook mechanism                  |
//
// # Architecture
//
// For agents with hooks support, goblin-forge:
// 1. Creates a hooks directory per session: /tmp/gforge/hooks/<session-id>/
// 2. Writes a hooks config that calls notify-gforge
// 3. notify-gforge writes events to the hooks directory as JSON files
// 4. HooksWatcher monitors the directory and emits structured events
//
// # Claude Code Integration
//
// Claude Code hooks are configured via ~/.claude/hooks.json or .claude/hooks.json:
//
//	{
//	  "hooks": {
//	    "SessionStart": [{"command": "notify-gforge session-start"}],
//	    "UserPromptSubmit": [{"command": "notify-gforge prompt \"$PROMPT\""}],
//	    "ToolComplete": [{"command": "notify-gforge tool $TOOL_NAME $EXIT_CODE"}],
//	    "Stop": [{"command": "notify-gforge session-stop $EXIT_CODE"}]
//	  }
//	}
//
// # Event Types
//
// Events are structured JSON messages with a type field and event-specific data.
// See Event type and EventType constants for details.
package hooks

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sync"
	"time"
)

// EventType represents the type of hook event
type EventType string

const (
	// EventSessionStart fires when an agent session begins
	EventSessionStart EventType = "session_start"

	// EventSessionStop fires when an agent session ends
	EventSessionStop EventType = "session_stop"

	// EventPromptSubmit fires when a user prompt is submitted
	EventPromptSubmit EventType = "prompt_submit"

	// EventToolStart fires when a tool execution begins
	EventToolStart EventType = "tool_start"

	// EventToolComplete fires when a tool execution completes
	EventToolComplete EventType = "tool_complete"

	// EventError fires when an error occurs
	EventError EventType = "error"

	// EventHeartbeat fires periodically to indicate the agent is alive
	EventHeartbeat EventType = "heartbeat"
)

// Event represents a structured event from an agent
type Event struct {
	Type      EventType              `json:"type"`
	Timestamp time.Time              `json:"timestamp"`
	SessionID string                 `json:"session_id"`
	Data      map[string]interface{} `json:"data,omitempty"`
}

// Handler is called when an event is received
type Handler func(event Event)

// Watcher monitors a hooks directory for events
type Watcher struct {
	sessionID string
	hooksDir  string
	handlers  []Handler
	mu        sync.RWMutex
	stopCh    chan struct{}
	running   bool
}

// Config holds hooks watcher configuration
type Config struct {
	SessionID string
	HooksDir  string // Base directory for hooks (default: /tmp/gforge/hooks)
}

// NewWatcher creates a new hooks watcher for a session
func NewWatcher(cfg Config) (*Watcher, error) {
	if cfg.SessionID == "" {
		return nil, fmt.Errorf("session ID is required")
	}

	if cfg.HooksDir == "" {
		cfg.HooksDir = filepath.Join(os.TempDir(), "gforge", "hooks")
	}

	sessionDir := filepath.Join(cfg.HooksDir, cfg.SessionID)
	if err := os.MkdirAll(sessionDir, 0755); err != nil {
		return nil, fmt.Errorf("failed to create hooks directory: %w", err)
	}

	return &Watcher{
		sessionID: cfg.SessionID,
		hooksDir:  sessionDir,
		handlers:  make([]Handler, 0),
		stopCh:    make(chan struct{}),
	}, nil
}

// OnEvent registers a handler for all events
func (w *Watcher) OnEvent(handler Handler) {
	w.mu.Lock()
	defer w.mu.Unlock()
	w.handlers = append(w.handlers, handler)
}

// Start begins watching for events
func (w *Watcher) Start() error {
	w.mu.Lock()
	if w.running {
		w.mu.Unlock()
		return fmt.Errorf("watcher already running")
	}
	w.running = true
	w.mu.Unlock()

	go w.watchLoop()
	return nil
}

// Stop stops watching for events
func (w *Watcher) Stop() {
	w.mu.Lock()
	defer w.mu.Unlock()

	if !w.running {
		return
	}

	close(w.stopCh)
	w.running = false
}

// watchLoop polls the hooks directory for new event files
func (w *Watcher) watchLoop() {
	ticker := time.NewTicker(100 * time.Millisecond)
	defer ticker.Stop()

	processed := make(map[string]bool)

	for {
		select {
		case <-w.stopCh:
			return
		case <-ticker.C:
			w.processNewEvents(processed)
		}
	}
}

// processNewEvents reads and processes any new event files
func (w *Watcher) processNewEvents(processed map[string]bool) {
	entries, err := os.ReadDir(w.hooksDir)
	if err != nil {
		return
	}

	for _, entry := range entries {
		if entry.IsDir() {
			continue
		}

		name := entry.Name()
		if processed[name] {
			continue
		}

		// Only process .json files
		if filepath.Ext(name) != ".json" {
			continue
		}

		path := filepath.Join(w.hooksDir, name)
		event, err := w.readEvent(path)
		if err != nil {
			// Mark as processed even on error to avoid repeated attempts
			processed[name] = true
			continue
		}

		// Dispatch to handlers
		w.dispatchEvent(event)
		processed[name] = true

		// Optionally remove processed event files
		os.Remove(path)
	}
}

// readEvent reads an event from a JSON file
func (w *Watcher) readEvent(path string) (Event, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return Event{}, err
	}

	var event Event
	if err := json.Unmarshal(data, &event); err != nil {
		return Event{}, err
	}

	// Fill in session ID if not present
	if event.SessionID == "" {
		event.SessionID = w.sessionID
	}

	return event, nil
}

// dispatchEvent sends an event to all registered handlers
func (w *Watcher) dispatchEvent(event Event) {
	w.mu.RLock()
	handlers := make([]Handler, len(w.handlers))
	copy(handlers, w.handlers)
	w.mu.RUnlock()

	for _, handler := range handlers {
		handler(event)
	}
}

// HooksDir returns the directory where events are written
func (w *Watcher) HooksDir() string {
	return w.hooksDir
}

// Cleanup removes the hooks directory
func (w *Watcher) Cleanup() error {
	return os.RemoveAll(w.hooksDir)
}

// WriteEvent writes an event to the hooks directory (for testing or notify-gforge)
func WriteEvent(dir string, event Event) error {
	if event.Timestamp.IsZero() {
		event.Timestamp = time.Now()
	}

	data, err := json.Marshal(event)
	if err != nil {
		return err
	}

	filename := fmt.Sprintf("%d_%s.json", time.Now().UnixNano(), event.Type)
	path := filepath.Join(dir, filename)

	return os.WriteFile(path, data, 0644)
}

// ClaudeCodeConfig represents the Claude Code hooks.json format
type ClaudeCodeConfig struct {
	Hooks map[string][]ClaudeHookEntry `json:"hooks"`
}

// ClaudeHookEntry represents a single hook command
type ClaudeHookEntry struct {
	Command string `json:"command"`
}

// GenerateClaudeCodeConfig creates a hooks.json config for Claude Code
// that writes events to the specified hooks directory.
func GenerateClaudeCodeConfig(hooksDir, sessionID string) ClaudeCodeConfig {
	// Base command that writes events to our hooks directory
	baseCmd := fmt.Sprintf("gforge notify --session %s --hooks-dir %s", sessionID, hooksDir)

	return ClaudeCodeConfig{
		Hooks: map[string][]ClaudeHookEntry{
			"SessionStart": {
				{Command: baseCmd + " session-start"},
			},
			"UserPromptSubmit": {
				{Command: baseCmd + ` prompt "$PROMPT"`},
			},
			"ToolUse": {
				{Command: baseCmd + ` tool-start "$TOOL_NAME" "$TOOL_INPUT"`},
			},
			"ToolComplete": {
				{Command: baseCmd + " tool-complete $TOOL_NAME $EXIT_CODE"},
			},
			"Stop": {
				{Command: baseCmd + " session-stop $EXIT_CODE"},
			},
		},
	}
}

// WriteClaudeCodeConfig writes the Claude Code hooks config to a file
func WriteClaudeCodeConfig(path string, cfg ClaudeCodeConfig) error {
	data, err := json.MarshalIndent(cfg, "", "  ")
	if err != nil {
		return fmt.Errorf("failed to marshal config: %w", err)
	}

	// Ensure parent directory exists
	if err := os.MkdirAll(filepath.Dir(path), 0755); err != nil {
		return fmt.Errorf("failed to create config directory: %w", err)
	}

	return os.WriteFile(path, data, 0644)
}

// SetupClaudeCodeHooks creates the hooks directory and config for a Claude Code session.
// Returns the path to the generated hooks.json file.
func SetupClaudeCodeHooks(sessionID, workdir string, cfg Config) (string, *Watcher, error) {
	// Create the watcher (creates hooks directory)
	watcher, err := NewWatcher(cfg)
	if err != nil {
		return "", nil, err
	}

	// Generate Claude Code config
	hooksCfg := GenerateClaudeCodeConfig(watcher.HooksDir(), sessionID)

	// Write to workdir/.claude/hooks.json (project-level config)
	configPath := filepath.Join(workdir, ".claude", "hooks.json")
	if err := WriteClaudeCodeConfig(configPath, hooksCfg); err != nil {
		watcher.Cleanup()
		return "", nil, fmt.Errorf("failed to write hooks config: %w", err)
	}

	return configPath, watcher, nil
}
