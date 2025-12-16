# Manager Agent Architecture Design

**Issue:** #13
**Author:** Frack
**Status:** Draft

---

## Key Insight: The Manager is a Recipe, Not Code

After analyzing the architecture, I've realized something: **we don't need to build a manager agent into goblin-forge**. The manager agent is a *usage pattern* composed of existing pieces:

1. **goblin-forge MCP server** (Issue #12 - DONE)
2. **GitHub MCP server** (exists: `@modelcontextprotocol/server-github`)
3. **Any MCP-capable agent** (Crush, Claude Code, etc.)
4. **A system prompt** defining the manager persona

The "Manager Agent" is not new infrastructure. It's a **configuration recipe**.

---

## Answering the Open Questions

### Q1: Where does the manager run?

**Answer: Wherever the user wants.**

The manager runs in any MCP-capable agent:
- Crush (via `crush.json` MCP config)
- Claude Code (via `claude-code-config.json`)
- Any future MCP-capable agent

We don't build `gforge manager`. We document how to configure existing agents as managers.

**Why this is better:**
- No new code to maintain
- Users choose their preferred agent
- Works with future agents automatically
- We already did the hard work (Issue #12)

### Q2: What MCP tools does the manager need?

**Core tools (required):**

| Server | Tools | Purpose |
|--------|-------|---------|
| `goblin-forge` | `gforge_spawn`, `gforge_list`, `gforge_status`, `gforge_send`, `gforge_output`, `gforge_stop`, `gforge_kill`, `gforge_stats` | Control goblins |
| `github` | `create_issue`, `create_pr`, `get_issue`, `list_issues` | Project management |

**Extension tools (optional):**

| Server | Tools | Purpose |
|--------|-------|---------|
| `slack` | `send_message` | Team notifications |
| `discord` | `send_message` | Team notifications |
| `linear` | `create_issue`, `update_issue` | Ticket management |

**Existing MCP servers we can leverage:**
- `@modelcontextprotocol/server-github` - GitHub operations
- `@modelcontextprotocol/server-slack` - Slack notifications
- Custom servers for Linear, Jira, etc.

### Q3: What's the interaction model?

**Recommended: On-demand with optional polling.**

**Phase 1 (MVP):** On-demand
- User invokes manager: "Review all goblins"
- Manager calls `gforge_list`, `gforge_output`, analyzes, reports
- User triggers reviews when needed

**Phase 2 (Future):** Event-driven
- Requires hooks integration (Issue #10)
- Goblins emit events, manager reacts
- More complex, deferred for now

### Q4: How does the manager personality work?

**Answer: System prompt in agent config.**

The manager's personality is defined by its system prompt. We provide a default "Frick-style" prompt, users can customize.

---

## The Recipe: Manager Agent Configuration

### For Crush

**crush.json:**
```json
{
  "mcp": {
    "goblin-forge": {
      "type": "stdio",
      "command": "gforge",
      "args": ["mcp-server"]
    },
    "github": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"]
    }
  },
  "system_prompt_file": "manager-prompt.md"
}
```

**manager-prompt.md:**
```markdown
# Manager Agent System Prompt

You are a PROJECT MANAGER for a team of AI coding agents ("goblins").

## Your Role
- **Coordinate**: Assign tasks, manage priorities
- **Review**: Check work across goblins, identify issues
- **Report**: Generate status summaries
- **Integrate**: File GitHub issues, update tickets
- **NEVER CODE**: Delegate all implementation work to goblins

## Your Tools
- `gforge_list` - See all active goblins
- `gforge_status` - Get details on a specific goblin
- `gforge_output` - Read a goblin's terminal output
- `gforge_send` - Send instructions to a goblin
- `gforge_spawn` - Create a new goblin for a task
- `gforge_stop/kill` - Clean up completed goblins
- `github_*` - File issues, create PRs

## Workflow
1. When asked for status: `gforge_list`, then `gforge_output` for each
2. When reviewing work: Read outputs, identify issues, file GitHub issues
3. When assigning tasks: `gforge_spawn` or `gforge_send` to existing goblin
4. When work is ready: Guide user to create PR (or use `github_create_pr`)

## Personality
You are organized, supportive, and slightly obsessed with process. You use
labels. You love a good status update. You file issues with enthusiasm.
```

### For Claude Code

**.claude/claude_code_config.json:**
```json
{
  "mcpServers": {
    "goblin-forge": {
      "command": "gforge",
      "args": ["mcp-server"]
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"]
    }
  }
}
```

Then invoke with a manager-focused prompt:
```bash
claude --system-prompt "$(cat manager-prompt.md)"
```

---

## Example Manager Session

```
User: What's the status of the team?

Manager (using gforge_list):
Currently managing 3 goblins:

1. "auth-impl" (claude) - Running for 23 minutes on branch feat/auth
2. "test-writer" (crush) - Running for 12 minutes on branch test/auth
3. "docs-updater" (codex) - Idle for 5 minutes on branch docs/auth

Let me check their progress...

Manager (using gforge_output for each):
📊 Status Report:

**auth-impl**: Making progress on login flow. Has implemented
  basic session handling. Currently working on logout.

**test-writer**: Has written 12 test cases for auth module.
  All passing. Ready for review.

**docs-updater**: Completed API documentation for /auth endpoints.
  Waiting for auth-impl to finish for final review.

Recommendation: test-writer's work is ready for review. Shall I
file a PR for the test suite?
```

---

## Proof of Concept Plan

### Phase 1: Document the Recipe (This Week)
- [x] Design document (this file)
- [ ] Example `crush.json` for manager mode
- [ ] Example `manager-prompt.md`
- [ ] Add to README or create docs/MANAGER.md

### Phase 2: Test with Crush
- [ ] Configure Crush with goblin-forge MCP
- [ ] Test manager prompt with real goblins
- [ ] Iterate on prompt based on results

### Phase 3: Expand Documentation
- [ ] Claude Code configuration guide
- [ ] Custom persona examples (strict manager, supportive mentor, etc.)
- [ ] Troubleshooting guide

---

## Why This Design is Elegant

1. **No new code** - We already built the hard part (Issue #12)
2. **Agent agnostic** - Works with Crush, Claude Code, future agents
3. **Customizable** - Users tweak the system prompt for their style
4. **Composable** - Add more MCP servers for more capabilities
5. **Future-proof** - As agents improve, the manager improves

---

## Open Items for Discussion

1. **Should we ship a default manager prompt with goblin-forge?**
   - Pro: Easy onboarding
   - Con: Maintenance burden

2. **Should `gforge` have a convenience command for manager mode?**
   - Something like `gforge manager --agent crush`
   - Would just launch the configured agent with manager prompt
   - Nice UX but adds code we said we don't need

3. **Event-driven architecture (Phase 2)?**
   - Requires Issue #10 (hooks-based output)
   - Could enable "manager daemon" that reacts to goblin events
   - Deferred for now

---

*"Every team needs a Frick. But Frick doesn't need to be code."*
