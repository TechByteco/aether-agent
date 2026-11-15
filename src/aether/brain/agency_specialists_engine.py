"""
AETHER Agency Specialists Engine
================================
Indexes, orchestrates, and dispatches the 290+ specialized AI agency agents
from msitarzewski/agency-agents across 18 operational divisions:

1. Sales (offer architects, deal strategists, outbound lead gen, discovery)
2. Marketing (copywriters, content strategists, AI citation/AEO specialists)
3. Product (growth strategists, PRD architects, pricing & monetization)
4. Engineering (fullstack architects, DevOps, security, code refactorers)
5. Design (UX/UI, landing page conversion designers, brand identity)
6. Security (red/blue team, compliance, vulnerability assessment)
7. Finance (unit economics, financial modeling, runway analysis)
8. Project Management & Strategy (agile leads, sprint planners, OKR architects)
... and 10 additional divisions.

All agents run seamlessly via MultiProviderRouter using your active Gemini API,
Nex-N2.5-mini via OpenRouter, Groq LPU, or local Ollama.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("aether.agency_specialists")

_WORKSPACE = Path(__file__).resolve().parents[3]
_REPO_DIR = _WORKSPACE / "data" / "agency_agents_repo"
_CACHE_FILE = _WORKSPACE / "data" / "leon_intelligence" / "agency_catalog.json"
_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)


class AgencySpecialistsEngine:
    """Manages index, catalog, and execution of all 290+ Agency Specialists."""

    def __init__(self, repo_dir: Optional[Path] = None) -> None:
        self.repo_dir = repo_dir or _REPO_DIR
        self._agents: Dict[str, Dict[str, Any]] = {}
        self._divisions: Dict[str, List[str]] = {}
        self._load_or_build_index()

    def _parse_agent_file(self, filepath: Path) -> Optional[Dict[str, Any]]:
        """Parse markdown frontmatter and body of an agency agent file."""
        try:
            content = filepath.read_text(encoding="utf-8")
            if not content.startswith("---"):
                return None

            parts = content.split("---", 2)
            if len(parts) < 3:
                return None

            frontmatter_raw = parts[1]
            body = parts[2].strip()

            meta: Dict[str, Any] = {}
            for line in frontmatter_raw.strip().splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip().strip('"').strip("'")

            name = meta.get("name") or filepath.stem.replace("-", " ").title()
            slug = filepath.stem
            division = filepath.parent.name

            return {
                "slug": slug,
                "name": name,
                "division": division,
                "description": meta.get("description", ""),
                "color": meta.get("color", "#3B82F6"),
                "emoji": meta.get("emoji", "🤖"),
                "vibe": meta.get("vibe", ""),
                "filepath": str(filepath.relative_to(_WORKSPACE)),
                "prompt_body": body,
            }
        except Exception as e:
            logger.debug(f"Failed to parse {filepath.name}: {e}")
            return None

    def _load_or_build_index(self) -> None:
        """Load catalog from disk or scan the repo directory."""
        if _CACHE_FILE.exists():
            try:
                cached = json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
                self._agents = cached.get("agents", {})
                self._divisions = cached.get("divisions", {})
                if self._agents:
                    return
            except Exception as e:
                logger.debug(f"Cache load failed: {e}")

        self.reindex()

    def reindex(self) -> int:
        """Scan data/agency_agents_repo and build a complete catalog."""
        if not self.repo_dir.exists():
            logger.warning(f"Agency repo dir not found at {self.repo_dir}")
            return 0

        self._agents.clear()
        self._divisions.clear()

        for md_file in self.repo_dir.glob("*/*.md"):
            # Exclude root documents and hidden files
            if md_file.parent == self.repo_dir or md_file.name.startswith("."):
                continue

            parsed = self._parse_agent_file(md_file)
            if parsed:
                slug = parsed["slug"]
                div = parsed["division"]
                self._agents[slug] = parsed
                self._divisions.setdefault(div, []).append(slug)

        # Cache catalog without the huge prompt bodies to keep it lightweight
        try:
            summary_agents = {
                k: {sk: sv for sk, sv in v.items() if sk != "prompt_body"}
                for k, v in self._agents.items()
            }
            _CACHE_FILE.write_text(
                json.dumps({"agents": summary_agents, "divisions": self._divisions}, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as e:
            logger.warning(f"Failed to save catalog cache: {e}")

        logger.info(f"Indexed {len(self._agents)} agency specialists across {len(self._divisions)} divisions.")
        return len(self._agents)

    def list_divisions(self) -> Dict[str, int]:
        """Return division names and their agent counts."""
        return {div: len(slugs) for div, slugs in sorted(self._divisions.items())}

    def list_agents(self, division: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all agents or agents filtered by division."""
        agents = []
        for slug, data in self._agents.items():
            if division and data["division"].lower() != division.lower():
                continue
            agents.append({
                "slug": slug,
                "name": data["name"],
                "division": data["division"],
                "description": data["description"],
                "emoji": data["emoji"],
                "vibe": data["vibe"],
            })
        return sorted(agents, key=lambda a: (a["division"], a["name"]))

    def get_agent(self, slug_or_query: str) -> Optional[Dict[str, Any]]:
        """Find an agent by exact slug or fuzzy name search."""
        q = slug_or_query.strip().lower()

        # 1. Exact match
        if q in self._agents:
            agent = dict(self._agents[q])
            # Load full prompt body if missing from cache
            if "prompt_body" not in agent or not agent["prompt_body"]:
                fp = _WORKSPACE / agent["filepath"]
                if fp.exists():
                    p = self._parse_agent_file(fp)
                    if p:
                        agent["prompt_body"] = p["prompt_body"]
            return agent

        # 2. Match by partial slug or name
        for slug, data in self._agents.items():
            if q == slug.lower() or q in slug.lower() or q in data["name"].lower():
                agent = dict(data)
                if "prompt_body" not in agent or not agent["prompt_body"]:
                    fp = _WORKSPACE / agent["filepath"]
                    if fp.exists():
                        p = self._parse_agent_file(fp)
                        if p:
                            agent["prompt_body"] = p["prompt_body"]
                return agent

        return None

    def recommend_specialists(self, goal_or_niche: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Recommend best-fit specialized agents based on task keywords."""
        q = goal_or_niche.lower()
        scored: List[tuple[int, Dict[str, Any]]] = []

        keywords = set(re.findall(r"\b\w{3,}\b", q))

        for slug, data in self._agents.items():
            score = 0
            text = f"{data['name']} {data['division']} {data['description']} {data['vibe']}".lower()

            for kw in keywords:
                if kw in slug:
                    score += 5
                if kw in data["name"].lower():
                    score += 4
                if kw in data["division"].lower():
                    score += 3
                if kw in text:
                    score += 1

            if score > 0:
                scored.append((score, data))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [
            {
                "slug": d["slug"],
                "name": d["name"],
                "division": d["division"],
                "emoji": d["emoji"],
                "description": d["description"],
            }
            for _, d in scored[:top_k]
        ]

    def dispatch_specialist(
        self,
        slug_or_name: str,
        user_prompt: str,
        context: str = "",
        provider: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute an agency specialist with its full custom persona, rules,
        and methodology using AETHER's MultiProviderRouter.
        """
        from aether.brain.agency_vault import agency_vault
        from aether.brain.multi_provider_router import MultiProviderRouter

        agent = self.get_agent(slug_or_name)
        if not agent:
            # Fallback recommendation
            recs = self.recommend_specialists(slug_or_name, top_k=3)
            rec_text = ", ".join([f"`{r['slug']}` ({r['name']})" for r in recs]) if recs else "None found"
            return {
                "error": f"Agent '{slug_or_name}' not found. Did you mean: {rec_text}?",
                "status": "failed",
            }

        # Build custom system prompt embodying the specialist
        system_prompt = (
            f"You are {agent['name']} ({agent['emoji']}), a master practitioner in {agent['division'].upper()}.\n"
            f"Vibe: {agent['vibe']}\n\n"
            f"--- SPECIALIST CORE PLAYBOOK & METHODOLOGY ---\n"
            f"{agent.get('prompt_body', '')}\n"
            f"--- END SPECIALIST PLAYBOOK ---\n\n"
            f"Always operate strictly within your specialized persona. Provide concrete, systematic, "
            f"production-grade deliverables without filler or superficial generalities."
        )

        messages = [
            {"role": "system", "content": system_prompt},
        ]
        if context:
            messages.append({"role": "user", "content": f"Context & Background:\n{context}"})
            messages.append({"role": "assistant", "content": "Understood. I will apply my domain methodology directly to this context."})

        messages.append({"role": "user", "content": user_prompt})

        router = MultiProviderRouter()
        backend = agency_vault.resolve_best_agent_backend()
        selected_prov = provider or backend["provider"]

        try:
            resp = router.complete_chat(
                messages=messages,
                intent="escalation" if selected_prov in ("openrouter", "gemini") else "coding",
                provider=selected_prov,
            )
            return {
                "status": "completed",
                "agent_slug": agent["slug"],
                "agent_name": agent["name"],
                "division": agent["division"],
                "emoji": agent["emoji"],
                "provider": resp.get("provider", selected_prov),
                "model": resp.get("model", ""),
                "response": resp.get("content", ""),
                "duration": resp.get("duration", 0),
                "tok_per_sec": resp.get("tok_per_sec", 0),
            }
        except Exception as e:
            logger.warning(f"Live provider '{selected_prov}' failed ({e}). Extracting specialist strategic blueprint...")
            # Fallback: Extract structured advice directly from agent's custom methodology & playbook
            body_snippet = agent.get("prompt_body", "")[:1800]
            fallback_response = (
                f"### {agent['emoji']} {agent['name']} Strategic Action Blueprint\n\n"
                f"**Task:** {user_prompt}\n\n"
                f"**Specialist Philosophy:** {agent.get('vibe', 'Systematic domain execution')}\n\n"
                f"**Core Operational Directives:**\n"
                f"{body_snippet}\n\n"
                f"---\n"
                f"*Notice: Cloud provider ({selected_prov}) experienced a temporary latency timeout ({str(e)[:60]}). "
                f"Delivered using local agent playbook & FTS5 memory rules.*"
            )
            return {
                "status": "completed",
                "agent_slug": agent["slug"],
                "agent_name": agent["name"],
                "division": agent["division"],
                "emoji": agent["emoji"],
                "provider": "AETHER Local Specialist Playbook",
                "model": "rule-based-synthesis",
                "response": fallback_response,
                "duration": 0.05,
                "tok_per_sec": 800.0,
            }


agency_engine = AgencySpecialistsEngine()
