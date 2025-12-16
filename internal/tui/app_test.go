package tui

import (
	"testing"
	"time"

	"github.com/astoreyai/goblin-forge/internal/coordinator"
	tea "github.com/charmbracelet/bubbletea"
)

func TestNew(t *testing.T) {
	app := New(nil)
	if app == nil {
		t.Fatal("App should not be nil")
	}

	if app.activeView != ViewDashboard {
		t.Error("Initial view should be dashboard")
	}

	if app.selectedIndex != 0 {
		t.Error("Initial selected index should be 0")
	}
}

func TestInit(t *testing.T) {
	app := New(nil)
	cmd := app.Init()

	if cmd == nil {
		t.Error("Init should return a command")
	}
}

func TestUpdateWindowSize(t *testing.T) {
	app := New(nil)
	app.width = 0
	app.height = 0

	msg := tea.WindowSizeMsg{Width: 100, Height: 40}
	newApp, _ := app.Update(msg)

	updated := newApp.(*App)
	if updated.width != 100 {
		t.Errorf("Expected width 100, got %d", updated.width)
	}
	if updated.height != 40 {
		t.Errorf("Expected height 40, got %d", updated.height)
	}
}

func TestUpdateTickMsg(t *testing.T) {
	app := New(nil)
	oldTime := app.lastUpdate

	time.Sleep(10 * time.Millisecond)

	msg := tickMsg(time.Now())
	newApp, cmd := app.Update(msg)

	updated := newApp.(*App)
	if !updated.lastUpdate.After(oldTime) {
		t.Error("Last update time should be updated")
	}

	if cmd == nil {
		t.Error("Tick should return a command for next tick")
	}
}

func TestUpdateGoblinListMsg(t *testing.T) {
	app := New(nil)

	goblins := []*coordinator.Goblin{
		{ID: "1", Name: "test1", Agent: "claude", Status: "running"},
		{ID: "2", Name: "test2", Agent: "codex", Status: "stopped"},
	}

	msg := goblinListMsg{goblins: goblins}
	newApp, _ := app.Update(msg)

	updated := newApp.(*App)
	if len(updated.goblins) != 2 {
		t.Errorf("Expected 2 goblins, got %d", len(updated.goblins))
	}
}

func TestUpdateGoblinListMsgBoundsCheck(t *testing.T) {
	app := New(nil)
	app.selectedIndex = 5 // Out of bounds

	goblins := []*coordinator.Goblin{
		{ID: "1", Name: "test1"},
	}

	msg := goblinListMsg{goblins: goblins}
	newApp, _ := app.Update(msg)

	updated := newApp.(*App)
	if updated.selectedIndex != 0 {
		t.Errorf("Selected index should be bounded to 0, got %d", updated.selectedIndex)
	}
}

func TestKeyQuit(t *testing.T) {
	app := New(nil)

	msg := tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'q'}}
	_, cmd := app.Update(msg)

	// Check if quit command was returned
	if cmd == nil {
		t.Error("Quit key should return a command")
	}
}

func TestKeyHelp(t *testing.T) {
	app := New(nil)
	app.activeView = ViewDashboard

	msg := tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'?'}}
	newApp, _ := app.Update(msg)

	updated := newApp.(*App)
	if updated.activeView != ViewHelp {
		t.Error("? should switch to help view")
	}
}

func TestKeyExitHelp(t *testing.T) {
	app := New(nil)
	app.activeView = ViewHelp

	msg := tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'x'}}
	newApp, _ := app.Update(msg)

	updated := newApp.(*App)
	if updated.activeView != ViewDashboard {
		t.Error("Any key should exit help view")
	}
}

func TestKeyNavigation(t *testing.T) {
	app := New(nil)
	app.goblins = []*coordinator.Goblin{
		{ID: "1", Name: "test1"},
		{ID: "2", Name: "test2"},
		{ID: "3", Name: "test3"},
	}
	app.selectedIndex = 0

	// Test down
	msg := tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'j'}}
	newApp, _ := app.Update(msg)
	updated := newApp.(*App)
	if updated.selectedIndex != 1 {
		t.Errorf("j should move selection down, got %d", updated.selectedIndex)
	}

	// Test wrap around
	updated.selectedIndex = 2
	newApp, _ = updated.Update(msg)
	updated = newApp.(*App)
	if updated.selectedIndex != 0 {
		t.Errorf("j at end should wrap to 0, got %d", updated.selectedIndex)
	}

	// Test up
	msg = tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'k'}}
	updated.selectedIndex = 0
	newApp, _ = updated.Update(msg)
	updated = newApp.(*App)
	if updated.selectedIndex != 2 {
		t.Errorf("k at 0 should wrap to end, got %d", updated.selectedIndex)
	}
}

