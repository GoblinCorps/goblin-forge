package main

import (
	"fmt"
	"os"

	"github.com/astoreyai/goblin-forge/internal/config"
	"github.com/astoreyai/goblin-forge/internal/coordinator"
	"github.com/astoreyai/goblin-forge/internal/logging"
	"github.com/astoreyai/goblin-forge/internal/storage"
	"github.com/astoreyai/goblin-forge/internal/tui"
	"github.com/spf13/cobra"
)

var (
	Version   = "0.1.0"
	Commit    = "dev"
	BuildDate = "unknown"
)

var (
	cfgFile string
	verbose bool
	cfg     *config.Config
	db      *storage.DB
	log     *logging.Logger
)

func main() {
	rootCmd := &cobra.Command{
		Use:   "gforge",
		Short: "Goblin Forge - Multi-agent CLI orchestrator",
		Long: `Goblin Forge (gforge) is a multi-agent command-line orchestrator
designed to coordinate and execute multiple coding-focused CLI agents in parallel.

"Where code is forged by many small minds."`,
		PersistentPreRunE: initializeApp,
		SilenceUsage:      true,
	}

	// Global flags
	rootCmd.PersistentFlags().StringVar(&cfgFile, "config", "", "config file (default ~/.config/gforge/config.yaml)")
	rootCmd.PersistentFlags().BoolVarP(&verbose, "verbose", "v", false, "verbose output")

	// Add commands
	rootCmd.AddCommand(
		newVersionCmd(),
		newConfigCmd(),
		newAgentsCmd(),
		newSpawnCmd(),
		newListCmd(),
		newStopCmd(),
		newKillCmd(),
		newAttachCmd(),
		newLogsCmd(),
		newDiffCmd(),
		newTaskCmd(),
		newStatusCmd(),
		newTopCmd(),
	)

	if err := rootCmd.Execute(); err != nil {
		os.Exit(1)
	}
}

func initializeApp(cmd *cobra.Command, args []string) error {
	// Skip initialization for version command
	if cmd.Name() == "version" {
		return nil
	}

	// Initialize logger
	log = logging.New(verbose)

	// Load configuration
	var err error
	cfg, err = config.Load(cfgFile)
	if err != nil {
		return fmt.Errorf("failed to load config: %w", err)
	}

	// Initialize database
	db, err = storage.New(cfg.DatabasePath)
	if err != nil {
		return fmt.Errorf("failed to initialize database: %w", err)
	}

	return nil
}

// === Version Command ===

func newVersionCmd() *cobra.Command {
	return &cobra.Command{
		Use:   "version",
		Short: "Print version information",
		Run: func(cmd *cobra.Command, args []string) {
			fmt.Printf("Goblin Forge %s\n", Version)
			fmt.Printf("  Commit:     %s\n", Commit)
			fmt.Printf("  Built:      %s\n", BuildDate)
			fmt.Printf("  Go version: go1.22+\n")
		},
	}
}

// === Config Command ===

func newConfigCmd() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "config",
		Short: "Manage configuration",
	}

	cmd.AddCommand(&cobra.Command{
		Use:   "show",
		Short: "Show current configuration",
		RunE: func(cmd *cobra.Command, args []string) error {
			return config.Show(cfg)
		},
	})

	cmd.AddCommand(&cobra.Command{
		Use:   "path",
		Short: "Show configuration file path",
		Run: func(cmd *cobra.Command, args []string) {
			fmt.Println(config.GetConfigPath(cfgFile))
		},
	})

	cmd.AddCommand(&cobra.Command{
		Use:   "init",
		Short: "Initialize default configuration",
		RunE: func(cmd *cobra.Command, args []string) error {
			return config.Initialize()
		},
	})

	return cmd
}

// === Agents Command ===

func newAgentsCmd() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "agents",
		Short: "Manage agent definitions",
	}

	cmd.AddCommand(&cobra.Command{
		Use:   "list",
		Short: "List available agents",
		RunE: func(cmd *cobra.Command, args []string) error {
			return listAgents()
		},
	})

	cmd.AddCommand(&cobra.Command{
		Use:   "scan",
		Short: "Scan for installed agents",
		RunE: func(cmd *cobra.Command, args []string) error {
			return scanAgents()
		},
	})

	return cmd
}

// === Spawn Command ===

