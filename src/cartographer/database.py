"""
Codebase Cartographer - Token-optimized codebase mapping for Claude Code
Copyright (c) 2025 Breach Craft - Mike Piekarski <mp@breachcraft.io>
Licensed under MIT License

Token-optimized SQLite database for codebase mapping.
Implements 3-tier storage: compact (50 tokens), summary (200 tokens), full (compressed).
"""

import sqlite3
import lzma
import pickle
import time
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field, asdict
from collections import defaultdict


@dataclass
class ComponentData:
    """
    Complete component data structure.
    Supports code components (classes, functions) and templates.
    """
    # Required fields
    name: str
    type: str  # class, function, method, interface, struct, module, template, block, macro, route, middleware
    file_path: str
    line_start: int
    line_end: int = 0

    # Code structure
    signature: Optional[str] = None
    docstring: Optional[str] = None
    params: List[Dict[str, str]] = field(default_factory=list)
    props: List[Dict[str, str]] = field(default_factory=list)
    methods: List[str] = field(default_factory=list)
    decorators: List[str] = field(default_factory=list)
    modifiers: List[str] = field(default_factory=list)  # async, static, private, etc.
    parent: Optional[str] = None

    # Visibility and categorization
    exported: bool = False
    is_test: bool = False
    is_async: bool = False
    complexity_score: int = 0

    # Frontend-specific (React/Vue)
    hooks: List[str] = field(default_factory=list)  # useState, useEffect, etc.
    state: List[Dict[str, str]] = field(default_factory=list)
    renders_components: List[str] = field(default_factory=list)
    api_calls: List[Dict[str, str]] = field(default_factory=list)

    # Template-specific (Jinja2, EJS, Handlebars)
    blocks: List[Dict[str, Any]] = field(default_factory=list)
    includes: List[str] = field(default_factory=list)
    variables: List[str] = field(default_factory=list)
    extends: Optional[str] = None

    # Route/API-specific metadata (http_method, path, router, etc.)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)


