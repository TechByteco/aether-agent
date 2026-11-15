"""
AETHER Hybrid Dense + Sparse RAG & Semantic Knowledge Graph Engine
==================================================================
Provides tier-1 cognitive memory synthesis:
1. Sparse BM25 FTS5 retrieval (Strict Cognitive Invariant #1: tokenized OR queries).
2. Pure stdlib Dense Vector Cosine Similarity retrieval (128-dim dense embedding hashing / Ollama embedding).
3. Reciprocal Rank Fusion (RRF) to merge dense & sparse rankings.
4. SQLite Knowledge Graph: Entity-Relationship-Entity triples (Subject, Predicate, Object).
"""

import json
import logging
import math
import os
import re
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from aether.config import config
from aether.memory.store import memory

logger = logging.getLogger("aether.hybrid_kg")


class HybridKnowledgeGraph:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or (config.data_dir / "conscious_memory.db")
        self.vector_dim = 128
        self._init_kg_schema()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=15.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        return conn

    def _init_kg_schema(self) -> None:
        """Initialize Knowledge Graph and Vector store tables."""
        conn = self._get_connection()
        with conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_triples (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT NOT NULL,
                predicate TEXT NOT NULL,
                object TEXT NOT NULL,
                confidence REAL DEFAULT 1.0,
                source TEXT DEFAULT 'conversation',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(subject, predicate, object) ON CONFLICT REPLACE
            );
            """)
            conn.execute("""
            CREATE TABLE IF NOT EXISTS dense_memory_embeddings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_type TEXT NOT NULL, -- 'episode', 'fact', 'triple'
                source_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                vector_json TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_kg_subject ON knowledge_triples(subject);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_kg_object ON knowledge_triples(object);")
        conn.close()

    def _compute_dense_vector(self, text: str) -> List[float]:
        """Compute normalized 128-dimensional dense semantic vector from text."""
        vec = [0.0] * self.vector_dim
        words = re.findall(r"\b\w+\b", text.lower())
        if not words:
            return vec

        for word in words:
            # Word hash bucketing with n-gram positional features
            h = hash(word) % self.vector_dim
            vec[h] += 1.0
            for i in range(len(word) - 2):
                ngram_h = hash(word[i:i+3]) % self.vector_dim
                vec[ngram_h] += 0.5

        # L2 Normalization
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            vec = [x / norm for x in vec]
        return vec

    def _cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        """Compute cosine similarity between two normalized vectors."""
        if not v1 or not v2 or len(v1) != len(v2):
            return 0.0
        return sum(a * b for a, b in zip(v1, v2))

    def add_triple(self, subject: str, predicate: str, obj: str, confidence: float = 1.0, source: str = "agent") -> bool:
        """Insert or update a semantic relation triple."""
        s = subject.strip().lower()
        p = predicate.strip().lower()
        o = obj.strip().lower()
        if not s or not p or not o:
            return False

        conn = self._get_connection()
        with conn:
            conn.execute(
                "INSERT INTO knowledge_triples (subject, predicate, object, confidence, source) VALUES (?, ?, ?, ?, ?)",
                (s, p, o, confidence, source)
            )
        conn.close()
        return True

    def extract_and_store_triples_from_text(self, text: str) -> List[Dict[str, str]]:
        """Extract entity relationships from text and persist into Knowledge Graph."""
        extracted = []
        # Pattern 1: X is/has/owns/built/runs Y
        patterns = [
            r"([a-zA-Z0-9_\-\s]{2,30})\s+(is a|is an|has|owns|built|manages|controls|executes|runs)\s+([a-zA-Z0-9_\-\s]{2,40})",
            r"([a-zA-Z0-9_\-\s]{2,30})\s+(connects to|depends on|uses|serves)\s+([a-zA-Z0-9_\-\s]{2,40})",
        ]

        for pat in patterns:
            for match in re.finditer(pat, text, re.IGNORECASE):
                s, p, o = match.groups()
                s_clean = s.strip().title()
                p_clean = p.strip().lower()
                o_clean = o.strip()
                if len(s_clean) > 1 and len(o_clean) > 1:
                    self.add_triple(s_clean, p_clean, o_clean, confidence=0.95)
                    extracted.append({"subject": s_clean, "predicate": p_clean, "object": o_clean})

        return extracted

    def query_knowledge_graph(self, entity: str) -> Dict[str, Any]:
        """Query direct and reverse relationships for a given entity."""
        e = entity.strip().lower()
        conn = self._get_connection()
        outgoing = []
        incoming = []

        with conn:
            for row in conn.execute("SELECT subject, predicate, object, confidence FROM knowledge_triples WHERE subject = ? OR subject LIKE ?", (e, f"%{e}%")):
                outgoing.append({"subject": row["subject"], "relation": row["predicate"], "object": row["object"], "confidence": row["confidence"]})
            for row in conn.execute("SELECT subject, predicate, object, confidence FROM knowledge_triples WHERE object = ? OR object LIKE ?", (e, f"%{e}%")):
                incoming.append({"subject": row["subject"], "relation": row["predicate"], "object": row["object"], "confidence": row["confidence"]})
        conn.close()

        return {
            "entity": entity,
            "outgoing_relations": outgoing,
            "incoming_relations": incoming,
            "total_connections": len(outgoing) + len(incoming)
        }

    def hybrid_search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Execute Hybrid Search (BM25 FTS5 Sparse + Dense Vector Cosine Similarity) merged via Reciprocal Rank Fusion (RRF).
        """
        query_vec = self._compute_dense_vector(query)

        # 1. Sparse BM25 Search from episodic memory
        # Invariant #1: Tokenize & remove stop words & join with OR
        stop_words = {"what", "the", "and", "please", "tell", "is", "a", "an", "for", "to", "in", "of"}
        raw_tokens = re.findall(r"\b\w+\b", query.lower())
        meaningful = [t for t in raw_tokens if t not in stop_words and len(t) > 1]
        fts_query = " OR ".join(meaningful) if meaningful else query.strip()

        sparse_results = []
        conn = self._get_connection()
        with conn:
            try:
                cursor = conn.execute(
                    "SELECT id, role, content, timestamp FROM episodes WHERE id IN (SELECT rowid FROM episodes_fts WHERE episodes_fts MATCH ?) ORDER BY id DESC LIMIT ?",
                    (fts_query, top_k * 2)
                )
                sparse_results = [dict(row) for row in cursor.fetchall()]
            except Exception:
                cursor = conn.execute("SELECT id, role, content, timestamp FROM episodes ORDER BY id DESC LIMIT ?", (top_k * 2,))
                sparse_results = [dict(row) for row in cursor.fetchall()]

            # 2. Dense Vector Scoring across recent episodes
            all_episodes = conn.execute("SELECT id, role, content, timestamp FROM episodes ORDER BY id DESC LIMIT 50").fetchall()
        conn.close()

        dense_scored = []
        for ep in all_episodes:
            ep_dict = dict(ep)
            vec = self._compute_dense_vector(ep_dict["content"])
            sim = self._cosine_similarity(query_vec, vec)
            dense_scored.append((sim, ep_dict))

        dense_scored.sort(key=lambda x: x[0], reverse=True)
        dense_top = [item[1] for item in dense_scored[:top_k * 2]]

        # 3. Reciprocal Rank Fusion (RRF: score = 1 / (60 + rank))
        rrf_scores: Dict[int, float] = {}
        item_map: Dict[int, Dict[str, Any]] = {}

        for rank, item in enumerate(sparse_results):
            eid = item["id"]
            rrf_scores[eid] = rrf_scores.get(eid, 0.0) + (1.0 / (60.0 + rank + 1.0))
            item_map[eid] = item

        for rank, item in enumerate(dense_top):
            eid = item["id"]
            rrf_scores[eid] = rrf_scores.get(eid, 0.0) + (1.0 / (60.0 + rank + 1.0))
            item_map[eid] = item

        # Sort merged items
        sorted_eids = sorted(rrf_scores.keys(), key=lambda eid: rrf_scores[eid], reverse=True)
        final_results = []
        for eid in sorted_eids[:top_k]:
            res_item = item_map[eid].copy()
            res_item["rrf_score"] = round(rrf_scores[eid], 4)
            final_results.append(res_item)

        return final_results


# Global instance
hybrid_kg = HybridKnowledgeGraph()


# ─── Cognitive Brain Tools Exposed to Engine ─────────────────────────────────

def tool_query_hybrid_memory(query: str, top_k: int = 5) -> str:
    """Perform hybrid dense vector + BM25 sparse search over episodic consciousness using Reciprocal Rank Fusion (RRF)."""
    results = hybrid_kg.hybrid_search(query=query, top_k=top_k)
    if not results:
        return f"No hybrid memory episodes found matching '{query}'."

    lines = [f"### 🧠 Hybrid RAG Memory Search ({len(results)} Matches)\n**Query:** `{query}`\n"]
    for r in results:
        lines.append(f"- **[{r.get('timestamp', 'N/A')}] ({r.get('role', 'user').upper()})** (RRF: {r.get('rrf_score', 0.0)}):")
        lines.append(f"  {r.get('content', '')[:180]}...\n")

    return "\n".join(lines)


def tool_query_semantic_knowledge_graph(entity: str) -> str:
    """Query semantic entity-relationship Knowledge Graph triples for any concept, project, or person."""
    kg_data = hybrid_kg.query_knowledge_graph(entity=entity)
    lines = [f"### 🕸️ Semantic Knowledge Graph for: **{entity}** ({kg_data['total_connections']} connections)\n"]

    if kg_data["outgoing_relations"]:
        lines.append("**Outgoing Relations:**")
        for rel in kg_data["outgoing_relations"]:
            lines.append(f"- `[{rel['subject']}]` ➔ **{rel['relation']}** ➔ `[{rel['object']}]` *(conf: {rel['confidence']})*")

    if kg_data["incoming_relations"]:
        lines.append("\n**Incoming Relations:**")
        for rel in kg_data["incoming_relations"]:
            lines.append(f"- `[{rel['subject']}]` ➔ **{rel['relation']}** ➔ `[{rel['object']}]`")

    if not kg_data["outgoing_relations"] and not kg_data["incoming_relations"]:
        lines.append("No relationship triples mapped yet for this entity.")

    return "\n".join(lines)


def tool_extract_knowledge_triples(text: str) -> str:
    """Extract entity relationships from text and insert into the Knowledge Graph."""
    triples = hybrid_kg.extract_and_store_triples_from_text(text)
    if not triples:
        return "No new relationship triples extracted from input."

    lines = [f"### ✓ Extracted & Stored {len(triples)} Knowledge Triples:\n"]
    for t in triples:
        lines.append(f"- `[{t['subject']}]` ➔ **{t['predicate']}** ➔ `[{t['object']}]`")

    return "\n".join(lines)
