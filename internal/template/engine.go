package template

import (
	"embed"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"text/template"

	"gopkg.in/yaml.v3"
)

//go:embed builtin/*.yaml
var builtinTemplates embed.FS

// Engine manages project templates and auto-detection
type Engine struct {
	builtin  map[string]*Template
	custom   map[string]*Template
	detector *Detector
}

// Template represents a project template configuration
type Template struct {
	Name         string            `yaml:"name"`
	Description  string            `yaml:"description"`
	Category     string            `yaml:"category"`
	Extends      string            `yaml:"extends"`
	Detect       DetectionRules    `yaml:"detect"`
	Variables    map[string]string `yaml:"variables"`
	Setup        []SetupStep       `yaml:"setup"`
	Commands     map[string]string `yaml:"commands"`
	Ports        []int             `yaml:"ports"`
	AgentContext string            `yaml:"agent_context"`
	Priority     int               `yaml:"priority"`
}

// DetectionRules defines how to auto-detect this template type
type DetectionRules struct {
	Files   []string       `yaml:"files"`
	Content []ContentMatch `yaml:"content"`
}

// ContentMatch defines a content-based detection rule
type ContentMatch struct {
	File    string `yaml:"file"`
	Pattern string `yaml:"pattern"`
}

// SetupStep defines a setup command to run
type SetupStep struct {
	Name    string `yaml:"name"`
	Command string `yaml:"command"`
	OnFail  string `yaml:"on_fail"` // "skip", "error", "warn"
}

// New creates a new template engine
func New() (*Engine, error) {
	e := &Engine{
		builtin:  make(map[string]*Template),
		custom:   make(map[string]*Template),
		detector: NewDetector(),
	}

	if err := e.loadBuiltinTemplates(); err != nil {
		return nil, fmt.Errorf("failed to load builtin templates: %w", err)
	}

	return e, nil
}

// loadBuiltinTemplates loads templates from embedded filesystem
func (e *Engine) loadBuiltinTemplates() error {
	entries, err := builtinTemplates.ReadDir("builtin")
	if err != nil {
		// If no embedded templates, load from disk (development mode)
		return e.loadTemplatesFromDisk()
	}

	for _, entry := range entries {
		if entry.IsDir() || !strings.HasSuffix(entry.Name(), ".yaml") {
			continue
		}

		data, err := builtinTemplates.ReadFile("builtin/" + entry.Name())
		if err != nil {
			return fmt.Errorf("failed to read template %s: %w", entry.Name(), err)
		}

		var tmpl Template
		if err := yaml.Unmarshal(data, &tmpl); err != nil {
			return fmt.Errorf("failed to parse template %s: %w", entry.Name(), err)
		}

		name := strings.TrimSuffix(entry.Name(), ".yaml")
		tmpl.Name = name
		e.builtin[name] = &tmpl
	}

	return nil
}

// loadTemplatesFromDisk loads templates from the templates directory
func (e *Engine) loadTemplatesFromDisk() error {
	templatesDir := "templates/builtin"

	// Walk through all subdirectories
	return filepath.Walk(templatesDir, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return nil // Skip errors
		}

		if info.IsDir() || !strings.HasSuffix(path, ".yaml") {
			return nil
		}

		data, err := os.ReadFile(path)
		if err != nil {
			return nil // Skip files we can't read
		}

		var tmpl Template
		if err := yaml.Unmarshal(data, &tmpl); err != nil {
			return nil // Skip invalid templates
		}

		// Extract name from path
		name := strings.TrimSuffix(filepath.Base(path), ".yaml")
		if tmpl.Name == "" {
			tmpl.Name = name
		}

		// Set category from directory
		dir := filepath.Dir(path)
		category := filepath.Base(dir)
		if tmpl.Category == "" && category != "builtin" {
			tmpl.Category = category
		}

		e.builtin[tmpl.Name] = &tmpl
		return nil
	})
}

// LoadCustomTemplates loads user-defined templates from a directory
func (e *Engine) LoadCustomTemplates(dir string) error {
	entries, err := os.ReadDir(dir)
	if err != nil {
		if os.IsNotExist(err) {
			return nil // No custom templates directory
		}
		return err
	}

	for _, entry := range entries {
		if entry.IsDir() || !strings.HasSuffix(entry.Name(), ".yaml") {
			continue
		}

		path := filepath.Join(dir, entry.Name())
		data, err := os.ReadFile(path)
		if err != nil {
			continue
		}

		var tmpl Template
		if err := yaml.Unmarshal(data, &tmpl); err != nil {
			continue
		}

		name := strings.TrimSuffix(entry.Name(), ".yaml")
		if tmpl.Name == "" {
			tmpl.Name = name
		}
		e.custom[name] = &tmpl
	}

	return nil
}

