package template

import (
	"os"
	"path/filepath"
	"testing"
)

func TestNew(t *testing.T) {
	engine, err := New()
	if err != nil {
		t.Fatalf("Failed to create engine: %v", err)
	}
	if engine == nil {
		t.Fatal("Engine should not be nil")
	}
}

func TestLoadTemplatesFromDisk(t *testing.T) {
	engine := &Engine{
		builtin:  make(map[string]*Template),
		custom:   make(map[string]*Template),
		detector: NewDetector(),
	}

	// Should not error even if templates don't exist
	err := engine.loadTemplatesFromDisk()
	if err != nil {
		t.Errorf("Should not error on missing templates: %v", err)
	}
}

func TestDetection(t *testing.T) {
	// Create temp directory with project files
	tmpDir, err := os.MkdirTemp("", "template-test")
	if err != nil {
		t.Fatal(err)
	}
	defer os.RemoveAll(tmpDir)

	// Create package.json
	pkgJSON := `{
		"name": "test",
		"dependencies": {
			"next": "^14.0.0"
		}
	}`
	os.WriteFile(filepath.Join(tmpDir, "package.json"), []byte(pkgJSON), 0644)

	engine, _ := New()

	// Should detect nodejs at minimum
	templates := engine.detector.DetectAll(tmpDir)
	if len(templates) == 0 {
		t.Error("Should detect at least one template")
	}

	// Check that nextjs is detected (higher priority)
	found := false
	for _, name := range templates {
		if name == "nextjs" {
			found = true
			break
		}
	}
	if !found {
		t.Error("Should detect nextjs template")
	}
}

func TestDetectPython(t *testing.T) {
	tmpDir, err := os.MkdirTemp("", "python-test")
	if err != nil {
		t.Fatal(err)
	}
	defer os.RemoveAll(tmpDir)

	// Create pyproject.toml
	os.WriteFile(filepath.Join(tmpDir, "pyproject.toml"), []byte(`
[project]
name = "test"
dependencies = ["fastapi"]
`), 0644)

	detector := NewDetector()
	name, priority := detector.Detect(tmpDir)

	// Should detect fastapi (higher priority than base python)
	if name != "fastapi" {
		t.Errorf("Expected fastapi, got %s", name)
	}
	if priority < 100 {
		t.Errorf("FastAPI priority should be >= 100, got %d", priority)
	}
}

func TestDetectRust(t *testing.T) {
	tmpDir, err := os.MkdirTemp("", "rust-test")
	if err != nil {
		t.Fatal(err)
	}
	defer os.RemoveAll(tmpDir)

	// Create Cargo.toml
	os.WriteFile(filepath.Join(tmpDir, "Cargo.toml"), []byte(`
[package]
name = "test"

[dependencies]
`), 0644)

	detector := NewDetector()
	name, _ := detector.Detect(tmpDir)

	if name != "rust" {
		t.Errorf("Expected rust, got %s", name)
	}
}

func TestDetectGolang(t *testing.T) {
	tmpDir, err := os.MkdirTemp("", "go-test")
	if err != nil {
		t.Fatal(err)
	}
	defer os.RemoveAll(tmpDir)

	// Create go.mod
	os.WriteFile(filepath.Join(tmpDir, "go.mod"), []byte(`
module test

go 1.22
`), 0644)

	detector := NewDetector()
	name, _ := detector.Detect(tmpDir)

	if name != "golang" {
		t.Errorf("Expected golang, got %s", name)
	}
}

func TestDetectGinFramework(t *testing.T) {
	tmpDir, err := os.MkdirTemp("", "gin-test")
	if err != nil {
		t.Fatal(err)
	}
	defer os.RemoveAll(tmpDir)

	// Create go.mod with gin dependency
	os.WriteFile(filepath.Join(tmpDir, "go.mod"), []byte(`
module test

go 1.22

require github.com/gin-gonic/gin v1.9.1
`), 0644)

	detector := NewDetector()
	name, _ := detector.Detect(tmpDir)

	if name != "gin" {
		t.Errorf("Expected gin, got %s", name)
	}
}

func TestDetectNodePnpm(t *testing.T) {
	tmpDir, err := os.MkdirTemp("", "pnpm-test")
	if err != nil {
		t.Fatal(err)
	}
	defer os.RemoveAll(tmpDir)

	// Create pnpm-lock.yaml
	os.WriteFile(filepath.Join(tmpDir, "pnpm-lock.yaml"), []byte(`
lockfileVersion: 5.4
`), 0644)

	// Create package.json too
	os.WriteFile(filepath.Join(tmpDir, "package.json"), []byte(`{}`), 0644)

	detector := NewDetector()
	name, _ := detector.Detect(tmpDir)

	if name != "nodejs-pnpm" {
		t.Errorf("Expected nodejs-pnpm, got %s", name)
	}
}

func TestTemplateGet(t *testing.T) {
	engine, _ := New()

	// Getting non-existent template should error
	_, err := engine.Get("nonexistent")
	if err == nil {
		t.Error("Should error for non-existent template")
	}
}

func TestTemplateList(t *testing.T) {
	engine, _ := New()
	templates := engine.List()

	// Should return empty list if no templates loaded
	// (In production, there would be embedded templates)
	if templates == nil {
		t.Error("List should not return nil")
	}
}

func TestCategories(t *testing.T) {
	engine, _ := New()
	categories := engine.Categories()

	if categories == nil {
		t.Error("Categories should not return nil")
	}
}

