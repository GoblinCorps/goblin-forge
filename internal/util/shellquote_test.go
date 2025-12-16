package util

import "testing"

func TestShellQuote(t *testing.T) {
	tests := []struct {
		name     string
		input    string
		expected string
	}{
		{
			name:     "empty string",
			input:    "",
			expected: "''",
		},
		{
			name:     "simple word",
			input:    "hello",
			expected: "hello",
		},
		{
			name:     "word with underscore",
			input:    "hello_world",
			expected: "hello_world",
		},
		{
			name:     "path",
			input:    "/usr/local/bin",
			expected: "/usr/local/bin",
		},
		{
			name:     "space in string",
			input:    "hello world",
			expected: "'hello world'",
		},
		{
			name:     "single quote",
			input:    "it's",
			expected: "'it'\"'\"'s'",
		},
		{
			name:     "double quotes",
			input:    `say "hello"`,
			expected: `'say "hello"'`,
		},
		{
			name:     "dollar sign",
			input:    "$PATH",
			expected: "'$PATH'",
		},
		{
			name:     "backticks",
			input:    "`whoami`",
			expected: "'`whoami`'",
		},
		{
			name:     "semicolon",
			input:    "cmd1; cmd2",
			expected: "'cmd1; cmd2'",
		},
		{
			name:     "pipe",
			input:    "ls | grep",
			expected: "'ls | grep'",
		},
		{
			name:     "ampersand",
			input:    "cmd &",
			expected: "'cmd &'",
		},
		{
			name:     "newline",
			input:    "line1\nline2",
			expected: "'line1\nline2'",
		},
		{
			name:     "tab",
			input:    "col1\tcol2",
			expected: "'col1\tcol2'",
		},
		{
			name:     "equals for env",
			input:    "KEY=value",
			expected: "KEY=value", // = is safe
		},
		{
			name:     "at sign",
			input:    "user@host",
			expected: "user@host", // @ is safe
		},
		{
			name:     "complex command injection attempt",
			input:    "$(rm -rf /)",
			expected: "'$(rm -rf /)'",
		},
		{
			name:     "glob patterns",
			input:    "*.txt",
			expected: "'*.txt'",
		},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			result := ShellQuote(tc.input)
			if result != tc.expected {
				t.Errorf("ShellQuote(%q) = %q, want %q", tc.input, result, tc.expected)
			}
		})
	}
}

func TestShellJoin(t *testing.T) {
	tests := []struct {
		name     string
		parts    []string
		expected string
	}{
		{
			name:     "simple command",
			parts:    []string{"echo", "hello"},
			expected: "echo hello",
		},
		{
			name:     "command with spaces",
			parts:    []string{"echo", "hello world"},
			expected: "echo 'hello world'",
		},
		{
			name:     "command with special chars",
			parts:    []string{"grep", "$USER", "/etc/passwd"},
			expected: "grep '$USER' /etc/passwd",
		},
		{
			name:     "claude with args",
			parts:    []string{"claude", "--dangerously-skip-permissions"},
			expected: "claude --dangerously-skip-permissions",
		},
		{
			name:     "ollama run",
			parts:    []string{"ollama", "run", "codellama"},
			expected: "ollama run codellama",
		},
		{
			name:     "empty parts",
			parts:    []string{"cmd", "", "arg"},
			expected: "cmd '' arg",
		},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			result := ShellJoin(tc.parts)
			if result != tc.expected {
				t.Errorf("ShellJoin(%v) = %q, want %q", tc.parts, result, tc.expected)
			}
		})
	}
}

func TestContainsShellSpecial(t *testing.T) {
	tests := []struct {
		input    string
		expected bool
	}{
		{"hello", false},
		{"/usr/bin/ls", false},
		{"hello world", false}, // spaces are not "special" in this context
		{"$PATH", true},
		{"`cmd`", true},
		{"cmd; rm", true},
		{"cmd | grep", true},
	}

	for _, tc := range tests {
		t.Run(tc.input, func(t *testing.T) {
			result := ContainsShellSpecial(tc.input)
			if result != tc.expected {
				t.Errorf("ContainsShellSpecial(%q) = %v, want %v", tc.input, result, tc.expected)
			}
		})
	}
}
