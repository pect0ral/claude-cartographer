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
# Clone the repository
git clone https://github.com/pect0ral/claude-cartographer.git
cd claude-cartographer

# ONE-COMMAND SETUP (installs + initializes + benchmarks)
./setup.sh /path/to/your/project

# Or step-by-step:
python install.py /path/to/your/project
cd /path/to/your/project
.claude-map/bin/claude-map init

# Start using
.claude-map/bin/claude-map find UserProfile              # Quick search
.claude-map/bin/claude-map query "find auth components"  # Natural language
.claude-map/bin/claude-map stats                         # View statistics
```

## Installation

### Option 1: Full Setup Script (Recommended)

The setup script installs, initializes the map, and runs a benchmark:

```bash
./setup.sh /path/to/your/project
```

### Option 2: Python Install

```bash
python install.py /path/to/your/project
```

**Install options:**

```bash
python install.py /path/to/project              # Fresh install
python install.py --update /path/to/project     # Update existing (preserves database)
python install.py --force /path/to/project      # Force fresh install
python install.py --uninstall /path/to/project  # Remove installation
python install.py --uninstall --keep-db         # Uninstall but backup database
```

### Option 3: Quick Install Script

```bash
./quick-install.sh /path/to/project
```

### Option 4: Manual Install

```bash
cd /path/to/project
python -m venv .claude-map/venv
.claude-map/venv/bin/pip install click watchdog tiktoken
# Copy src/cartographer to .claude-map/src/cartographer
# Create launcher scripts in .claude-map/bin/
```

> **Note:** Windows is not currently supported. macOS and Linux only.

### Post-Installation

After installation, initialize the codebase map:

```bash
cd /path/to/your/project
.claude-map/bin/claude-map init              # Standard initialization
.claude-map/bin/claude-map init -w 8         # Use 8 worker threads (faster)
.claude-map/bin/claude-map init --watch      # Initialize and start watching
```

## CLI Commands

### Quick Reference

| Command | Purpose | Key Options |
|---------|---------|-------------|
| `find <name>` | Quick name search | `-l/--limit`, `-o/--offset`, `-q/--quiet` |
| `query "<text>"` | Natural language search | `-t/--max-tokens`, `-o/--offset`, `-f/--format`, `-q/--quiet` |
| `show <file>` | File structure | `-q/--quiet` |
| `exports` | List public API | `-l/--limit`, `-o/--offset`, `-q/--quiet` |
| `stats` | Database stats | `-f/--format` |
| `session` | Token savings | `-v/--verbose`, `--lifetime`, `-f/--format` |
| `init [path]` | Initialize mapping | `-w/--workers`, `--no-mp`, `--watch` |
| `update` | Incremental update | `-w/--workers`, `--no-mp` |
| `watch` | Auto-update | `-d/--debounce` |
| `optimize` | DB maintenance | (none) |
| `benchmark` | Performance test | `--verbose/--quiet`, `-f/--format` |

> **Note:** Commands with `-o/--offset` support pagination for large result sets.

### Primary Commands

#### `find` - Quick Component Search
The fastest way to locate functions, classes, or components by name.

```bash
claude-map find <name>           # Search by name
claude-map find <name> -l 50     # Return up to 50 results (default: 20)
claude-map find <name> -o 20     # Skip first 20 results (pagination)
claude-map find <name> -q        # Quiet mode (suppress token stats)
```

#### `query` - Natural Language Search
Complex searches with relationship understanding and token budgeting.

```bash
claude-map query "<text>"              # Natural language query
claude-map query "<text>" -t 5000      # Limit to 5000 tokens (default: 10000)
claude-map query "<text>" -t 20000     # More results for large codebases
claude-map query "<text>" -o 50        # Skip first 50 results (pagination)
claude-map query "<text>" -f json      # Output as JSON
claude-map query "<text>" -q           # Quiet mode
```

**Query patterns supported:**
- `"find UserProfile"` - locate component by name
- `"dependencies of auth.py"` - file dependencies
- `"what calls authenticate"` - call chain analysis
- `"exports"` - list public API
- `"overview"` - codebase summary

**Fallback:** Unrecognized patterns do full-text search on component names.

**Token limit guidance:**
- `-t 2000` - Simple lookups, just a few results needed
- `-t 10000` (default) - Broader exploration
- `-t 20000` - Comprehensive results across large codebases

### Pagination

When results are truncated, the output shows pagination info:
```
--- Results 1-20 of 150 (use --offset 20 for next 20) ---
```

To get the next page of results, use the `--offset` / `-o` option:
```bash
claude-map find User -o 20       # Get results 21-40
claude-map query "auth" -o 50    # Get results 51+
claude-map exports -o 100        # Get exports 101+
```

Pagination is available on: `find`, `query`, and `exports` commands.

#### `show` - File Structure Overview
Understand a file's structure without reading the entire file.

```bash
claude-map show <file_path>      # Show all components in a file
claude-map show <file_path> -q   # Quiet mode
```

### Utility Commands

#### `exports` - List Public API
```bash
claude-map exports               # List all exported/public components
claude-map exports -l 100        # Return up to 100 results (default: 50)
claude-map exports -o 50         # Skip first 50 results (pagination)
claude-map exports -q            # Quiet mode
```

#### `stats` - Database Statistics
```bash
claude-map stats                 # Show mapping statistics
claude-map stats -f json         # Output as JSON
```

#### `session` - Token Savings Report
```bash
claude-map session               # Current session stats
claude-map session -v            # Verbose (show recent queries)
claude-map session --lifetime    # All-time statistics
claude-map session -f json       # Output as JSON
```

### Maintenance Commands

#### `init` - Initialize Mapping
```bash
claude-map init                  # Initialize in current directory
claude-map init /path/to/project # Initialize specific path
claude-map init -w 8             # Use 8 worker threads
claude-map init --no-mp          # Disable multiprocessing
claude-map init --watch          # Watch for changes after init
```

#### `update` - Incremental Update
```bash
claude-map update                # Update changed files only
claude-map update -w 8           # Use 8 worker threads
claude-map update --no-mp        # Disable multiprocessing
```

#### `watch` - Auto-Update on Changes
```bash
claude-map watch                 # Watch and auto-update
claude-map watch -d 1.0          # 1 second debounce (default: 0.5)
```

#### `optimize` - Database Optimization
```bash
claude-map optimize              # VACUUM and ANALYZE the database
```

#### `benchmark` - Performance Testing
```bash
claude-map benchmark             # Compare cartographer vs traditional approach
claude-map benchmark --quiet     # Less verbose output
claude-map benchmark -f json     # Output as JSON
```

## Python API

```python
from cartographer import ClaudeCodeIntegration