func TestMergeTemplates(t *testing.T) {
	engine, _ := New()

	parent := &Template{
		Name:        "parent",
		Description: "Parent template",
		Variables:   map[string]string{"foo": "bar"},
		Commands:    map[string]string{"build": "npm build"},
	}

	child := &Template{
		Name:        "child",
		Description: "Child template",
		Variables:   map[string]string{"baz": "qux"},
		Commands:    map[string]string{"test": "npm test"},
	}

	merged := engine.mergeTemplates(parent, child)

	if merged.Name != "child" {
		t.Errorf("Name should be child, got %s", merged.Name)
	}

	if merged.Variables["foo"] != "bar" {
		t.Error("Parent variable should be inherited")
	}

	if merged.Variables["baz"] != "qux" {
		t.Error("Child variable should be present")
	}

	if merged.Commands["build"] != "npm build" {
		t.Error("Parent command should be inherited")
	}

	if merged.Commands["test"] != "npm test" {
		t.Error("Child command should be present")
	}
}

func TestResolveVariables(t *testing.T) {
	engine, _ := New()

	cmd := "{{.PackageManager}} install {{.Package}}"
	vars := map[string]string{
		"PackageManager": "npm",
		"Package":        "express",
	}

	result, err := engine.ResolveVariables(cmd, vars)
	if err != nil {
		t.Fatalf("ResolveVariables failed: %v", err)
	}

	expected := "npm install express"
	if result != expected {
		t.Errorf("Expected %q, got %q", expected, result)
	}
}

func TestLoadCustomTemplates(t *testing.T) {
	tmpDir, err := os.MkdirTemp("", "custom-templates")
	if err != nil {
		t.Fatal(err)
	}
	defer os.RemoveAll(tmpDir)

	// Create a custom template
	template := `
name: my-custom
description: Custom template
category: custom
commands:
  build: make build
  test: make test
`
	os.WriteFile(filepath.Join(tmpDir, "my-custom.yaml"), []byte(template), 0644)

	engine, _ := New()
	err = engine.LoadCustomTemplates(tmpDir)
	if err != nil {
		t.Fatalf("Failed to load custom templates: %v", err)
	}

	// Should be able to get the custom template
	tmpl, err := engine.Get("my-custom")
	if err != nil {
		t.Errorf("Should find custom template: %v", err)
	}
	if tmpl != nil && tmpl.Commands["build"] != "make build" {
		t.Error("Custom template commands not loaded correctly")
	}
}

func TestLoadCustomTemplates_NoDir(t *testing.T) {
	engine, _ := New()
	err := engine.LoadCustomTemplates("/nonexistent/path")
	if err != nil {
		t.Error("Should not error for non-existent directory")
	}
}

func TestDetectorDetectAll(t *testing.T) {
	tmpDir, err := os.MkdirTemp("", "detect-all-test")
	if err != nil {
		t.Fatal(err)
	}
	defer os.RemoveAll(tmpDir)

	// Create multiple detection markers
	os.WriteFile(filepath.Join(tmpDir, "package.json"), []byte(`{
		"dependencies": {"next": "14.0.0"}
	}`), 0644)
	os.WriteFile(filepath.Join(tmpDir, "pnpm-lock.yaml"), []byte(""), 0644)

	detector := NewDetector()
	matches := detector.DetectAll(tmpDir)

	if len(matches) < 2 {
		t.Errorf("Expected at least 2 matches, got %d", len(matches))
	}

	// First match should be highest priority
	if len(matches) > 0 && matches[0] != "nextjs" {
		t.Errorf("Expected nextjs as first match, got %s", matches[0])
	}
}

func TestErrNoTemplateMatch(t *testing.T) {
	engine, _ := New()

	tmpDir, err := os.MkdirTemp("", "empty-project")
	if err != nil {
		t.Fatal(err)
	}
	defer os.RemoveAll(tmpDir)

	_, err = engine.Detect(tmpDir)
	if err != ErrNoTemplateMatch {
		t.Errorf("Expected ErrNoTemplateMatch, got %v", err)
	}
}

func TestDetectDjango(t *testing.T) {
	tmpDir, err := os.MkdirTemp("", "django-test")
	if err != nil {
		t.Fatal(err)
	}
	defer os.RemoveAll(tmpDir)

	// Create manage.py (Django marker)
	os.WriteFile(filepath.Join(tmpDir, "manage.py"), []byte(`#!/usr/bin/env python
import django
`), 0644)

	detector := NewDetector()
	name, _ := detector.Detect(tmpDir)

	if name != "django" {
		t.Errorf("Expected django, got %s", name)
	}
}

func TestDetectRails(t *testing.T) {
	tmpDir, err := os.MkdirTemp("", "rails-test")
	if err != nil {
		t.Fatal(err)
	}
	defer os.RemoveAll(tmpDir)

	// Create Gemfile with rails
	os.WriteFile(filepath.Join(tmpDir, "Gemfile"), []byte(`
source 'https://rubygems.org'
gem 'rails', '~> 7.0'
`), 0644)

	detector := NewDetector()
	name, _ := detector.Detect(tmpDir)

	if name != "rails" {
		t.Errorf("Expected rails, got %s", name)
	}
}

func TestDetectVite(t *testing.T) {
	tmpDir, err := os.MkdirTemp("", "vite-test")
	if err != nil {
		t.Fatal(err)
	}
	defer os.RemoveAll(tmpDir)

	// Create vite.config.ts
	os.WriteFile(filepath.Join(tmpDir, "vite.config.ts"), []byte(`
import { defineConfig } from 'vite'
export default defineConfig({})
`), 0644)

	// Also create package.json
	os.WriteFile(filepath.Join(tmpDir, "package.json"), []byte(`{}`), 0644)

	detector := NewDetector()
	name, _ := detector.Detect(tmpDir)

	if name != "vite" {
		t.Errorf("Expected vite, got %s", name)
	}
}