func newSpawnCmd() *cobra.Command {
	var (
		agent   string
		project string
		branch  string
	)

	cmd := &cobra.Command{
		Use:   "spawn <name>",
		Short: "Spawn a new goblin (agent instance)",
		Long: `Create and start a new goblin with the specified agent.

Examples:
  gforge spawn coder --agent claude
  gforge spawn reviewer --agent gemini --project ./myapp
  gforge spawn tester --agent codex --branch feat/tests`,
		Args: cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			name := args[0]
			return spawnGoblin(name, agent, project, branch)
		},
	}

	cmd.Flags().StringVarP(&agent, "agent", "a", "claude", "Agent to use (claude, codex, gemini, ollama)")
	cmd.Flags().StringVarP(&project, "project", "p", ".", "Project directory")
	cmd.Flags().StringVarP(&branch, "branch", "b", "", "Git branch name (auto-generated if empty)")

	return cmd
}

// === List Command ===

func newListCmd() *cobra.Command {
	return &cobra.Command{
		Use:     "list",
		Aliases: []string{"ls"},
		Short:   "List all goblins",
		RunE: func(cmd *cobra.Command, args []string) error {
			return listGoblins()
		},
	}
}

// === Stop Command ===

func newStopCmd() *cobra.Command {
	return &cobra.Command{
		Use:   "stop <name>",
		Short: "Stop a running goblin",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			return stopGoblin(args[0])
		},
	}
}

// === Kill Command ===

func newKillCmd() *cobra.Command {
	return &cobra.Command{
		Use:   "kill <name>",
		Short: "Kill a goblin and cleanup its resources",
		Long:  `Forcefully terminate a goblin, remove its tmux session and optionally its worktree.`,
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			return killGoblin(args[0])
		},
	}
}

// === Attach Command ===

func newAttachCmd() *cobra.Command {
	return &cobra.Command{
		Use:     "attach <name>",
		Aliases: []string{"a"},
		Short:   "Attach to a goblin's tmux session",
		Long: `Attach to a running goblin's tmux session.
Use Ctrl+B D to detach and return to gforge.`,
		Args: cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			return attachGoblin(args[0])
		},
	}
}

// === Logs Command ===

func newLogsCmd() *cobra.Command {
	var (
		lines int
		follow bool
	)

	cmd := &cobra.Command{
		Use:   "logs <name>",
		Short: "View goblin output logs",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			return showLogs(args[0], lines, follow)
		},
	}

	cmd.Flags().IntVarP(&lines, "lines", "n", 50, "Number of lines to show")
	cmd.Flags().BoolVarP(&follow, "follow", "f", false, "Follow log output")

	return cmd
}

// === Diff Command ===

func newDiffCmd() *cobra.Command {
	var staged bool

	cmd := &cobra.Command{
		Use:   "diff <name>",
		Short: "Show changes made by a goblin",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			return showDiff(args[0], staged)
		},
	}

	cmd.Flags().BoolVarP(&staged, "staged", "s", false, "Show staged changes only")

	return cmd
}

// === Task Command ===

func newTaskCmd() *cobra.Command {
	var goblin string

	cmd := &cobra.Command{
		Use:   "task <description>",
		Short: "Send a task to a goblin",
		Long: `Send a task description to a running goblin.
The task will be typed into the goblin's terminal session.`,
		Args: cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			return sendTask(args[0], goblin)
		},
	}

	cmd.Flags().StringVarP(&goblin, "goblin", "g", "", "Target goblin name (required)")
	cmd.MarkFlagRequired("goblin")

	return cmd
}

// === Status Command ===

func newStatusCmd() *cobra.Command {
	return &cobra.Command{
		Use:   "status",
		Short: "Show system status",
		RunE: func(cmd *cobra.Command, args []string) error {
			return showStatus()
		},
	}
}

// === Top Command (TUI Dashboard) ===

func newTopCmd() *cobra.Command {
	return &cobra.Command{
		Use:   "top",
		Short: "Launch interactive TUI dashboard",
		Long: `Launch an htop-like interactive terminal UI for managing goblins.

Keybindings:
  j/k, Up/Down  Navigate goblin list
  a, Enter      Attach to selected goblin
  s             Stop selected goblin
  K (Shift+K)   Kill selected goblin
  d             Show diff for selected goblin
  r             Refresh goblin list
  ?             Show help
  q             Quit`,
		RunE: func(cmd *cobra.Command, args []string) error {
			coord := coordinator.New(db, cfg, log)
			return tui.Run(coord)
		},
	}
}
