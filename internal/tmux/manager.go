package tmux

import (
	"bufio"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"sync"
	"time"
)

// Manager handles tmux session lifecycle
type Manager struct {
	socketName  string
	socketPath  string
	sessions    map[string]*Session
	mu          sync.RWMutex
	captureDir  string
}

// Session represents a tmux session
type Session struct {
	ID          string
	Name        string
	WindowID    string
	PaneID      string
	WorkingDir  string
	Status      SessionStatus
	CreatedAt   time.Time
	AttachedAt  *time.Time
	capturePath string
	sendMu      sync.Mutex // Protects send operations to prevent interleaved input
}

// SendOptions configures send behavior
type SendOptions struct {
	PostDelay time.Duration // Delay after sending (0 = auto-calculate for text)
	NoDelay   bool          // Skip delay entirely (for key presses)
}

// DefaultTextDelay is the base delay after sending text
const DefaultTextDelay = 50 * time.Millisecond

// calculatePostDelay determines appropriate delay based on content length
func calculatePostDelay(textLen int) time.Duration {
	// Base delay + 1ms per 100 characters for large content
	return DefaultTextDelay + time.Duration(textLen/100)*time.Millisecond
}

// SessionStatus represents the state of a session
type SessionStatus string

const (
	StatusCreated  SessionStatus = "created"
	StatusRunning  SessionStatus = "running"
	StatusAttached SessionStatus = "attached"
	StatusDetached SessionStatus = "detached"
	StatusDead     SessionStatus = "dead"
)

// Config holds tmux manager configuration
type Config struct {
	SocketName   string
	CaptureDir   string
	HistoryLimit int
	DefaultShell string
}

// NewManager creates a new tmux manager
func NewManager(cfg Config) *Manager {
	if cfg.SocketName == "" {
		cfg.SocketName = "gforge"
	}
	if cfg.CaptureDir == "" {
		cfg.CaptureDir = filepath.Join(os.TempDir(), "gforge", "captures")
	}
	if cfg.HistoryLimit == 0 {
		cfg.HistoryLimit = 50000
	}

	// Ensure capture directory exists
	os.MkdirAll(cfg.CaptureDir, 0755)

	// Determine socket path
	socketPath := ""
	if tmpDir := os.Getenv("TMUX_TMPDIR"); tmpDir != "" {
		socketPath = filepath.Join(tmpDir, cfg.SocketName)
	} else if tmpDir := os.Getenv("TMPDIR"); tmpDir != "" {
		socketPath = filepath.Join(tmpDir, fmt.Sprintf("tmux-%d", os.Getuid()), cfg.SocketName)
	}

	return &Manager{
		socketName: cfg.SocketName,
		socketPath: socketPath,
		sessions:   make(map[string]*Session),
		captureDir: cfg.CaptureDir,
	}
}

// Create creates a new tmux session
func (m *Manager) Create(name, workingDir string) (*Session, error) {
	m.mu.Lock()
	defer m.mu.Unlock()

	// Check if session already exists
	if _, exists := m.sessions[name]; exists {
		return nil, fmt.Errorf("session '%s' already exists", name)
	}

	// Check if tmux session exists externally
	if m.sessionExists(name) {
		return nil, fmt.Errorf("tmux session '%s' already exists", name)
	}

	// Ensure working directory exists
	if workingDir != "" {
		if _, err := os.Stat(workingDir); os.IsNotExist(err) {
			return nil, fmt.Errorf("working directory does not exist: %s", workingDir)
		}
	}

	// Create tmux session
	args := []string{
		"-L", m.socketName,
		"new-session",
		"-d",           // Detached
		"-s", name,     // Session name
		"-x", "200",    // Width
		"-y", "50",     // Height
	}

	if workingDir != "" {
		args = append(args, "-c", workingDir)
	}

	cmd := exec.Command("tmux", args...)
	output, err := cmd.CombinedOutput()
	if err != nil {
		return nil, fmt.Errorf("failed to create tmux session: %w\nOutput: %s", err, string(output))
	}

	// Get window and pane IDs
	windowID, paneID := m.getSessionInfo(name)

	// Setup capture file for output
	capturePath := filepath.Join(m.captureDir, fmt.Sprintf("%s.log", name))

	session := &Session{
		ID:          name,
		Name:        name,
		WindowID:    windowID,
		PaneID:      paneID,
		WorkingDir:  workingDir,
		Status:      StatusCreated,
		CreatedAt:   time.Now(),
		capturePath: capturePath,
	}

	// Start output capture
	if err := m.startCapture(session); err != nil {
		// Non-fatal, just log
		fmt.Fprintf(os.Stderr, "Warning: failed to start capture: %v\n", err)
	}

	m.sessions[name] = session
	return session, nil
}

