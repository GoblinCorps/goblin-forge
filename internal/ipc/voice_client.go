package ipc

import (
	"encoding/json"
	"fmt"
	"net"
	"os"
	"os/exec"
	"path/filepath"
	"sync"
	"time"
)

const (
	DefaultSocketPath = "/tmp/gforge-voice.sock"
	connectTimeout    = 5 * time.Second
	readTimeout       = 100 * time.Millisecond
)

// VoiceCommand represents a parsed voice command
type VoiceCommand struct {
	Action      string `json:"action"`
	Name        string `json:"name,omitempty"`
	Agent       string `json:"agent,omitempty"`
	Task        string `json:"task,omitempty"`
	Message     string `json:"message,omitempty"`
	Description string `json:"description,omitempty"`
	Raw         string `json:"raw,omitempty"`
}

// VoiceStatus represents the voice daemon status
type VoiceStatus struct {
	Status    string `json:"status"`
	Recording bool   `json:"recording"`
	Model     string `json:"model"`
}

// VoiceClient manages communication with the voice daemon
type VoiceClient struct {
	socketPath string
	conn       net.Conn
	handlers   []func(VoiceCommand)
	mu         sync.Mutex
	connected  bool
	stopCh     chan struct{}
}

// NewVoiceClient creates a new voice client
func NewVoiceClient(socketPath string) *VoiceClient {
	if socketPath == "" {
		socketPath = DefaultSocketPath
	}
	return &VoiceClient{
		socketPath: socketPath,
		handlers:   make([]func(VoiceCommand), 0),
		stopCh:     make(chan struct{}),
	}
}

// Connect connects to the voice daemon
func (c *VoiceClient) Connect() error {
	c.mu.Lock()
	defer c.mu.Unlock()

	if c.connected {
		return nil
	}

	// Check if socket exists
	if _, err := os.Stat(c.socketPath); os.IsNotExist(err) {
		return fmt.Errorf("voice daemon not running (socket not found)")
	}

	conn, err := net.DialTimeout("unix", c.socketPath, connectTimeout)
	if err != nil {
		return fmt.Errorf("failed to connect to voice daemon: %w", err)
	}

	c.conn = conn
	c.connected = true

	return nil
}

// Disconnect disconnects from the voice daemon
func (c *VoiceClient) Disconnect() {
	c.mu.Lock()
	defer c.mu.Unlock()

	if c.conn != nil {
		c.conn.Close()
		c.conn = nil
	}
	c.connected = false

	// Signal stop
	select {
	case <-c.stopCh:
	default:
		close(c.stopCh)
	}
}

// IsConnected returns whether the client is connected
func (c *VoiceClient) IsConnected() bool {
	c.mu.Lock()
	defer c.mu.Unlock()
	return c.connected
}

// OnCommand registers a handler for incoming commands
func (c *VoiceClient) OnCommand(handler func(VoiceCommand)) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.handlers = append(c.handlers, handler)
}

// Listen starts listening for commands from the voice daemon
func (c *VoiceClient) Listen() error {
	if !c.IsConnected() {
		if err := c.Connect(); err != nil {
			return err
		}
	}

	decoder := json.NewDecoder(c.conn)

	for {
		select {
		case <-c.stopCh:
			return nil
		default:
			// Set read deadline for non-blocking check
			c.conn.SetReadDeadline(time.Now().Add(readTimeout))

			var cmd VoiceCommand
			if err := decoder.Decode(&cmd); err != nil {
				if netErr, ok := err.(net.Error); ok && netErr.Timeout() {
					continue // Timeout, check stopCh and try again
				}
				return fmt.Errorf("failed to read command: %w", err)
			}

			// Dispatch to handlers
			c.mu.Lock()
			handlers := make([]func(VoiceCommand), len(c.handlers))
			copy(handlers, c.handlers)
			c.mu.Unlock()

			for _, handler := range handlers {
				go handler(cmd)
			}
		}
	}
}

// GetStatus gets the voice daemon status
func (c *VoiceClient) GetStatus() (*VoiceStatus, error) {
	if !c.IsConnected() {
		if err := c.Connect(); err != nil {
			return nil, err
		}
	}

	// Send status request
	req := map[string]string{"action": "status"}
	data, err := json.Marshal(req)
	if err != nil {
		return nil, err
	}

	if _, err := c.conn.Write(data); err != nil {
		return nil, fmt.Errorf("failed to send status request: %w", err)
	}

	// Read response
	c.conn.SetReadDeadline(time.Now().Add(5 * time.Second))
	var status VoiceStatus
	if err := json.NewDecoder(c.conn).Decode(&status); err != nil {
		return nil, fmt.Errorf("failed to read status: %w", err)
	}

	return &status, nil
}

// StartRecording triggers recording start
func (c *VoiceClient) StartRecording() error {
	return c.sendControl("start_recording")
}

// StopRecording triggers recording stop
func (c *VoiceClient) StopRecording() error {
	return c.sendControl("stop_recording")
}

func (c *VoiceClient) sendControl(action string) error {
	if !c.IsConnected() {
		if err := c.Connect(); err != nil {
			return err
		}
	}

	req := map[string]string{"action": action}
	data, err := json.Marshal(req)
	if err != nil {
		return err
	}

	if _, err := c.conn.Write(data); err != nil {
		return fmt.Errorf("failed to send control: %w", err)
	}

	return nil
}

// IsDaemonRunning checks if the voice daemon is running
func IsDaemonRunning() bool {
	_, err := os.Stat(DefaultSocketPath)
	return err == nil
}

// StartDaemon starts the voice daemon process
func StartDaemon(modelSize, device string) error {
	// Find the daemon script
	daemonPath := findDaemonPath()
	if daemonPath == "" {
		return fmt.Errorf("voice daemon not found")
	}

	args := []string{daemonPath}
	if modelSize != "" {
		args = append(args, "--model", modelSize)
	}
	if device != "" {
		args = append(args, "--device", device)
	}

	cmd := exec.Command("python3", args...)
	cmd.Stdout = nil // Daemon runs in background
	cmd.Stderr = nil

	if err := cmd.Start(); err != nil {
		return fmt.Errorf("failed to start voice daemon: %w", err)
	}

	// Wait for socket to be created
	for i := 0; i < 50; i++ {
		if _, err := os.Stat(DefaultSocketPath); err == nil {
			return nil
		}
		time.Sleep(100 * time.Millisecond)
	}

	return fmt.Errorf("voice daemon did not start (timeout)")
}

// StopDaemon stops the voice daemon
func StopDaemon() error {
	client := NewVoiceClient("")
	if err := client.Connect(); err != nil {
		return nil // Already stopped
	}
	defer client.Disconnect()

	// Send exit command
	req := map[string]string{"action": "exit_voice"}
	data, _ := json.Marshal(req)
	client.conn.Write(data)

	return nil
}

func findDaemonPath() string {
	// Check common locations
	locations := []string{
		"voice/daemon.py",
		"./voice/daemon.py",
		filepath.Join(os.Getenv("HOME"), ".local/share/gforge/voice/daemon.py"),
		"/usr/local/share/gforge/voice/daemon.py",
	}

	// Also check relative to executable
	if exe, err := os.Executable(); err == nil {
		exeDir := filepath.Dir(exe)
		locations = append(locations,
			filepath.Join(exeDir, "voice/daemon.py"),
			filepath.Join(exeDir, "../voice/daemon.py"),
		)
	}

	for _, path := range locations {
		if _, err := os.Stat(path); err == nil {
			return path
		}
	}

	return ""
}