func TestKeyNavigationEmpty(t *testing.T) {
	app := New(nil)
	app.goblins = []*coordinator.Goblin{}
	app.selectedIndex = 0

	msg := tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'j'}}
	newApp, _ := app.Update(msg)

	updated := newApp.(*App)
	if updated.selectedIndex != 0 {
		t.Error("Navigation on empty list should not change index")
	}
}

func TestViewLoading(t *testing.T) {
	app := New(nil)
	app.width = 0

	view := app.View()
	if view != "Loading..." {
		t.Error("View should show loading when width is 0")
	}
}

func TestViewDashboard(t *testing.T) {
	app := New(nil)
	app.width = 100
	app.height = 40

	view := app.View()
	if view == "" {
		t.Error("Dashboard view should not be empty")
	}

	if len(view) == 0 {
		t.Error("Dashboard view should have content")
	}
}

func TestViewHelp(t *testing.T) {
	app := New(nil)
	app.width = 100
	app.height = 40
	app.activeView = ViewHelp

	view := app.View()
	if view == "" {
		t.Error("Help view should not be empty")
	}

	// Should contain keybinding info
	if len(view) == 0 {
		t.Error("Help view should have content")
	}
}

func TestRenderHeader(t *testing.T) {
	app := New(nil)
	app.width = 80

	header := app.renderHeader()
	if header == "" {
		t.Error("Header should not be empty")
	}
}

func TestRenderGoblinList(t *testing.T) {
	app := New(nil)
	app.goblins = []*coordinator.Goblin{
		{ID: "1", Name: "coder", Agent: "claude", Status: "running", CreatedAt: time.Now()},
	}
	app.selectedIndex = 0

	list := app.renderGoblinList(40, 20)
	if list == "" {
		t.Error("Goblin list should not be empty")
	}
}

func TestRenderGoblinListEmpty(t *testing.T) {
	app := New(nil)
	app.goblins = []*coordinator.Goblin{}

	list := app.renderGoblinList(40, 20)
	if list == "" {
		t.Error("Empty goblin list should still render")
	}
}

func TestRenderOutputPanel(t *testing.T) {
	app := New(nil)
	app.output = []string{"line 1", "line 2"}

	panel := app.renderOutputPanel(60, 20)
	if panel == "" {
		t.Error("Output panel should not be empty")
	}
}

func TestRenderFooter(t *testing.T) {
	app := New(nil)
	app.width = 80

	footer := app.renderFooter()
	if footer == "" {
		t.Error("Footer should not be empty")
	}
}

func TestTruncate(t *testing.T) {
	tests := []struct {
		input    string
		maxLen   int
		expected string
	}{
		{"hello", 10, "hello"},
		{"hello world", 8, "hello..."},
		{"hi", 2, "hi"},
		{"abc", 3, "abc"},
		{"abcd", 3, "abc"},
	}

	for _, tc := range tests {
		result := truncate(tc.input, tc.maxLen)
		if result != tc.expected {
			t.Errorf("truncate(%q, %d) = %q, expected %q", tc.input, tc.maxLen, result, tc.expected)
		}
	}
}

func TestMax(t *testing.T) {
	tests := []struct {
		a, b     int
		expected int
	}{
		{1, 2, 2},
		{5, 3, 5},
		{0, 0, 0},
		{-1, 1, 1},
	}

	for _, tc := range tests {
		result := max(tc.a, tc.b)
		if result != tc.expected {
			t.Errorf("max(%d, %d) = %d, expected %d", tc.a, tc.b, result, tc.expected)
		}
	}
}

func TestErrMsg(t *testing.T) {
	app := New(nil)

	testErr := errMsg{err: nil}
	newApp, _ := app.Update(testErr)

	updated := newApp.(*App)
	if updated.err != nil {
		t.Error("Nil error should be handled")
	}
}