// sessionExists checks if a tmux session exists
func (m *Manager) sessionExists(name string) bool {
	cmd := exec.Command("tmux", "-L", m.socketName, "has-session", "-t", name)
	return cmd.Run() == nil
}

// getSessionInfo retrieves window and pane IDs for a session
func (m *Manager) getSessionInfo(name string) (windowID, paneID string) {
	cmd := exec.Command("tmux", "-L", m.socketName,
		"list-panes", "-t", name, "-F", "#{window_id}:#{pane_id}")
	output, err := cmd.Output()
	if err != nil {
		return "", ""
	}

	parts := strings.Split(strings.TrimSpace(string(output)), ":")
	if len(parts) == 2 {
		return parts[0], parts[1]
	}
	return "", ""
}

// startCapture starts capturing output from a session
func (m *Manager) startCapture(session *Session) error {
	// Create capture file
	f, err := os.Create(session.capturePath)
	if err != nil {
		return err
	}
	f.Close()

	// Use pipe-pane to capture output
	cmd := exec.Command("tmux", "-L", m.socketName,
		"pipe-pane", "-t", session.Name,
		fmt.Sprintf("cat >> %s", session.capturePath))

	return cmd.Run()
}

// stopCapture stops capturing output
func (m *Manager) stopCapture(session *Session) error {
	cmd := exec.Command("tmux", "-L", m.socketName,
		"pipe-pane", "-t", session.Name)
	return cmd.Run()
}

// Attach attaches to a session (replaces current process)
func (m *Manager) Attach(name string) error {
	m.mu.RLock()
	session, exists := m.sessions[name]
	m.mu.RUnlock()

	if !exists {
		// Check if it exists in tmux but not tracked
		if !m.sessionExists(name) {
			return fmt.Errorf("session '%s' not found", name)
		}
	} else {
		now := time.Now()
		session.AttachedAt = &now
		session.Status = StatusAttached
	}

	// Attach to tmux session (replaces current process)
	tmuxPath, err := exec.LookPath("tmux")
	if err != nil {
		return fmt.Errorf("tmux not found: %w", err)
	}

	args := []string{"tmux", "-L", m.socketName, "attach-session", "-t", name}

	// Use syscall.Exec to replace current process
	env := os.Environ()
	return execCommand(tmuxPath, args, env)
}

// execCommand is a wrapper that can be mocked in tests
var execCommand = func(path string, args []string, env []string) error {
	cmd := exec.Command(path, args[1:]...)
	cmd.Stdin = os.Stdin
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	cmd.Env = env
	return cmd.Run()
}

// escapeTmuxContent escapes content for safe transmission via tmux send-keys.
// Order matters: backslashes must be escaped first to avoid double-escaping.
func escapeTmuxContent(s string) string {
	s = strings.ReplaceAll(s, "\\", "\\\\")
	s = strings.ReplaceAll(s, "\n", "\\n")
	return s
}

// SendText sends literal text to a session using tmux's -l (literal) flag.
// The text is escaped for safe transmission. Use SendKey for special keys.
// Includes automatic post-send delay based on content length.
func (m *Manager) SendText(name, text string) error {
	return m.SendTextWithOptions(name, text, SendOptions{})
}

