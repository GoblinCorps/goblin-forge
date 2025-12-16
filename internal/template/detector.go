package template

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
)

// Detector handles project type auto-detection
type Detector struct {
	rules []DetectorRule
}

// DetectorRule defines a detection rule
type DetectorRule struct {
	Name       string
	Priority   int
	FileCheck  func(path string) bool
	ContentCheck func(path string) bool
}

// NewDetector creates a new project type detector
func NewDetector() *Detector {
	d := &Detector{
		rules: make([]DetectorRule, 0),
	}
	d.registerBuiltinRules()
	return d
}

// registerBuiltinRules registers all built-in detection rules
func (d *Detector) registerBuiltinRules() {
	// Node.js ecosystem (higher priority for specific package managers)
	d.rules = append(d.rules, DetectorRule{
		Name:     "nodejs-bun",
		Priority: 100,
		FileCheck: func(path string) bool {
			return fileExists(filepath.Join(path, "bun.lockb"))
		},
	})

	d.rules = append(d.rules, DetectorRule{
		Name:     "nodejs-pnpm",
		Priority: 90,
		FileCheck: func(path string) bool {
			return fileExists(filepath.Join(path, "pnpm-lock.yaml"))
		},
	})

	d.rules = append(d.rules, DetectorRule{
		Name:     "nodejs-yarn",
		Priority: 85,
		FileCheck: func(path string) bool {
			return fileExists(filepath.Join(path, "yarn.lock"))
		},
	})

	d.rules = append(d.rules, DetectorRule{
		Name:     "nodejs",
		Priority: 50,
		FileCheck: func(path string) bool {
			return fileExists(filepath.Join(path, "package.json"))
		},
	})

	// Node.js frameworks (higher priority than base nodejs)
	d.rules = append(d.rules, DetectorRule{
		Name:     "nextjs",
		Priority: 110,
		ContentCheck: func(path string) bool {
			return hasPackageDependency(path, "next")
		},
	})

	d.rules = append(d.rules, DetectorRule{
		Name:     "vite",
		Priority: 105,
		FileCheck: func(path string) bool {
			return fileExists(filepath.Join(path, "vite.config.ts")) ||
				fileExists(filepath.Join(path, "vite.config.js"))
		},
	})

	d.rules = append(d.rules, DetectorRule{
		Name:     "remix",
		Priority: 110,
		ContentCheck: func(path string) bool {
			return hasPackageDependency(path, "@remix-run/react")
		},
	})

	d.rules = append(d.rules, DetectorRule{
		Name:     "astro",
		Priority: 110,
		ContentCheck: func(path string) bool {
			return hasPackageDependency(path, "astro")
		},
	})

	// Python ecosystem
	d.rules = append(d.rules, DetectorRule{
		Name:     "python-uv",
		Priority: 100,
		FileCheck: func(path string) bool {
			return fileExists(filepath.Join(path, "uv.lock"))
		},
	})

	d.rules = append(d.rules, DetectorRule{
		Name:     "python-poetry",
		Priority: 95,
		FileCheck: func(path string) bool {
			return fileExists(filepath.Join(path, "poetry.lock"))
		},
	})

	d.rules = append(d.rules, DetectorRule{
		Name:     "python-pipenv",
		Priority: 90,
		FileCheck: func(path string) bool {
			return fileExists(filepath.Join(path, "Pipfile.lock"))
		},
	})

	d.rules = append(d.rules, DetectorRule{
		Name:     "python",
		Priority: 50,
		FileCheck: func(path string) bool {
			return fileExists(filepath.Join(path, "pyproject.toml")) ||
				fileExists(filepath.Join(path, "requirements.txt")) ||
				fileExists(filepath.Join(path, "setup.py"))
		},
	})

	// Python frameworks
	d.rules = append(d.rules, DetectorRule{
		Name:     "fastapi",
		Priority: 110,
		ContentCheck: func(path string) bool {
			return hasPythonDependency(path, "fastapi")
		},
	})

	d.rules = append(d.rules, DetectorRule{
		Name:     "django",
		Priority: 110,
		FileCheck: func(path string) bool {
			return fileExists(filepath.Join(path, "manage.py"))
		},
	})

	d.rules = append(d.rules, DetectorRule{
		Name:     "flask",
		Priority: 105,
		ContentCheck: func(path string) bool {
			return hasPythonDependency(path, "flask")
		},
	})

	// Rust
	d.rules = append(d.rules, DetectorRule{
		Name:     "rust",
		Priority: 50,
		FileCheck: func(path string) bool {
			return fileExists(filepath.Join(path, "Cargo.toml"))
		},
	})

	d.rules = append(d.rules, DetectorRule{
		Name:     "actix",
		Priority: 110,
		ContentCheck: func(path string) bool {
			return hasCargoDepenency(path, "actix-web")
		},
	})

	// Go
	d.rules = append(d.rules, DetectorRule{
		Name:     "golang",
		Priority: 50,
		FileCheck: func(path string) bool {
			return fileExists(filepath.Join(path, "go.mod"))
		},
	})

	d.rules = append(d.rules, DetectorRule{
		Name:     "gin",
		Priority: 110,
		ContentCheck: func(path string) bool {
			return hasGoDependency(path, "github.com/gin-gonic/gin")
		},
	})

	// Ruby
	d.rules = append(d.rules, DetectorRule{
		Name:     "ruby",
		Priority: 50,
		FileCheck: func(path string) bool {
			return fileExists(filepath.Join(path, "Gemfile"))
		},
	})

	d.rules = append(d.rules, DetectorRule{
		Name:     "rails",
		Priority: 110,
		ContentCheck: func(path string) bool {
			return hasGemDependency(path, "rails")
		},
	})

	// Elixir
	d.rules = append(d.rules, DetectorRule{
		Name:     "elixir",
		Priority: 50,
		FileCheck: func(path string) bool {
			return fileExists(filepath.Join(path, "mix.exs"))
		},
	})

	d.rules = append(d.rules, DetectorRule{
		Name:     "phoenix",
		Priority: 110,
		ContentCheck: func(path string) bool {
			return hasMixDependency(path, "phoenix")
		},
	})

	// Java
	d.rules = append(d.rules, DetectorRule{
		Name:     "java-maven",
		Priority: 60,
		FileCheck: func(path string) bool {
			return fileExists(filepath.Join(path, "pom.xml"))
		},
	})

	d.rules = append(d.rules, DetectorRule{
		Name:     "java-gradle",
		Priority: 60,
		FileCheck: func(path string) bool {
			return fileExists(filepath.Join(path, "build.gradle")) ||
				fileExists(filepath.Join(path, "build.gradle.kts"))
		},
	})

	// .NET
	d.rules = append(d.rules, DetectorRule{
		Name:     "dotnet",
		Priority: 50,
		FileCheck: func(path string) bool {
			matches, _ := filepath.Glob(filepath.Join(path, "*.csproj"))
			return len(matches) > 0
		},
	})

	// C/C++
	d.rules = append(d.rules, DetectorRule{
		Name:     "c-cpp",
		Priority: 40,
		FileCheck: func(path string) bool {
			return fileExists(filepath.Join(path, "CMakeLists.txt")) ||
				fileExists(filepath.Join(path, "Makefile")) ||
				fileExists(filepath.Join(path, "meson.build"))
		},
	})

	// Zig
	d.rules = append(d.rules, DetectorRule{
		Name:     "zig",
		Priority: 50,
		FileCheck: func(path string) bool {
			return fileExists(filepath.Join(path, "build.zig"))
		},
	})
}