# Initialize
integration = ClaudeCodeIntegration('/path/to/project')

# Token-budgeted queries (default: 10000 tokens)
context = integration.get_context("find authentication")

# With custom token limits
context = integration.get_context("find authentication", max_tokens=2000)   # Minimal
context = integration.get_context("show all exports", max_tokens=20000)     # Comprehensive

# With pagination (offset parameter)
context = integration.get_context("find User", offset=20)  # Skip first 20 results

# Quick operations
result = integration.quick_find('UserProfile')             # Find by name
result = integration.quick_find('User', limit=50)          # With result limit
result = integration.quick_find('User', limit=20, offset=20)  # Pagination
summary = integration.get_file_summary('src/auth.py')      # File structure
exports = integration.list_exports(limit=100)              # Public API
exports = integration.list_exports(limit=50, offset=50)    # Pagination
stats = integration.get_stats()                            # Database stats

# Session tracking
session_summary = integration.get_session_summary()        # Current session
lifetime_stats = integration.get_lifetime_stats()          # All-time stats

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

The installer adds comprehensive instructions to your project's `CLAUDE.md` file that teach Claude how to use the cartographer effectively. The injected documentation includes:

- **Complete command reference** with all options and flags
- **"When to use" guidance** for each command
- **Token limit guidance** for optimizing queries
- **Query examples** for natural language searches
- **Absolute paths** to the `claude-map` binary (automatically configured per-installation)

**Example of what gets added:**

```markdown
## CRITICAL: Use Codebase Cartographer First

**BEFORE using Read, Grep, or Glob tools to explore code, use the cartographer.**

### Primary Commands

#### `find` - Quick Component Search (Use Most Often)
/path/to/project/.claude-map/bin/claude-map find <name>      # Search by name
/path/to/project/.claude-map/bin/claude-map find <name> -l 50 # Up to 50 results

#### `query` - Natural Language Search
/path/to/project/.claude-map/bin/claude-map query "<text>"         # Natural language
/path/to/project/.claude-map/bin/claude-map query "<text>" -t 5000 # Token-limited

**Token limit guidance:**
- Use `-t 2000` for simple lookups
- Use default (10000) for broader exploration
- Use `-t 20000` for comprehensive results

### Command Reference
| Command | Purpose | Key Options |
|---------|---------|-------------|
| find    | Quick name search | -l/--limit, -q/--quiet |
| query   | Natural language  | -t/--max-tokens, -f/--format |
... (full table with all 11 commands)
```

**Key behaviors:**
- Claude queries the cartographer **first** before using Read, Grep, or Glob
- If the cartographer returns no results, Claude **falls back** to native tools
- The section is wrapped in `<!-- CARTOGRAPHER_START -->` / `<!-- CARTOGRAPHER_END -->` markers for easy updates
- Running `python install.py --update` refreshes the documentation while preserving your other CLAUDE.md content

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