// SendTextWithOptions sends literal text with configurable options.
func (m *Manager) SendTextWithOptions(name, text string, opts SendOptions) error {
	session := m.Get(name)
	if session == nil {
		return fmt.Errorf("session '%s' not found", name)
	}

	// Acquire per-session lock to prevent interleaved sends
	session.sendMu.Lock()
	defer session.sendMu.Unlock()

	escaped := escapeTmuxContent(text)
	args := []string{"-L", m.socketName, "send-keys", "-t", name, "-l", escaped}

	cmd := exec.Command("tmux", args...)
	output, err := cmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("failed to send text: %w\nOutput: %s", err, string(output))
	}

	// Apply post-send delay unless explicitly disabled
	if !opts.NoDelay {
		delay := opts.PostDelay
		if delay == 0 {
			delay = calculatePostDelay(len(text))
		}
		time.Sleep(delay)
	}

	return nil
}

// SendKey sends a special key (Enter, C-c, Escape, etc.) to a session.
// Does NOT use -l flag, so tmux interprets the key name.
// No delay is applied since key presses are instantaneous.
func (m *Manager) SendKey(name, key string) error {
	session := m.Get(name)
	if session == nil {
		return fmt.Errorf("session '%s' not found", name)
	}

	// Acquire per-session lock to prevent interleaved sends
	session.sendMu.Lock()
	defer session.sendMu.Unlock()

	args := []string{"-L", m.socketName, "send-keys", "-t", name, key}

	cmd := exec.Command("tmux", args...)
	output, err := cmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("failed to send key: %w\nOutput: %s", err, string(output))
	}

	return nil
}

// SendKeys sends keystrokes to a session.
// Deprecated: Use SendText for literal text or SendKey for special keys.
// This method exists for backward compatibility and does not escape content.
func (m *Manager) SendKeys(name string, keys ...string) error {
	session := m.Get(name)
	if session == nil {
		return fmt.Errorf("session '%s' not found", name)
	}

	// Acquire per-session lock to prevent interleaved sends
	session.sendMu.Lock()
	defer session.sendMu.Unlock()

	args := []string{"-L", m.socketName, "send-keys", "-t", name}
	args = append(args, keys...)

	cmd := exec.Command("tmux", args...)
	output, err := cmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("failed to send keys: %w\nOutput: %s", err, string(output))
	}

	return nil
}

// SendCommand sends a command (with Enter key) to a session.
// Text is sent literally, then Enter is sent as a separate key.
func (m *Manager) SendCommand(name, command string) error {
	// Send text literally
	if err := m.SendText(name, command); err != nil {
		return err
	}
	// Send Enter as special key (no -l flag)
	return m.SendKey(name, "Enter")
}

// Kill terminates a session
func (m *Manager) Kill(name string) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	session, exists := m.sessions[name]
	if exists {
		// Stop capture
		m.stopCapture(session)
		// Remove from tracking
		delete(m.sessions, name)
	}

	// Kill tmux session
	cmd := exec.Command("tmux", "-L", m.socketName, "kill-session", "-t", name)
	output, err := cmd.CombinedOutput()
	if err != nil {
		// Session might already be dead
		if !strings.Contains(string(output), "no such session") {
			return fmt.Errorf("failed to kill session: %w\nOutput: %s", err, string(output))
		}
	}

	return nil
}

// List returns all tracked sessions
func (m *Manager) List() []*Session {
	m.mu.RLock()
	defer m.mu.RUnlock()

	sessions := make([]*Session, 0, len(m.sessions))
	for _, s := range m.sessions {
		// Update status
		if m.sessionExists(s.Name) {
			if s.Status == StatusDead {
				s.Status = StatusRunning
			}
		} else {
			s.Status = StatusDead
		}
		sessions = append(sessions, s)
	}

	return sessions
}

// Get retrieves a session by name
func (m *Manager) Get(name string) *Session {
	m.mu.RLock()
	defer m.mu.RUnlock()
	return m.sessions[name]
}

// ListTmuxSessions lists all tmux sessions (including untracked)
func (m *Manager) ListTmuxSessions() ([]string, error) {
	cmd := exec.Command("tmux", "-L", m.socketName, "list-sessions", "-F", "#{session_name}")
	output, err := cmd.Output()
	if err != nil {
		// No sessions might exist
		return []string{}, nil
	}

	var sessions []string
	scanner := bufio.NewScanner(strings.NewReader(string(output)))
	for scanner.Scan() {
		name := strings.TrimSpace(scanner.Text())
		if name != "" {
			sessions = append(sessions, name)
		}
	}

	return sessions, nil
}

