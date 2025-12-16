package ipc

import (
	"encoding/json"
	"net"
	"os"
	"path/filepath"
	"testing"
	"time"
)

func TestNewVoiceClient(t *testing.T) {
	client := NewVoiceClient("")
	if client.socketPath != DefaultSocketPath {
		t.Errorf("Expected default socket path, got %s", client.socketPath)
	}

	client = NewVoiceClient("/custom/path.sock")
	if client.socketPath != "/custom/path.sock" {
		t.Errorf("Expected custom socket path, got %s", client.socketPath)
	}
}

func TestConnectNoSocket(t *testing.T) {
	client := NewVoiceClient("/nonexistent/socket.sock")
	err := client.Connect()
	if err == nil {
		t.Error("Expected error when socket doesn't exist")
	}
}

func TestConnectAndDisconnect(t *testing.T) {
	// Create a mock server
	tmpDir := t.TempDir()
	socketPath := filepath.Join(tmpDir, "test.sock")

	listener, err := net.Listen("unix", socketPath)
	if err != nil {
		t.Fatalf("Failed to create listener: %v", err)
	}
	defer listener.Close()

	// Accept connections in background
	go func() {
		conn, _ := listener.Accept()
		if conn != nil {
			time.Sleep(100 * time.Millisecond)
			conn.Close()
		}
	}()

	client := NewVoiceClient(socketPath)

	// Connect
	err = client.Connect()
	if err != nil {
		t.Fatalf("Failed to connect: %v", err)
	}

	if !client.IsConnected() {
		t.Error("Expected client to be connected")
	}

	// Disconnect
	client.Disconnect()
	if client.IsConnected() {
		t.Error("Expected client to be disconnected")
	}
}

func TestVoiceCommand(t *testing.T) {
	cmd := VoiceCommand{
		Action: "spawn",
		Name:   "coder",
		Agent:  "claude",
	}

	data, err := json.Marshal(cmd)
	if err != nil {
		t.Fatalf("Failed to marshal: %v", err)
	}

	var parsed VoiceCommand
	if err := json.Unmarshal(data, &parsed); err != nil {
		t.Fatalf("Failed to unmarshal: %v", err)
	}

	if parsed.Action != "spawn" {
		t.Errorf("Expected action spawn, got %s", parsed.Action)
	}
	if parsed.Name != "coder" {
		t.Errorf("Expected name coder, got %s", parsed.Name)
	}
	if parsed.Agent != "claude" {
		t.Errorf("Expected agent claude, got %s", parsed.Agent)
	}
}

func TestOnCommand(t *testing.T) {
	client := NewVoiceClient("")

	received := false
	client.OnCommand(func(cmd VoiceCommand) {
		received = true
	})

	if len(client.handlers) != 1 {
		t.Errorf("Expected 1 handler, got %d", len(client.handlers))
	}
}

func TestIsDaemonRunning(t *testing.T) {
	// Should return false when no socket
	os.Remove(DefaultSocketPath)
	if IsDaemonRunning() {
		t.Error("Expected daemon not running")
	}
}

func TestFindDaemonPath(t *testing.T) {
	// Create a temp daemon script
	tmpDir := t.TempDir()
	voiceDir := filepath.Join(tmpDir, "voice")
	os.MkdirAll(voiceDir, 0755)

	daemonPath := filepath.Join(voiceDir, "daemon.py")
	os.WriteFile(daemonPath, []byte("# test"), 0644)

	// Change to temp dir
	oldWd, _ := os.Getwd()
	os.Chdir(tmpDir)
	defer os.Chdir(oldWd)

	path := findDaemonPath()
	if path == "" {
		t.Error("Expected to find daemon path")
	}
}

func TestVoiceStatus(t *testing.T) {
	status := VoiceStatus{
		Status:    "ok",
		Recording: true,
		Model:     "tiny",
	}

	data, err := json.Marshal(status)
	if err != nil {
		t.Fatalf("Failed to marshal: %v", err)
	}

	var parsed VoiceStatus
	if err := json.Unmarshal(data, &parsed); err != nil {
		t.Fatalf("Failed to unmarshal: %v", err)
	}

	if parsed.Status != "ok" {
		t.Errorf("Expected status ok, got %s", parsed.Status)
	}
	if !parsed.Recording {
		t.Error("Expected recording to be true")
	}
	if parsed.Model != "tiny" {
		t.Errorf("Expected model tiny, got %s", parsed.Model)
	}
}
