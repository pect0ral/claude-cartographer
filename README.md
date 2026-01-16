# Claude Cartographer

**Save 95%+ tokens when working with large codebases in Claude Code**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/pect0ral/claude-cartographer/pulls)
[![Issues](https://img.shields.io/github/issues/pect0ral/claude-cartographer)](https://github.com/pect0ral/claude-cartographer/issues)

> **Topics:** `claude` `claude-code` `agents` `skills` `hooks` `token-optimization` `developer-tools` `ai` `llm` `code-analysis` `productivity` `anthropic`

---

## The Problem

In using Claude Code extensively, I found myself hitting token limits faster and faster—even on max plans. Every file read, every search operation was burning through my budget. I needed a better way.

## The Solution

What started as an experiment with Claude hooks and skills evolved into **Claude Cartographer**—a tool that maps out your entire project and takes inventory of all relevant files, classes, methods, functions, and more across common languages like Python, Go, JavaScript, TypeScript, SQL, and others.

The mapping updates automatically as you edit files. When you ask Claude to interact with your codebase, it checks the map first instead of searching blindly or reading whole files—saving your valuable tokens.

**Instead of loading entire files (10,000-50,000+ tokens), queries return 200-2,000 tokens.**

**Result: 95-98% token reduction** on typical codebase queries.

---

## How It Works

Claude Cartographer creates a lightweight, searchable database of your codebase:

1. **Initial Mapping** - Scans your project and extracts all classes, functions, methods, components, and exports
2. **Smart Storage** - Uses a 3-tier storage system (compact/summary/full) optimized for token efficiency
3. **Real-Time Updates** - Watches for file changes and updates the map automatically via Claude Code hooks
4. **Instant Queries** - When Claude needs information, it queries the map first instead of reading full files
5. **Token Savings** - Returns precise locations and signatures using 50-200 tokens instead of thousands

### Integration with Claude Code

The tool integrates seamlessly via:
- **Hooks** - Automatically queue file updates when you use Edit/Write tools
- **Skills** - Claude learns to search the map before reading files
- **CLI** - Direct commands for querying and managing the map

---

## Major Components

### 1. Multi-Language Parsers
Extracts structure from source code:
- **Python** - Full AST parsing with type hints, decorators, async/await
- **JavaScript/TypeScript** - Classes, functions, interfaces, React components, JSX
- **Go** - Structs, interfaces, functions, methods, goroutines
- **Ruby** - Classes, modules, methods, mixins
- **Templates** - Jinja2, EJS, Handlebars, SQL schemas

### 2. SQLite Database Backend
High-performance storage with:
- **FTS5 Full-Text Search** - Lightning-fast natural language queries
- **WAL Mode** - Write-ahead logging for concurrent access
- **Memory Mapping** - Optimized for large codebases
- **3-Tier Storage** - Compact (50 tokens), Summary (200 tokens), Full (compressed)

### 3. File Watcher & Auto-Updates
Real-time synchronization:
- **Debounced Updates** - Batches changes to avoid thrashing
- **Update Queue** - Collects changes during Claude Code sessions
- **Smart Invalidation** - Only re-parses modified files

### 4. Claude Code Hooks
Automatic integration:
- **cartographer-update.sh** - Queues file changes on Edit/Write
- **cartographer-finalize.sh** - Processes updates at session end
- **settings.json** - Hook configuration for Claude Code

### 5. CLI & Python API
Flexible access:
- **CLI Commands** - `find`, `query`, `show`, `stats`, `benchmark`
- **Python API** - `ClaudeCodeIntegration` class for programmatic use
- **Token Budgeting** - Query with max token limits for precise control

---

## Features

- **3-Tier Storage**: Compact (50 tokens), Summary (200 tokens), Full (compressed)
- **Multi-Language Support**: Python, JavaScript/TypeScript, Go, Ruby, Jinja2, EJS, Handlebars
- **SQLite Backend**: Optimized with FTS5 full-text search, WAL mode, memory mapping
- **Portable Installation**: Self-contained in `.claude-map/` with local venv
- **Real-Time Updates**: File watching with debouncing
- **Performance Benchmarking**: Compare token savings vs traditional approach

## Quick Start

```bash
# Clone or download the repository
git clone https://github.com/pect0ral/claude-cartographer.git
cd codebase-cartographer

# ONE-COMMAND SETUP (installs + initializes + benchmarks)
./setup.sh /path/to/your/project

# Or step-by-step:
./quick-install.sh /path/to/your/project
cd /path/to/your/project
.claude-map/bin/claude-map init

# Query the map
.claude-map/bin/claude-map query "find authentication components"
.claude-map/bin/claude-map find UserProfile
.claude-map/bin/claude-map stats
```

## Installation

### Option 1: Quick Install (Recommended)

```bash
# macOS/Linux
./quick-install.sh /path/to/project
```

> **Note:** Windows is not currently supported. macOS and Linux only.

### Option 2: Python Install

```bash
python install.py /path/to/project
```

### Option 3: Manual Install

```bash
cd /path/to/project
python -m venv .claude-map/venv
.claude-map/venv/bin/pip install click watchdog tiktoken
# Copy src/cartographer to .claude-map/src/cartographer
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `init` | Initialize codebase mapping |
| `update` | Incremental update (changed files only) |
| `query <text>` | Natural language query |
| `find <name>` | Quick component search |
| `show <file>` | Show components in a file |
| `stats` | Display statistics |
| `watch` | Real-time file watching |
| `benchmark` | Run performance benchmark |
| `optimize` | Optimize database |
| `exports` | List exported components |

## Usage Examples

```bash
# Initialize mapping
claude-map init

# Find components
claude-map find UserProfile
claude-map query "find authentication"

# Show file contents
claude-map show src/auth/user.py

# Get dependencies
claude-map query "dependencies for auth.py"

# View statistics
claude-map stats

# Run benchmark
claude-map benchmark

# Watch for changes
claude-map watch
```

## Python API

```python
from cartographer import ClaudeCodeIntegration

# Initialize
integration = ClaudeCodeIntegration('/path/to/project')

# Token-budgeted queries
context = integration.get_context("find authentication", max_tokens=2000)

# Quick operations
result = integration.quick_find('UserProfile')
summary = integration.get_file_summary('src/auth.py')
exports = integration.list_exports()
stats = integration.get_stats()

# Clean up
integration.close()
```

## Performance Targets

| Operation | Traditional | Optimized | Savings |
|-----------|-------------|-----------|---------|
| Find component | 15,000 | 200 | 98.7% |
| File dependencies | 25,000 | 500 | 98.0% |
| List exports | 30,000 | 1,000 | 96.7% |
| File summary | 20,000 | 800 | 96.0% |
| Call chain | 40,000 | 1,500 | 96.3% |

**Overall: 95-98% token reduction**

## Supported Languages

- **Python** - Full AST parsing with type hints, decorators
- **JavaScript/TypeScript** - Classes, functions, interfaces, React components
- **Go** - Structs, interfaces, functions, methods
- **Ruby** - Classes, modules, methods
- **Templates** - Jinja2, EJS, Handlebars

## Directory Structure

```
project/
├── .claude-map/              # Self-contained installation
│   ├── codebase.db          # SQLite database
│   ├── venv/                # Python virtual environment
│   ├── bin/                 # Launcher scripts
│   │   └── claude-map       # Main CLI
│   ├── src/cartographer/    # Source code
│   ├── cache/               # Query cache
│   └── config.json          # Configuration
├── .claude/                  # Claude Code integration
│   ├── hooks/               # Auto-update hooks
│   │   └── cartographer-update.sh
│   ├── skills/              # Skill definitions
│   │   └── cartographer.md
│   └── settings.json        # Hook configuration
└── your-code/               # Your actual code
```

## Claude Code Integration

The installer automatically sets up Claude Code integration:

### CLAUDE.md Integration

The installer adds instructions to your project's `CLAUDE.md` file that teach Claude to prioritize the cartographer over its native tools:

```markdown
## CRITICAL: Use Codebase Cartographer First

**You MUST use the cartographer BEFORE using Read, Grep, or Glob tools to explore code.**

**In Planning Mode:** When using EnterPlanMode, your FIRST action should be to use the cartographer...
```

**Key behaviors:**
- Claude is instructed to query the cartographer **first** before using Read, Grep, or Glob
- In **Planning Mode**, Claude uses the cartographer as its first action to understand the codebase structure
- If the cartographer returns no results, Claude **falls back** to its native tools (Grep, Glob, Read)
- The section is wrapped in `<!-- CARTOGRAPHER_START -->` / `<!-- CARTOGRAPHER_END -->` markers for easy updates

This "cartographer-first, native-fallback" approach ensures Claude always tries the token-efficient path while maintaining full functionality for edge cases the cartographer doesn't cover.

### Automatic Updates
Hooks automatically queue file updates when you use Edit/Write tools.
The map is updated at session end or when the queue reaches 10 files.

### Skills
Claude learns to use the cartographer via `.claude/skills/cartographer.md`.
It will prefer searching the map before reading full files.

### /map Command
Use `/map` in Claude Code for manual operations:
- `/map init` - Initialize mapping
- `/map update` - Update changed files
- `/map stats` - Show statistics
- `/map find <name>` - Quick search

### Best Practice
Claude will automatically search the map before reading files:
```bash
# Claude runs this first:
.claude-map/bin/claude-map find UserProfile
# Output: class UserProfile(p:3, m:5) - src/models/user.py:42

# Then reads only the relevant lines:
Read src/models/user.py lines 42-80
```

This saves **95%+ tokens** on typical queries.

## Configuration

Edit `.claude-map/config.json`:

```json
{
  "settings": {
    "max_workers": 8,
    "cache_enabled": true,
    "watch_enabled": true,
    "ignore_patterns": [
      "node_modules",
      ".git",
      "__pycache__"
    ]
  }
}
```

## Contributing

**We'd love your help!** Claude Cartographer is an open-source project aimed at helping developers maximize their Claude subscriptions and get more value from the models they have access to.

### Ways to Contribute

We're looking for support in several areas:

#### 1. Extend Language Support
Help us parse more languages and frameworks:
- **Rust** - Structs, traits, impls, macros
- **Java/Kotlin** - Classes, interfaces, annotations
- **C/C++** - Headers, classes, templates
- **Swift** - Classes, protocols, extensions
- **PHP** - Classes, traits, namespaces
- **Shell Scripts** - Functions, exported variables
- **Terraform/HCL** - Resources, modules, variables

#### 2. Enhance Existing Parsers
Improve token efficiency:
- Better signature compression techniques
- Smarter dependency extraction
- More accurate type inference
- Enhanced JSDoc/docstring parsing

#### 3. Novel Token-Saving Techniques
Help us discover new ways to do more with less:
- Alternative compression strategies
- Semantic code summarization
- Context-aware snippet extraction
- Cross-file relationship mapping
- Smart caching strategies

#### 4. Claude Code Integration
Improve the developer experience:
- Better hooks for auto-updates
- More intelligent skills
- Integration with other MCP servers
- Custom query DSL for power users

#### 5. Performance & Scalability
Make it faster for massive codebases:
- Parallel parsing optimizations
- Incremental update improvements
- Memory usage reduction
- Query performance tuning

### How to Get Started

1. Fork the repository
2. Check out the [Issues](https://github.com/pect0ral/claude-cartographer/issues) page
3. Pick an issue labeled `good-first-issue` or `help-wanted`
4. Submit a pull request

### Philosophy

Our goal is simple: **maximize the value of your Claude subscription by minimizing token waste**. Every feature should serve this mission. We value:
- Token efficiency over feature completeness
- Precision over verbosity
- Speed over perfection
- Simplicity over complexity

If you have ideas for novel ways to save tokens or enhance utility, we want to hear from you!

---

## License

MIT License - Copyright (c) 2025 Breach Craft

See [LICENSE](LICENSE) for details.

## Credits

Created by **Mike Piekarski** (mp@breachcraft.io)
Founder, [Breach Craft](https://breachcraft.io)

---

*Stop wasting tokens. Start mapping smarter.*