// CapturePane captures the current pane content
func (m *Manager) CapturePane(name string, lines int) (string, error) {
	if lines == 0 {
		lines = 1000
	}

	cmd := exec.Command("tmux", "-L", m.socketName,
		"capture-pane", "-t", name, "-p", "-S", fmt.Sprintf("-%d", lines))

	output, err := cmd.Output()
	if err != nil {
		return "", fmt.Errorf("failed to capture pane: %w", err)
	}

	return string(output), nil
}

// GetOutput reads captured output from a session
func (m *Manager) GetOutput(name string, lines int) ([]string, error) {
	m.mu.RLock()
	session, exists := m.sessions[name]
	m.mu.RUnlock()

	if !exists {
		return nil, fmt.Errorf("session '%s' not found", name)
	}

	if session.capturePath == "" {
		return nil, fmt.Errorf("no capture file for session '%s'", name)
	}

	// Read capture file
	f, err := os.Open(session.capturePath)
	if err != nil {
		return nil, err
	}
	defer f.Close()

	var allLines []string
	scanner := bufio.NewScanner(f)
	for scanner.Scan() {
		allLines = append(allLines, scanner.Text())
	}

	// Return last N lines
	if lines > 0 && len(allLines) > lines {
		return allLines[len(allLines)-lines:], nil
	}

	return allLines, nil
}

// Resize resizes a session
func (m *Manager) Resize(name string, width, height int) error {
	cmd := exec.Command("tmux", "-L", m.socketName,
		"resize-window", "-t", name, "-x", fmt.Sprintf("%d", width), "-y", fmt.Sprintf("%d", height))

	output, err := cmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("failed to resize: %w\nOutput: %s", err, string(output))
	}

	return nil
}

// SetEnvironment sets an environment variable in a session
func (m *Manager) SetEnvironment(name, key, value string) error {
	cmd := exec.Command("tmux", "-L", m.socketName,
		"set-environment", "-t", name, key, value)

	return cmd.Run()
}

// IsServerRunning checks if the tmux server is running
func (m *Manager) IsServerRunning() bool {
	cmd := exec.Command("tmux", "-L", m.socketName, "list-sessions")
	return cmd.Run() == nil
}

// StartServer starts the tmux server if not running
func (m *Manager) StartServer() error {
	if m.IsServerRunning() {
		return nil
	}

	cmd := exec.Command("tmux", "-L", m.socketName, "start-server")
	return cmd.Run()
}

// KillServer kills the tmux server and all sessions
func (m *Manager) KillServer() error {
	m.mu.Lock()
	defer m.mu.Unlock()

	// Clear tracked sessions
	m.sessions = make(map[string]*Session)

	cmd := exec.Command("tmux", "-L", m.socketName, "kill-server")
	cmd.Run() // Ignore errors - server might not be running

	return nil
}

// Sync synchronizes tracked sessions with actual tmux sessions
func (m *Manager) Sync() error {
	m.mu.Lock()
	defer m.mu.Unlock()

	// Get actual tmux sessions
	tmuxSessions, err := m.ListTmuxSessions()
	if err != nil {
		return err
	}

	tmuxSet := make(map[string]bool)
	for _, name := range tmuxSessions {
		tmuxSet[name] = true
	}

	// Mark dead sessions
	for name, session := range m.sessions {
		if !tmuxSet[name] {
			session.Status = StatusDead
		}
	}

	// Add untracked sessions
	for _, name := range tmuxSessions {
		if _, exists := m.sessions[name]; !exists {
			// This is an untracked session, add it
			windowID, paneID := m.getSessionInfo(name)
			m.sessions[name] = &Session{
				ID:         name,
				Name:       name,
				WindowID:   windowID,
				PaneID:     paneID,
				Status:     StatusRunning,
				CreatedAt:  time.Now(), // Unknown, use now
			}
		}
	}

	return nil
}
