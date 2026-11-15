"""
Conscious Persistent Disk-Backed Memory Store
Stores episodic stream, structured facts, and semantic insights using SQLite FTS5.
Zero persistent RAM footprint; data lives directly on disk in WAL mode.
"""

import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

from aether.config import config


class MemoryStore:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or str(config.data_dir / "conscious_memory.db")
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        # WAL mode: ultra-fast, zero memory bloat, safe concurrent reads/writes
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            # 1. Episodic journal of all conversations and events
            conn.execute("""
            CREATE TABLE IF NOT EXISTS episodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                session_id TEXT DEFAULT 'default'
            );
            """)

            # 2. Structured knowledge graph of facts about user, system, preferences
            conn.execute("""
            CREATE TABLE IF NOT EXISTS facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity TEXT NOT NULL,
                attribute TEXT NOT NULL,
                value TEXT NOT NULL,
                confidence REAL DEFAULT 1.0,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(entity, attribute) ON CONFLICT REPLACE
            );
            """)

            # 3. Higher-order consolidated insights
            conn.execute("""
            CREATE TABLE IF NOT EXISTS insights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                category TEXT NOT NULL,
                insight_text TEXT NOT NULL
            );
            """)

            # 4. FTS5 Full-Text Search index for episodic recall
            conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS fts_episodes USING fts5(
                content,
                content='episodes',
                content_rowid='id',
                tokenize='porter'
            );
            """)

            # Triggers to keep episodic FTS table in sync
            conn.execute("""
            CREATE TRIGGER IF NOT EXISTS episodes_ai AFTER INSERT ON episodes BEGIN
                INSERT INTO fts_episodes(rowid, content) VALUES (new.id, new.content);
            END;
            """)
            conn.execute("""
            CREATE TRIGGER IF NOT EXISTS episodes_ad AFTER DELETE ON episodes BEGIN
                INSERT INTO fts_episodes(fts_episodes, rowid, content) VALUES('delete', old.id, old.content);
            END;
            """)

            # 5. Procedural memory (Heuristics & Learned Rules - ExpeL pattern)
            conn.execute("""
            CREATE TABLE IF NOT EXISTS heuristic_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT DEFAULT 'general',
                rule TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            """)
            conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS fts_heuristic_rules USING fts5(
                rule,
                content='heuristic_rules',
                content_rowid='id',
                tokenize='porter'
            );
            """)
            conn.execute("""
            CREATE TRIGGER IF NOT EXISTS heuristics_ai AFTER INSERT ON heuristic_rules BEGIN
                INSERT INTO fts_heuristic_rules(rowid, rule) VALUES (new.id, new.rule);
            END;
            """)
            conn.execute("""
            CREATE TRIGGER IF NOT EXISTS heuristics_ad AFTER DELETE ON heuristic_rules BEGIN
                INSERT INTO fts_heuristic_rules(fts_heuristic_rules, rowid, rule) VALUES('delete', old.id, old.rule);
            END;
            """)

    def add_episode(
        self,
        role: str = "user",
        content: str = "",
        session_id: str = "default",
        user_message: Optional[str] = None,
        assistant_response: Optional[str] = None,
        tools_used: Optional[List[str]] = None,
    ) -> int:
        """Record an event or conversation turn into the episodic stream."""
        if user_message and assistant_response:
            self.add_episode(role="user", content=user_message, session_id=session_id)
            return self.add_episode(role="assistant", content=assistant_response, session_id=session_id)

        final_content = (content or user_message or assistant_response or "").strip()
        if not final_content:
            return 0

        with self._get_connection() as conn:
            cur = conn.execute(
                "INSERT INTO episodes (role, content, session_id) VALUES (?, ?, ?)",
                (role, final_content, session_id),
            )
            return cur.lastrowid or 0

    def remember_fact(self, entity: str, attribute: str, value: str) -> None:
        """Store or update an atomic fact into the long-term semantic knowledge graph."""
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO facts (entity, attribute, value, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(entity, attribute) DO UPDATE SET
                    value=excluded.value,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (entity.strip().lower(), attribute.strip().lower(), value.strip()),
            )

    def recall_facts(self, entity: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch all facts or facts pertaining to a specific entity."""
        with self._get_connection() as conn:
            if entity:
                cur = conn.execute(
                    "SELECT entity, attribute, value, updated_at FROM facts WHERE entity = ? ORDER BY attribute",
                    (entity.strip().lower(),),
                )
            else:
                cur = conn.execute(
                    "SELECT entity, attribute, value, updated_at FROM facts ORDER BY entity, attribute"
                )
            return [dict(row) for row in cur.fetchall()]

    def search_episodes(self, query: str, limit: int = 6) -> List[Dict[str, Any]]:
        """
        Search episodic history using FTS5 full-text indexing.
        Extracts key content terms with stop-word elimination and OR-expansion so
        lengthy instructions, multiline paragraphs, or conversational commands
        retrieve accurately without failing on multi-token strict AND constraints.
        """
        raw_tokens = [w.strip() for w in "".join(c if c.isalnum() else " " for c in query).lower().split()]
        stop_words = {
            "a", "an", "the", "and", "or", "is", "it", "in", "on", "to", "for", "of",
            "with", "at", "by", "from", "this", "that", "me", "my", "you", "your", "what",
            "tell", "please", "right", "now", "can", "could", "would", "how", "why", "are",
            "i", "we", "be", "do", "does", "did", "have", "has", "had", "so", "if", "then"
        }
        meaningful = [w for w in raw_tokens if w not in stop_words and len(w) > 1]
        
        # Build query: try meaningful terms with OR, fallback to raw tokens, fallback to raw query
        fts_query = " OR ".join(meaningful[:10]) if meaningful else " OR ".join(raw_tokens[:5])
        if not fts_query:
            return []

        with self._get_connection() as conn:
            try:
                cur = conn.execute(
                    """
                    SELECT e.id, e.timestamp, e.role, e.content
                    FROM fts_episodes f
                    JOIN episodes e ON f.rowid = e.id
                    WHERE fts_episodes MATCH ?
                    ORDER BY rank
                    LIMIT ?
                    """,
                    (fts_query, limit),
                )
                results = [dict(row) for row in cur.fetchall()]
                if results:
                    return results
            except sqlite3.OperationalError:
                pass

            # Fallback to wildcard LIKE for primary keywords
            keyword = meaningful[0] if meaningful else (raw_tokens[0] if raw_tokens else "")
            if not keyword:
                return []
            cur = conn.execute(
                """
                SELECT id, timestamp, role, content
                FROM episodes
                WHERE content LIKE ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (f"%{keyword}%", limit),
            )
            return [dict(row) for row in cur.fetchall()]

    def add_heuristic_rule(self, rule: str = "", domain: str = "general", rule_text: Optional[str] = None, source: Optional[str] = None) -> int:
        """Store an operational rule or self-improvement insight (ExpeL/Reflexion pattern)."""
        final_rule = (rule_text or rule).strip()
        if not final_rule:
            return 0
        with self._get_connection() as conn:
            cur = conn.execute(
                "INSERT INTO heuristic_rules (domain, rule) VALUES (?, ?)",
                (domain.strip().lower(), final_rule),
            )
            return cur.lastrowid or 0

    def recall_heuristic_rules(self, query: str, limit: int = 4) -> List[str]:
        """
        Recall procedural rules and self-corrections relevant to a given task.
        Tokenizes query, strips conversational stop-words, and joins with OR for FTS5 BM25 scoring.
        """
        raw_tokens = [w.strip() for w in "".join(c if c.isalnum() else " " for c in query).lower().split()]
        stop_words = {
            "a", "an", "the", "and", "or", "is", "it", "in", "on", "to", "for", "of",
            "with", "at", "by", "from", "this", "that", "me", "my", "you", "your", "what",
            "tell", "please", "right", "now", "can", "could", "would", "how", "why", "are",
            "i", "we", "be", "do", "does", "did", "have", "has", "had", "so", "if", "then"
        }
        meaningful = [w for w in raw_tokens if w not in stop_words and len(w) > 1]
        fts_query = " OR ".join(meaningful[:8]) if meaningful else " OR ".join(raw_tokens[:4])

        if not fts_query:
            with self._get_connection() as conn:
                rows = conn.execute("SELECT rule FROM heuristic_rules ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
                return [r[0] for r in rows]

        with self._get_connection() as conn:
            try:
                cur = conn.execute(
                    """
                    SELECT h.rule
                    FROM fts_heuristic_rules f
                    JOIN heuristic_rules h ON f.rowid = h.id
                    WHERE fts_heuristic_rules MATCH ?
                    ORDER BY rank
                    LIMIT ?
                    """,
                    (fts_query, limit),
                )
                rules = [r[0] for r in cur.fetchall()]
                if rules:
                    return rules
            except sqlite3.OperationalError:
                pass

            # Fallback to recent rules if match yields nothing
            cur = conn.execute(
                "SELECT rule FROM heuristic_rules ORDER BY id DESC LIMIT ?",
                (limit,)
            )
            return [r[0] for r in cur.fetchall()]

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for a text string using 4 chars per token rule of thumb."""
        return max(1, len(text) // 4) if text else 0

    def get_recent_episodes(self, limit: int = 6) -> List[Dict[str, Any]]:
        """Fetch the most recent turns for immediate conversational flow."""
        with self._get_connection() as conn:
            cur = conn.execute(
                "SELECT id, role, content, timestamp FROM episodes ORDER BY id DESC LIMIT ?",
                (limit,),
            )
            rows = [dict(row) for row in cur.fetchall()]
            rows.reverse()
            return rows

    def compact_episodes(self, keep_recent: int = 4, watermark_tokens: int = 3500) -> Optional[str]:
        """
        Hierarchical context compaction (MemGPT/CoALA pattern):
        If raw episode buffer exceeds watermark_tokens, summarize older turns
        and consolidate them into a structured insight or summary episode,
        preserving the most recent N turns raw for immediate conversational flow.
        """
        recent = self.get_recent_episodes(limit=20)
        if len(recent) <= keep_recent:
            return None

        total_tokens = sum(self.estimate_tokens(e["content"]) for e in recent)
        if total_tokens < watermark_tokens:
            return None

        # Turns to compact: everything except the last keep_recent turns
        to_compact = recent[:-keep_recent]
        summary_lines = []
        for turn in to_compact:
            snippet = turn["content"][:180].replace("\n", " ")
            summary_lines.append(f"- {turn['role'].upper()}: {snippet}")

        summary_text = "Prior conversation summary:\n" + "\n".join(summary_lines)
        
        with self._get_connection() as conn:
            # Store consolidated insight
            conn.execute(
                "INSERT INTO insights (category, insight_text) VALUES (?, ?)",
                ("dialogue_summary", summary_text[:1000]),
            )
            # Remove compacted raw episodes to free context space
            oldest_id = to_compact[-1]["id"]
            conn.execute("DELETE FROM episodes WHERE id <= ?", (oldest_id,))
            # Insert the compact summary marker
            conn.execute(
                "INSERT INTO episodes (role, content, session_id) VALUES (?, ?, ?)",
                ("system", f"[Context Summary: {len(to_compact)} turns consolidated]\n{summary_text[:800]}", "compacted"),
            )

        return summary_text

    def get_memory_stats(self) -> Dict[str, Any]:
        """Return memory size, counts, and estimated active context tokens."""
        with self._get_connection() as conn:
            ep_count = conn.execute("SELECT COUNT(*) FROM episodes").fetchone()[0]
            fact_count = conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
            insight_count = conn.execute("SELECT COUNT(*) FROM insights").fetchone()[0]
            rule_count = conn.execute("SELECT COUNT(*) FROM heuristic_rules").fetchone()[0]
            recent_texts = conn.execute("SELECT content FROM episodes ORDER BY id DESC LIMIT 12").fetchall()

        active_tokens = sum(self.estimate_tokens(r[0]) for r in recent_texts)
        db_file = config.data_dir / "conscious_memory.db"
        size_kb = round(db_file.stat().st_size / 1024, 2) if db_file.exists() else 0
        return {
            "episodes": ep_count,
            "facts": fact_count,
            "insights": insight_count,
            "heuristics": rule_count,
            "active_tokens": active_tokens,
            "disk_size_kb": size_kb,
        }


memory = MemoryStore()
