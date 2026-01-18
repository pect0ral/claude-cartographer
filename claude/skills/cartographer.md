---
name: cartographer
description: Token-optimized codebase exploration using the Codebase Cartographer. Use this skill when exploring code structure, finding components, checking dependencies, or understanding a codebase. Saves 95%+ tokens compared to reading full files.
---

# Codebase Cartographer

Query the codebase map before reading files to save tokens.

## When to Use

- Finding components, classes, or functions by name
- Understanding file dependencies
- Getting codebase structure overview
- Finding exported/public APIs
- Tracing call chains

## Commands

### `find` - Quick Component Search (Use Most Often)
```bash
.claude-map/bin/claude-map find <name>        # Search by name
.claude-map/bin/claude-map find <name> -l 50  # Return up to 50 results (default: 20)
.claude-map/bin/claude-map find <name> -o 20  # Skip first 20 (pagination)
.claude-map/bin/claude-map find <name> -q     # Quiet mode (suppress token stats)
```

### `query` - Pattern-Based Search
```bash
.claude-map/bin/claude-map query "<text>"          # Pattern-based query
.claude-map/bin/claude-map query "<text>" -t 5000  # Limit to 5000 tokens (default: 10000)
.claude-map/bin/claude-map query "<text>" -o 50    # Skip first 50 results (pagination)
.claude-map/bin/claude-map query "<text>" -q       # Quiet mode
```

### `show` - File Structure
```bash
.claude-map/bin/claude-map show <file_path>   # Show all components in a file
```

### `exports` - Public API
```bash
.claude-map/bin/claude-map exports            # List all exported/public components
.claude-map/bin/claude-map exports -l 100     # Return up to 100 results
.claude-map/bin/claude-map exports -o 50      # Skip first 50 (pagination)
```

### Other Commands
```bash
.claude-map/bin/claude-map stats              # Database statistics
.claude-map/bin/claude-map update             # Update map after changes
```

## Query Patterns

| Pattern | Example |
|---------|---------|
| Find by name | `find UserProfile` |
| Dependencies | `dependencies of auth.py` |
| Call chain | `what calls authenticate` |
| File components | `show src/user.py` |
| Overview | `overview` |
| Exports | `exports` |

**Fallback:** Unrecognized patterns do full-text search on component names.

## Pagination

When results are truncated, output shows:
```
--- Results 1-20 of 150 (use --offset 20 for next 20) ---
```

Use `--offset` / `-o` to get the next page.

## Workflow

1. **Search first**: `find ComponentName` returns location in ~50 tokens
2. **Read targeted**: Use line numbers from search to read only needed code
3. **Check dependencies**: Before modifying, check what calls/imports the code

## Output Format

Compact (~50 tokens per result):
```
class UserProfile(p:3, m:5) - auth/user.py:15
func authenticate(params:2, async) - auth/login.py:42
```

## Token Savings

| Operation | Traditional | Optimized | Savings |
|-----------|-------------|-----------|---------|
| Find component | 15,000 | 200 | 98.7% |
| Dependencies | 25,000 | 500 | 98.0% |
| List exports | 30,000 | 1,000 | 96.7% |