// Detect identifies the project type
func (d *Detector) Detect(path string) (string, int) {
	var bestMatch string
	var bestPriority int = -1

	for _, rule := range d.rules {
		matched := false

		if rule.FileCheck != nil && rule.FileCheck(path) {
			matched = true
		}

		if rule.ContentCheck != nil && rule.ContentCheck(path) {
			matched = true
		}

		if matched && rule.Priority > bestPriority {
			bestMatch = rule.Name
			bestPriority = rule.Priority
		}
	}

	return bestMatch, bestPriority
}

// DetectAll returns all matching templates sorted by priority
func (d *Detector) DetectAll(path string) []string {
	type match struct {
		name     string
		priority int
	}

	var matches []match

	for _, rule := range d.rules {
		matched := false

		if rule.FileCheck != nil && rule.FileCheck(path) {
			matched = true
		}

		if rule.ContentCheck != nil && rule.ContentCheck(path) {
			matched = true
		}

		if matched {
			matches = append(matches, match{rule.Name, rule.Priority})
		}
	}

	// Sort by priority (highest first)
	for i := 0; i < len(matches); i++ {
		for j := i + 1; j < len(matches); j++ {
			if matches[j].priority > matches[i].priority {
				matches[i], matches[j] = matches[j], matches[i]
			}
		}
	}

	result := make([]string, len(matches))
	for i, m := range matches {
		result[i] = m.name
	}

	return result
}

// Helper functions

func fileExists(path string) bool {
	_, err := os.Stat(path)
	return err == nil
}

func hasPackageDependency(path, pkg string) bool {
	data, err := os.ReadFile(filepath.Join(path, "package.json"))
	if err != nil {
		return false
	}

	var pkgJSON map[string]interface{}
	if err := json.Unmarshal(data, &pkgJSON); err != nil {
		return false
	}

	// Check dependencies
	if deps, ok := pkgJSON["dependencies"].(map[string]interface{}); ok {
		if _, found := deps[pkg]; found {
			return true
		}
	}

	// Check devDependencies
	if deps, ok := pkgJSON["devDependencies"].(map[string]interface{}); ok {
		if _, found := deps[pkg]; found {
			return true
		}
	}

	return false
}

func hasPythonDependency(path, pkg string) bool {
	// Check pyproject.toml
	data, err := os.ReadFile(filepath.Join(path, "pyproject.toml"))
	if err == nil {
		if strings.Contains(string(data), pkg) {
			return true
		}
	}

	// Check requirements.txt
	data, err = os.ReadFile(filepath.Join(path, "requirements.txt"))
	if err == nil {
		lines := strings.Split(string(data), "\n")
		for _, line := range lines {
			if strings.HasPrefix(strings.TrimSpace(line), pkg) {
				return true
			}
		}
	}

	return false
}

func hasCargoDepenency(path, pkg string) bool {
	data, err := os.ReadFile(filepath.Join(path, "Cargo.toml"))
	if err != nil {
		return false
	}
	return strings.Contains(string(data), pkg)
}

func hasGoDependency(path, pkg string) bool {
	data, err := os.ReadFile(filepath.Join(path, "go.mod"))
	if err != nil {
		return false
	}
	return strings.Contains(string(data), pkg)
}

func hasGemDependency(path, gem string) bool {
	data, err := os.ReadFile(filepath.Join(path, "Gemfile"))
	if err != nil {
		return false
	}
	return strings.Contains(string(data), gem)
}

func hasMixDependency(path, pkg string) bool {
	data, err := os.ReadFile(filepath.Join(path, "mix.exs"))
	if err != nil {
		return false
	}
	return strings.Contains(string(data), pkg)
}