class TokenOptimizedDatabase:
    """
    SQLite database optimized for token-efficient queries.

    Design principles:
    1. Three-tier storage: compact (~50 tokens), summary (~200 tokens), full (compressed)
    2. Aggressive indexing for sub-millisecond queries
    3. In-memory cache for hot data
    4. Query result caching
    5. Access tracking for adaptive optimization

    Usage:
        db = TokenOptimizedDatabase(Path('.claude-map/codebase.db'))
        db.add_component(component_data)
        results = db.query_compact('UserProfile')
        summary = db.query_summary('UserProfile')
        details = db.get_details('UserProfile')
    """

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.conn: Optional[sqlite3.Connection] = None
        self._init_connection()
        self._init_schema()

        # Performance caches
        self.hot_cache: Dict[str, Any] = {}
        self.query_cache: Dict[str, Tuple[str, float]] = {}
        self.cache_ttl = 300  # 5 minutes

        # Statistics
        self.cache_hits = 0
        self.cache_misses = 0
        self.query_count = 0
        self.total_query_time = 0.0

    def _init_connection(self):
        """Initialize database connection with optimizations."""
        self.conn = sqlite3.connect(
            str(self.db_path),
            check_same_thread=False,
            isolation_level=None  # Autocommit for performance
        )
        self.conn.row_factory = sqlite3.Row
        self._apply_optimizations()

    def _apply_optimizations(self):
        """Apply aggressive SQLite performance optimizations."""
        optimizations = [
            "PRAGMA journal_mode = WAL",           # Write-Ahead Logging
            "PRAGMA synchronous = NORMAL",         # Balanced durability/speed
            "PRAGMA cache_size = -128000",         # 128MB cache
            "PRAGMA temp_store = MEMORY",          # In-memory temp tables
            "PRAGMA mmap_size = 536870912",        # 512MB memory-mapped I/O
            "PRAGMA page_size = 8192",             # Larger pages
            "PRAGMA auto_vacuum = INCREMENTAL",    # Prevent DB bloat
            "PRAGMA foreign_keys = ON",            # Referential integrity
            "PRAGMA secure_delete = OFF",          # Faster deletes
            "PRAGMA locking_mode = NORMAL",        # Allow concurrent access
        ]

        for pragma in optimizations:
            try:
                self.conn.execute(pragma)
            except sqlite3.Error:
                pass  # Silently ignore unsupported pragmas

    def _init_schema(self):
        """Initialize database schema with comprehensive indexes."""

        schema_sql = """
        -- ================================================================
        -- COMPONENT INDEX - Three-tier token-optimized storage
        -- ================================================================
        CREATE TABLE IF NOT EXISTS component_index (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            -- Basic identity
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            file_path TEXT NOT NULL,
            line_start INTEGER NOT NULL,
            line_end INTEGER NOT NULL,

            -- Token-optimized representations
            compact TEXT NOT NULL,              -- Ultra-compact (~50 tokens)
            summary TEXT NOT NULL,              -- Detailed summary (~200 tokens)
            details BLOB,                       -- Compressed full data (LZMA)

            -- Token counts for budget management
            tokens_compact INTEGER DEFAULT 50,
            tokens_summary INTEGER DEFAULT 200,
            tokens_details INTEGER DEFAULT 1000,

            -- Quick filters
            is_exported BOOLEAN DEFAULT 0,
            is_test BOOLEAN DEFAULT 0,
            is_async BOOLEAN DEFAULT 0,
            complexity_score INTEGER DEFAULT 0,

            -- Performance tracking
            access_count INTEGER DEFAULT 0,
            last_accessed REAL,

            -- Timestamps
            created_at REAL DEFAULT (julianday('now')),
            updated_at REAL DEFAULT (julianday('now'))
        );

        -- ================================================================
        -- FULL-TEXT SEARCH - Lightning-fast component search
        -- ================================================================
        CREATE VIRTUAL TABLE IF NOT EXISTS component_search USING fts5(
            name,
            compact,
            summary,
            content=component_index,
            content_rowid=id,
            tokenize='porter unicode61'
        );

        -- Triggers to keep FTS in sync
        CREATE TRIGGER IF NOT EXISTS component_search_insert
        AFTER INSERT ON component_index BEGIN
            INSERT INTO component_search(rowid, name, compact, summary)
            VALUES (new.id, new.name, new.compact, new.summary);
        END;

        CREATE TRIGGER IF NOT EXISTS component_search_delete
        AFTER DELETE ON component_index BEGIN
            DELETE FROM component_search WHERE rowid = old.id;
        END;

        CREATE TRIGGER IF NOT EXISTS component_search_update
        AFTER UPDATE ON component_index BEGIN
            DELETE FROM component_search WHERE rowid = old.id;
            INSERT INTO component_search(rowid, name, compact, summary)
            VALUES (new.id, new.name, new.compact, new.summary);
        END;

        -- ================================================================
        -- RELATIONSHIPS - Component connections
        -- ================================================================
        CREATE TABLE IF NOT EXISTS relationships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_id INTEGER NOT NULL,
            to_id INTEGER,
            to_name TEXT NOT NULL,
            rel_type TEXT NOT NULL,  -- imports, calls, extends, implements, uses, renders
            confidence REAL DEFAULT 1.0,
            line_number INTEGER,

            FOREIGN KEY (from_id) REFERENCES component_index(id) ON DELETE CASCADE
        );

        -- ================================================================
        -- FILES - File-level metadata
        -- ================================================================
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT UNIQUE NOT NULL,
            language TEXT NOT NULL,
            hash TEXT NOT NULL,
            size INTEGER NOT NULL,
            lines INTEGER NOT NULL,
            component_count INTEGER DEFAULT 0,
            total_tokens INTEGER DEFAULT 0,
            last_modified REAL NOT NULL,
            last_indexed REAL DEFAULT (julianday('now'))
        );

        -- ================================================================
        -- QUERY CACHE - Materialized query results
        -- ================================================================
        CREATE TABLE IF NOT EXISTS query_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query_key TEXT UNIQUE NOT NULL,
            result_compact TEXT NOT NULL,
            result_tokens INTEGER NOT NULL,
            computed_at REAL DEFAULT (julianday('now')),
            hit_count INTEGER DEFAULT 0
        );

        -- ================================================================
        -- INDEXES - Aggressive indexing for performance
        -- ================================================================
        CREATE INDEX IF NOT EXISTS idx_component_name ON component_index(name);
        CREATE INDEX IF NOT EXISTS idx_component_type ON component_index(type);
        CREATE INDEX IF NOT EXISTS idx_component_file ON component_index(file_path);
        CREATE INDEX IF NOT EXISTS idx_component_exported ON component_index(is_exported);
        CREATE INDEX IF NOT EXISTS idx_component_access ON component_index(access_count DESC);
        CREATE INDEX IF NOT EXISTS idx_component_name_type ON component_index(name, type);
        CREATE INDEX IF NOT EXISTS idx_component_file_line ON component_index(file_path, line_start);

        CREATE INDEX IF NOT EXISTS idx_rel_from ON relationships(from_id);
        CREATE INDEX IF NOT EXISTS idx_rel_to ON relationships(to_id);
        CREATE INDEX IF NOT EXISTS idx_rel_to_name ON relationships(to_name);
        CREATE INDEX IF NOT EXISTS idx_rel_type ON relationships(rel_type);

        CREATE INDEX IF NOT EXISTS idx_files_path ON files(path);
        CREATE INDEX IF NOT EXISTS idx_files_lang ON files(language);

        CREATE INDEX IF NOT EXISTS idx_cache_key ON query_cache(query_key);
        """

        self.conn.executescript(schema_sql)

    # ================================================================
    # COMPACT REPRESENTATION GENERATION
    # ================================================================

    def _generate_compact(self, comp: ComponentData) -> str:
        """
        Generate ultra-compact representation (~50 tokens).
        Format: {type} {name}({key_info}) - {short_path}:{line}

        Examples:
            class UserProfile(p:3, m:5) - auth/user.py:15
            func authenticate(params:2, async) - auth/login.py:42
            template base.html(blocks:3, inc:2) - templates/base.html:1
        """
        short_path = self._short_path(comp.file_path)

        if comp.type in ('class', 'interface', 'struct'):
            props = len(comp.props) if comp.props else 0
            methods = len(comp.methods) if comp.methods else 0
            info = f"p:{props}, m:{methods}"
            if comp.exported:
                info += ", exp"

        elif comp.type in ('function', 'method'):
            params = len(comp.params) if comp.params else 0
            info = f"params:{params}"
            if comp.is_async:
                info += ", async"
            if comp.exported:
                info += ", exp"

        elif comp.type == 'template':
            blocks = len(comp.blocks) if comp.blocks else 0
            includes = len(comp.includes) if comp.includes else 0
            info = f"blocks:{blocks}, inc:{includes}"
            if comp.extends:
                info += f", ext:{comp.extends}"

        elif comp.type == 'component':  # React/Vue
            hooks = len(comp.hooks) if comp.hooks else 0
            renders = len(comp.renders_components) if comp.renders_components else 0
            info = f"hooks:{hooks}, renders:{renders}"
            if comp.exported:
                info += ", exp"
        else:
            info = "exp" if comp.exported else ""

        return f"{comp.type} {comp.name}({info}) - {short_path}:{comp.line_start}"

    def _generate_summary(self, comp: ComponentData) -> str:
        """
        Generate detailed summary (~200 tokens).
        Includes signature, key props/params, methods, and docstring excerpt.
        """
        lines = []

        # Header with type indicator
        export_marker = "[exported]" if comp.exported else ""
        async_marker = "[async]" if comp.is_async else ""
        lines.append(f"**{comp.name}** ({comp.type}) {export_marker} {async_marker}".strip())

        # Location
        lines.append(f"Location: {comp.file_path}:{comp.line_start}")

        # Signature (truncated if long)
        if comp.signature:
            sig = comp.signature[:150] + "..." if len(comp.signature) > 150 else comp.signature
            lines.append(f"Signature: `{sig}`")

        # Parent/inheritance
        if comp.parent:
            lines.append(f"Parent: {comp.parent}")
        if comp.extends:
            lines.append(f"Extends: {comp.extends}")

        # Parameters (first 5)
        if comp.params:
            param_strs = []
            for p in comp.params[:5]:
                ptype = p.get('type', 'any')
                param_strs.append(f"{p['name']}: {ptype}")
            if len(comp.params) > 5:
                param_strs.append(f"... +{len(comp.params) - 5} more")
            lines.append(f"Params: {', '.join(param_strs)}")

        # Properties (first 5)
        if comp.props:
            prop_strs = []
            for p in comp.props[:5]:
                ptype = p.get('type', 'any')
                prop_strs.append(f"{p['name']}: {ptype}")
            if len(comp.props) > 5:
                prop_strs.append(f"... +{len(comp.props) - 5} more")
            lines.append(f"Props: {', '.join(prop_strs)}")

        # Methods (first 5 public)
        if comp.methods:
            public_methods = [m for m in comp.methods if not m.startswith('_')][:5]
            if public_methods:
                method_str = ', '.join(public_methods)
                if len(comp.methods) > 5:
                    method_str += f" ... +{len(comp.methods) - 5} more"
                lines.append(f"Methods: {method_str}")

        # Hooks (React)
        if comp.hooks:
            lines.append(f"Hooks: {', '.join(comp.hooks[:5])}")

        # Renders (React)
        if comp.renders_components:
            lines.append(f"Renders: {', '.join(comp.renders_components[:5])}")

        # Template blocks
        if comp.blocks:
            block_names = [b.get('name', 'unnamed') for b in comp.blocks[:5]]
            lines.append(f"Blocks: {', '.join(block_names)}")

        # Includes
        if comp.includes:
            lines.append(f"Includes: {', '.join(comp.includes[:5])}")

        # Docstring (first 100 chars or first line)
        if comp.docstring:
            doc = comp.docstring.split('\n')[0][:100]
            if len(comp.docstring) > 100:
                doc += "..."
            lines.append(f"Doc: {doc}")

        # Decorators
        if comp.decorators:
            lines.append(f"Decorators: {', '.join(comp.decorators[:3])}")

        return '\n'.join(lines)

    def _compress_details(self, comp: ComponentData) -> bytes:
        """Compress full component data using LZMA."""
        data = comp.to_dict()
        pickled = pickle.dumps(data)
        return lzma.compress(pickled)

    def _decompress_details(self, data: bytes) -> Dict[str, Any]:
        """Decompress full component data."""
        decompressed = lzma.decompress(data)
        return pickle.loads(decompressed)

    def _short_path(self, file_path: str) -> str:
        """Shorten file path for compact representation."""
        parts = Path(file_path).parts
        if len(parts) <= 2:
            return file_path
        return '/'.join(parts[-2:])

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count (rough: 4 chars = 1 token)."""
        return max(len(text) // 4, 1)

    def _calculate_complexity(self, comp: ComponentData) -> int:
        """Calculate complexity score (0-100)."""
        score = 0

        # Parameters and properties
        param_count = len(comp.params) if comp.params else 0
        prop_count = len(comp.props) if comp.props else 0
        score += min((param_count + prop_count) * 5, 20)

        # Methods
        method_count = len(comp.methods) if comp.methods else 0
        score += min(method_count * 3, 25)

        # Lines of code
        loc = comp.line_end - comp.line_start + 1
        score += min(loc // 10, 25)

        # Frontend complexity
        renders = len(comp.renders_components) if comp.renders_components else 0
        score += min(renders * 2, 15)

        api_calls = len(comp.api_calls) if comp.api_calls else 0
        score += min(api_calls * 3, 15)

        return min(score, 100)

    # ================================================================
    # DATA OPERATIONS
    # ================================================================

    def add_component(self, comp: ComponentData) -> int:
        """
        Add or update a component in the database.
        Returns the component ID.
        """
        # Generate representations
        compact = self._generate_compact(comp)
        summary = self._generate_summary(comp)
        details = self._compress_details(comp)

        # Calculate metrics
        tokens_compact = self._estimate_tokens(compact)
        tokens_summary = self._estimate_tokens(summary)
        tokens_details = self._estimate_tokens(str(comp.to_dict()))
        complexity = self._calculate_complexity(comp)

        # Check if exists
        cursor = self.conn.execute(
            "SELECT id FROM component_index WHERE name = ? AND file_path = ? AND line_start = ?",
            (comp.name, comp.file_path, comp.line_start)
        )
        existing = cursor.fetchone()

        if existing:
            # Update existing
            self.conn.execute("""
                UPDATE component_index SET
                    type = ?, line_end = ?, compact = ?, summary = ?, details = ?,
                    tokens_compact = ?, tokens_summary = ?, tokens_details = ?,
                    is_exported = ?, is_test = ?, is_async = ?, complexity_score = ?,
                    updated_at = julianday('now')
                WHERE id = ?
            """, (
                comp.type, comp.line_end, compact, summary, details,
                tokens_compact, tokens_summary, tokens_details,
                comp.exported, comp.is_test, comp.is_async, complexity,
                existing['id']
            ))
            return existing['id']
        else:
            # Insert new
            cursor = self.conn.execute("""
                INSERT INTO component_index (
                    name, type, file_path, line_start, line_end,
                    compact, summary, details,
                    tokens_compact, tokens_summary, tokens_details,
                    is_exported, is_test, is_async, complexity_score
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                comp.name, comp.type, comp.file_path, comp.line_start, comp.line_end,
                compact, summary, details,
                tokens_compact, tokens_summary, tokens_details,
                comp.exported, comp.is_test, comp.is_async, complexity
            ))
            return cursor.lastrowid

    def add_relationship(
        self,
        from_id: int,
        to_name: str,
        rel_type: str,
        to_id: Optional[int] = None,
        confidence: float = 1.0,
        line_number: Optional[int] = None
    ):
        """Add a relationship between components."""
        self.conn.execute("""
            INSERT INTO relationships (from_id, to_id, to_name, rel_type, confidence, line_number)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (from_id, to_id, to_name, rel_type, confidence, line_number))

    def add_file(
        self,
        path: str,
        language: str,
        file_hash: str,
        size: int,
        lines: int,
        component_count: int = 0,
        total_tokens: int = 0,
        last_modified: float = None
    ):
        """Add or update file metadata."""
        if last_modified is None:
            last_modified = time.time()

        self.conn.execute("""
            INSERT OR REPLACE INTO files (
                path, language, hash, size, lines, component_count, total_tokens, last_modified
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (path, language, file_hash, size, lines, component_count, total_tokens, last_modified))

    def delete_file_components(self, file_path: str):
        """Delete all components from a file."""
        # Get component IDs first
        cursor = self.conn.execute(
            "SELECT id FROM component_index WHERE file_path = ?",
            (file_path,)
        )
        ids = [row['id'] for row in cursor.fetchall()]

        # Delete relationships
        if ids:
            placeholders = ','.join('?' * len(ids))
            self.conn.execute(
                f"DELETE FROM relationships WHERE from_id IN ({placeholders})",
                ids
            )

        # Delete components
        self.conn.execute("DELETE FROM component_index WHERE file_path = ?", (file_path,))

        # Delete file record
        self.conn.execute("DELETE FROM files WHERE path = ?", (file_path,))

    # ================================================================
    # QUERY OPERATIONS
    # ================================================================

    def query_compact(
        self,
        query: str,
        limit: int = 20,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Query components and return compact representations.
        Optimized for minimal token usage.

        Supports pagination via limit and offset parameters.
        Returns truncation info when results are limited.
        """
        start_time = time.time()
        self.query_count += 1

        # Check cache (include offset in key)
        cache_key = f"compact:{query}:{limit}:{offset}:{filters}"
        if cache_key in self.query_cache:
            result, cached_time = self.query_cache[cache_key]
            if time.time() - cached_time < self.cache_ttl:
                self.cache_hits += 1
                return result

        self.cache_misses += 1

        # Build base WHERE clause
        where_clause = "WHERE 1=1"
        params = []

        if filters:
            if filters.get('type'):
                where_clause += " AND type = ?"
                params.append(filters['type'])
            if filters.get('exported'):
                where_clause += " AND is_exported = 1"
            if filters.get('file_path'):
                where_clause += " AND file_path LIKE ?"
                params.append(f"%{filters['file_path']}%")

        # Name search
        if query:
            where_clause += " AND (name LIKE ? OR compact LIKE ?)"
            params.extend([f"%{query}%", f"%{query}%"])

        # Get total count first
        count_sql = f"SELECT COUNT(*) as total FROM component_index {where_clause}"
        cursor = self.conn.execute(count_sql, params)
        total_count = cursor.fetchone()['total']

        # Build query with pagination
        sql = f"SELECT compact, access_count FROM component_index {where_clause}"
        sql += " ORDER BY access_count DESC, name LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor = self.conn.execute(sql, params)
        rows = cursor.fetchall()

        # Build result with pagination info
        result_lines = []
        for row in rows:
            result_lines.append(row['compact'])

        if not result_lines:
            result = f"No components found matching '{query}'"
        else:
            result = '\n'.join(result_lines)

            # Add pagination info if there are more results
            shown_end = offset + len(result_lines)
            if total_count > shown_end:
                remaining = total_count - shown_end
                result += f"\n\n--- Results {offset + 1}-{shown_end} of {total_count} (use --offset {shown_end} for next {min(remaining, limit)}) ---"
            elif offset > 0:
                result += f"\n\n--- Results {offset + 1}-{shown_end} of {total_count} ---"

        # Cache result
        self.query_cache[cache_key] = (result, time.time())

        self.total_query_time += time.time() - start_time
        return result

    def query_summary(self, name: str) -> str:
        """Get summary representation for a component."""
        start_time = time.time()
        self.query_count += 1

        cursor = self.conn.execute("""
            SELECT id, summary FROM component_index WHERE name = ?
            ORDER BY access_count DESC LIMIT 1
        """, (name,))
        row = cursor.fetchone()

        if row:
            # Update access count
            self.conn.execute("""
                UPDATE component_index SET access_count = access_count + 1, last_accessed = ?
                WHERE id = ?
            """, (time.time(), row['id']))

            self.total_query_time += time.time() - start_time
            return row['summary']

        self.total_query_time += time.time() - start_time
        return f"Component '{name}' not found"

    def get_details(self, name: str) -> Optional[Dict[str, Any]]:
        """Get full decompressed details for a component."""
        cursor = self.conn.execute("""
            SELECT id, details FROM component_index WHERE name = ?
            ORDER BY access_count DESC LIMIT 1
        """, (name,))
        row = cursor.fetchone()

        if row and row['details']:
            # Update access count
            self.conn.execute("""
                UPDATE component_index SET access_count = access_count + 1, last_accessed = ?
                WHERE id = ?
            """, (time.time(), row['id']))

            return self._decompress_details(row['details'])

        return None

    def search_fts(self, query: str, limit: int = 20, offset: int = 0) -> str:
        """Full-text search across components with pagination support."""
        # Get total count first
        try:
            count_cursor = self.conn.execute("""
                SELECT COUNT(*) as total
                FROM component_search s
                JOIN component_index c ON s.rowid = c.id
                WHERE component_search MATCH ?
            """, (query,))
            total_count = count_cursor.fetchone()['total']
        except sqlite3.OperationalError:
            total_count = 0

        cursor = self.conn.execute("""
            SELECT c.compact, c.access_count
            FROM component_search s
            JOIN component_index c ON s.rowid = c.id
            WHERE component_search MATCH ?
            ORDER BY rank, c.access_count DESC
            LIMIT ? OFFSET ?
        """, (query, limit, offset))

        rows = cursor.fetchall()
        if rows:
            result = '\n'.join(row['compact'] for row in rows)

            # Add pagination info if there are more results
            shown_end = offset + len(rows)
            if total_count > shown_end:
                remaining = total_count - shown_end
                result += f"\n\n--- Results {offset + 1}-{shown_end} of {total_count} (use --offset {shown_end} for next {min(remaining, limit)}) ---"
            elif offset > 0:
                result += f"\n\n--- Results {offset + 1}-{shown_end} of {total_count} ---"

            return result
        return (
            f"No results for '{query}'\n\n"
            "Try:\n"
            "  - Use 'find <name>' for exact component name search\n"
            "  - Use 'show <file.py>' to see components in a file\n"
            "  - Use 'exports' to list all public components\n"
            "  - Check spelling or use partial names"
        )

    def get_call_chain(self, func_name: str, max_depth: int = 3) -> str:
        """
        Get call chain for a function using recursive CTE.
        Returns components that call this function, and what they call.
        """
        # Find the function
        cursor = self.conn.execute(
            "SELECT id, compact FROM component_index WHERE name = ? LIMIT 1",
            (func_name,)
        )
        root = cursor.fetchone()

        if not root:
            return f"Function '{func_name}' not found"

        lines = [f"Call chain for {func_name}:", f"  {root['compact']}", "", "Called by:"]

        # Find callers
        cursor = self.conn.execute("""
            SELECT DISTINCT c.compact
            FROM relationships r
            JOIN component_index c ON r.from_id = c.id
            WHERE r.to_name = ? AND r.rel_type = 'calls'
            LIMIT 10
        """, (func_name,))

        callers = cursor.fetchall()
        if callers:
            for row in callers:
                lines.append(f"  <- {row['compact']}")
        else:
            lines.append("  (no callers found)")

        lines.append("")
        lines.append("Calls:")

        # Find callees
        cursor = self.conn.execute("""
            SELECT DISTINCT r.to_name
            FROM relationships r
            JOIN component_index c ON r.from_id = c.id
            WHERE c.name = ? AND r.rel_type IN ('calls', 'uses')
            LIMIT 10
        """, (func_name,))

        callees = cursor.fetchall()
        if callees:
            for row in callees:
                lines.append(f"  -> {row['to_name']}")
        else:
            lines.append("  (no calls found)")

        return '\n'.join(lines)

    def get_dependencies(self, file_path: str) -> str:
        """Get dependencies for a file."""
        # Normalize path
        if not file_path.startswith('/'):
            file_path = f"%{file_path}"

        cursor = self.conn.execute("""
            SELECT DISTINCT r.to_name, r.rel_type
            FROM relationships r
            JOIN component_index c ON r.from_id = c.id
            WHERE c.file_path LIKE ?
            AND r.rel_type = 'imports'
            ORDER BY r.to_name
        """, (file_path,))

        rows = cursor.fetchall()

        if rows:
            lines = [f"Dependencies for {file_path}:", ""]
            for row in rows:
                lines.append(f"  - {row['to_name']}")
            return '\n'.join(lines)

        return f"No dependencies found for {file_path}"

    def get_file_components(self, file_path: str) -> str:
        """Get all components in a file."""
        cursor = self.conn.execute("""
            SELECT compact FROM component_index
            WHERE file_path LIKE ?
            ORDER BY line_start
        """, (f"%{file_path}",))

        rows = cursor.fetchall()

        if rows:
            lines = [f"Components in {file_path}:", ""]
            for row in rows:
                lines.append(f"  {row['compact']}")
            return '\n'.join(lines)

        return f"No components found in {file_path}"

    def list_exports(self, limit: int = 50, offset: int = 0) -> str:
        """List all exported components (public API) with pagination support."""
        # Get total count first
        cursor = self.conn.execute("SELECT COUNT(*) as total FROM component_index WHERE is_exported = 1")
        total_count = cursor.fetchone()['total']

        cursor = self.conn.execute("""
            SELECT compact FROM component_index
            WHERE is_exported = 1
            ORDER BY access_count DESC, name
            LIMIT ? OFFSET ?
        """, (limit, offset))

        rows = cursor.fetchall()

        if rows:
            lines = ["Exported Components (Public API):", ""]
            for row in rows:
                lines.append(f"  {row['compact']}")

            # Add pagination info if there are more results
            shown_end = offset + len(rows)
            if total_count > shown_end:
                remaining = total_count - shown_end
                lines.append("")
                lines.append(f"--- Results {offset + 1}-{shown_end} of {total_count} (use --offset {shown_end} for next {min(remaining, limit)}) ---")
            elif offset > 0:
                lines.append("")
                lines.append(f"--- Results {offset + 1}-{shown_end} of {total_count} ---")

            return '\n'.join(lines)

        return "No exported components found"

    # ================================================================
    # STATISTICS AND MAINTENANCE
    # ================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive database statistics."""
        stats = {}

        # Component counts
        cursor = self.conn.execute("SELECT COUNT(*) as cnt FROM component_index")
        stats['total_components'] = cursor.fetchone()['cnt']

        cursor = self.conn.execute("SELECT COUNT(*) as cnt FROM component_index WHERE is_exported = 1")
        stats['exported_count'] = cursor.fetchone()['cnt']

        cursor = self.conn.execute("SELECT COUNT(*) as cnt FROM component_index WHERE is_test = 1")
        stats['test_count'] = cursor.fetchone()['cnt']

        # File stats
        cursor = self.conn.execute("SELECT COUNT(*) as cnt, SUM(lines) as total_lines FROM files")
        row = cursor.fetchone()
        stats['total_files'] = row['cnt'] or 0
        stats['total_lines'] = row['total_lines'] or 0

        # By language
        cursor = self.conn.execute("""
            SELECT language, COUNT(*) as files, SUM(component_count) as components
            FROM files GROUP BY language ORDER BY files DESC
        """)
        stats['by_language'] = [
            {'language': r['language'], 'files': r['files'], 'components': r['components'] or 0}
            for r in cursor.fetchall()
        ]

        # Hot components
        cursor = self.conn.execute("""
            SELECT name, type, access_count FROM component_index
            WHERE access_count > 0
            ORDER BY access_count DESC LIMIT 10
        """)
        stats['hot_components'] = [
            {'name': r['name'], 'type': r['type'], 'access_count': r['access_count']}
            for r in cursor.fetchall()
        ]

        # Performance
        stats['performance'] = {
            'total_queries': self.query_count,
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'cache_hit_rate': f"{self.cache_hits / max(self.cache_hits + self.cache_misses, 1) * 100:.1f}%",
            'avg_query_time_ms': f"{self.total_query_time / max(self.query_count, 1) * 1000:.2f}",
        }

        # Database size
        try:
            stats['database_size_mb'] = f"{self.db_path.stat().st_size / 1024 / 1024:.2f}"
        except:
            stats['database_size_mb'] = "0.00"

        return stats

    def optimize(self):
        """Run database optimization."""
        self.conn.execute("VACUUM")
        self.conn.execute("ANALYZE")
        self.hot_cache.clear()
        self.query_cache.clear()

    def clear_cache(self):
        """Clear all caches."""
        self.hot_cache.clear()
        self.query_cache.clear()
        self.cache_hits = 0
        self.cache_misses = 0

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
