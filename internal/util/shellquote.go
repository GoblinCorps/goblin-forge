package util

import (
	"strings"
	"unicode"
)

// shellSafeChars are characters that don't need quoting in shell
const shellSafeChars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-./:=@"

// isShellSafe checks if a rune is safe to use unquoted in shell
func isShellSafe(r rune) bool {
	return strings.ContainsRune(shellSafeChars, r)
}

// ShellQuote quotes a string for safe use in shell commands.
// Equivalent to Python's shlex.quote().
//
// Examples:
//
//	ShellQuote("")           -> "''"
//	ShellQuote("hello")      -> "hello"
//	ShellQuote("hello world") -> "'hello world'"
//	ShellQuote("it's")       -> "'it'\"'\"'s'"
//	ShellQuote("$PATH")      -> "'$PATH'"
func ShellQuote(s string) string {
	// Empty string needs explicit empty quotes
	if s == "" {
		return "''"
	}

	// Check if quoting is needed
	safe := true
	for _, r := range s {
		if !isShellSafe(r) {
			safe = false
			break
		}
	}
	if safe {
		return s
	}

	// Use single quotes, escape any existing single quotes
	// The pattern 'text'"'"'more' handles single quotes by:
	// 1. Ending the single-quoted section
	// 2. Adding an escaped single quote in double quotes
	// 3. Starting a new single-quoted section
	return "'" + strings.ReplaceAll(s, "'", "'\"'\"'") + "'"
}

// ShellJoin joins command parts with proper quoting for shell execution.
// Equivalent to Python's shlex.join().
func ShellJoin(parts []string) string {
	quoted := make([]string, len(parts))
	for i, p := range parts {
		quoted[i] = ShellQuote(p)
	}
	return strings.Join(quoted, " ")
}

// ContainsShellSpecial checks if a string contains shell-special characters
func ContainsShellSpecial(s string) bool {
	for _, r := range s {
		if !isShellSafe(r) && !unicode.IsSpace(r) {
			return true
		}
	}
	return false
}