// Detect auto-detects the project type from a directory
func (e *Engine) Detect(projectPath string) (*Template, error) {
	var bestMatch *Template
	var bestPriority int = -1

	// Check custom templates first
	for _, tmpl := range e.custom {
		if e.matchesDetection(projectPath, tmpl.Detect) {
			if tmpl.Priority > bestPriority {
				bestMatch = tmpl
				bestPriority = tmpl.Priority
			}
		}
	}

	// Then check builtin templates
	for _, tmpl := range e.builtin {
		if e.matchesDetection(projectPath, tmpl.Detect) {
			if tmpl.Priority > bestPriority {
				bestMatch = tmpl
				bestPriority = tmpl.Priority
			}
		}
	}

	if bestMatch == nil {
		return nil, ErrNoTemplateMatch
	}

	return bestMatch, nil
}

// matchesDetection checks if a project matches detection rules
func (e *Engine) matchesDetection(projectPath string, rules DetectionRules) bool {
	// Check for marker files
	for _, file := range rules.Files {
		path := filepath.Join(projectPath, file)
		if _, err := os.Stat(path); err == nil {
			return true
		}
	}

	// Check for content matches
	for _, match := range rules.Content {
		path := filepath.Join(projectPath, match.File)
		data, err := os.ReadFile(path)
		if err != nil {
			continue
		}
		if strings.Contains(string(data), match.Pattern) {
			return true
		}
	}

	return false
}

// Get retrieves a template by name
func (e *Engine) Get(name string) (*Template, error) {
	// Check custom first
	if tmpl, ok := e.custom[name]; ok {
		return tmpl, nil
	}
	// Then builtin
	if tmpl, ok := e.builtin[name]; ok {
		return tmpl, nil
	}
	return nil, fmt.Errorf("template not found: %s", name)
}

// List returns all available templates
func (e *Engine) List() []*Template {
	result := make([]*Template, 0, len(e.builtin)+len(e.custom))
	for _, tmpl := range e.builtin {
		result = append(result, tmpl)
	}
	for _, tmpl := range e.custom {
		result = append(result, tmpl)
	}
	return result
}

// ListByCategory returns templates filtered by category
func (e *Engine) ListByCategory(category string) []*Template {
	result := make([]*Template, 0)
	for _, tmpl := range e.List() {
		if tmpl.Category == category {
			result = append(result, tmpl)
		}
	}
	return result
}

// Categories returns all available categories
func (e *Engine) Categories() []string {
	seen := make(map[string]bool)
	for _, tmpl := range e.List() {
		if tmpl.Category != "" {
			seen[tmpl.Category] = true
		}
	}

	result := make([]string, 0, len(seen))
	for cat := range seen {
		result = append(result, cat)
	}
	return result
}

// Resolve resolves template inheritance and returns the final template
func (e *Engine) Resolve(tmpl *Template) (*Template, error) {
	if tmpl.Extends == "" {
		return tmpl, nil
	}

	parent, err := e.Get(tmpl.Extends)
	if err != nil {
		return nil, fmt.Errorf("parent template not found: %s", tmpl.Extends)
	}

	// Resolve parent first (recursive)
	parent, err = e.Resolve(parent)
	if err != nil {
		return nil, err
	}

	// Merge child over parent
	return e.mergeTemplates(parent, tmpl), nil
}

// mergeTemplates merges child template over parent
func (e *Engine) mergeTemplates(parent, child *Template) *Template {
	merged := &Template{
		Name:         child.Name,
		Description:  child.Description,
		Category:     child.Category,
		Extends:      "", // Already resolved
		Priority:     child.Priority,
		AgentContext: child.AgentContext,
	}

	// Merge detection rules
	merged.Detect.Files = append(parent.Detect.Files, child.Detect.Files...)
	merged.Detect.Content = append(parent.Detect.Content, child.Detect.Content...)

	// Merge variables (child overrides parent)
	merged.Variables = make(map[string]string)
	for k, v := range parent.Variables {
		merged.Variables[k] = v
	}
	for k, v := range child.Variables {
		merged.Variables[k] = v
	}

	// Merge setup steps (parent first, then child)
	merged.Setup = append(parent.Setup, child.Setup...)

	// Merge commands (child overrides parent)
	merged.Commands = make(map[string]string)
	for k, v := range parent.Commands {
		merged.Commands[k] = v
	}
	for k, v := range child.Commands {
		merged.Commands[k] = v
	}

	// Merge ports
	merged.Ports = append(parent.Ports, child.Ports...)

	// Override description and agent context if provided
	if merged.Description == "" {
		merged.Description = parent.Description
	}
	if merged.AgentContext == "" {
		merged.AgentContext = parent.AgentContext
	}

	return merged
}

// ResolveVariables substitutes variables in a command string
func (e *Engine) ResolveVariables(cmd string, vars map[string]string) (string, error) {
	tmpl, err := template.New("cmd").Parse(cmd)
	if err != nil {
		return "", err
	}

	var buf strings.Builder
	if err := tmpl.Execute(&buf, vars); err != nil {
		return "", err
	}

	return buf.String(), nil
}

// ErrNoTemplateMatch is returned when no template matches a project
var ErrNoTemplateMatch = fmt.Errorf("no template matches this project")
