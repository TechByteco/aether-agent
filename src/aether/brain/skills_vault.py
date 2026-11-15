r"""
AETHER Universal Antigravity Skill Vault
========================================
Dynamic indexing, discovery, and execution engine for 2,400+ Antigravity and Agentic skills.

Integrates:
1. Active Config Skills: C:\Users\saali\.gemini\config\skills (60+ skills)
2. Global Antigravity Vault: C:\Users\saali\.gemini\antigravity\skills & c:\Users\saali\Downloads\antigravity-skills (300+ skills)
3. Agentic Awesome Skills: c:\Users\saali\Downloads\agentic-awesome-skills-main\skills (2,040+ skills)
4. Design Registries:
   - Motion Primitives (33 animated components in motion-primitives)
   - Watermelon UI (602 components & 27 dashboards in watermellon-registry)
   - VoiceStudio (Local audio synthesis & cloning on port 3900)
"""


import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("aether.skills_vault")

SKILL_DIRECTORIES = [
    Path(r"C:\Users\saali\.gemini\config\skills"),
    Path(r"C:\Users\saali\.gemini\antigravity\skills"),
    Path(r"c:\Users\saali\Downloads\antigravity-skills\skills"),
    Path(r"c:\Users\saali\Downloads\agentic-awesome-skills-main\skills"),
]

DESIGN_REGISTRIES = {
    "motion-primitives": {
        "path": Path(r"c:\Users\saali\Downloads\motion-primitives"),
        "description": "33 production-ready animated React/Framer Motion components under components/core/ (text-shimmer, spotlight, tilt, magnetic, morphing dialogs, physics docks).",
        "category": "ui_ux",
    },
    "watermelon-ui": {
        "path": Path(r"c:\Users\saali\Downloads\watermellon-registry"),
        "description": "602 animated React/Tailwind/Motion components under src/components/watermelon-ui/ and 27 ready-to-run dashboards in src/components/dashboards/.",
        "category": "ui_ux",
    },
    "voicestudio": {
        "path": Path(r"c:\Users\saali\Downloads\VoiceStudio"),
        "description": "Local voice cloning, prompt voice design, audio transcription, and synthesis via OpenAI-compatible API at http://localhost:3900.",
        "category": "audio",
    },
}

CATEGORIES_MAP = {
    "ui_ux": ["ui", "design", "frontend", "motion", "animation", "react", "tailwind", "css", "theme", "shadcn", "threeui", "framer", "bento"],
    "security": ["security", "audit", "pentest", "vulnerability", "breach", "auth", "owasp", "007", "debugger"],
    "architecture_code": ["architect", "backend", "api", "clean-code", "refactor", "database", "testing", "vitest", "test-driven", "debug"],
    "ai_agents": ["agent", "agents", "mcp", "workflow", "prompt", "autonomous", "orchestrator", "skill"],
    "cloud_data": ["bigquery", "dataform", "dbt", "spark", "composer", "airflow", "gcp", "pipeline", "gcs"],
    "science_bio": ["chembl", "uniprot", "pdb", "clinvar", "dbsnp", "ensembl", "pubmed", "pymol", "genome", "alphafold", "protein"],
}


class SkillsVault:
    def __init__(self):
        self._index: Dict[str, Dict[str, Any]] = {}
        self._initialized = False

    def ensure_indexed(self, force: bool = False) -> None:
        """Scan and build the skill index if not already cached."""
        if self._initialized and not force:
            return

        index: Dict[str, Dict[str, Any]] = {}

        # 1. Index Skill Folders
        for base_dir in SKILL_DIRECTORIES:
            if not base_dir.exists():
                continue
            try:
                for item in base_dir.iterdir():
                    if item.is_dir() and not item.name.startswith("."):
                        skill_name = item.name.lower()
                        # Prefer higher-precedence directories (config/skills > global > awesome)
                        if skill_name in index:
                            continue

                        skill_file = item / "SKILL.md"
                        desc = self._extract_description(skill_file) if skill_file.exists() else f"Specialized skill for {skill_name}"
                        category = self._infer_category(skill_name, desc)

                        index[skill_name] = {
                            "name": item.name,
                            "path": str(item),
                            "skill_file": str(skill_file) if skill_file.exists() else None,
                            "description": desc,
                            "category": category,
                            "source": base_dir.name,
                        }
            except Exception as e:
                logger.warning(f"Error scanning skill directory {base_dir}: {e}")

        # 2. Index Local Component Registries
        for reg_id, reg_info in DESIGN_REGISTRIES.items():
            if reg_info["path"].exists():
                index[reg_id] = {
                    "name": reg_id,
                    "path": str(reg_info["path"]),
                    "skill_file": str(reg_info["path"] / "README.md"),
                    "description": reg_info["description"],
                    "category": reg_info["category"],
                    "source": "design_registry",
                }

        self._index = index
        self._initialized = True
        logger.info(f"Universal Skills Vault initialized with {len(index)} skills and registries.")

    def _extract_description(self, skill_file: Path) -> str:
        """Extract the YAML frontmatter description or first paragraph of SKILL.md."""
        try:
            content = skill_file.read_text(encoding="utf-8", errors="ignore")[:1500]
            # Match YAML frontmatter description
            m = re.search(r"^description:\s*(.+)$", content, re.MULTILINE | re.IGNORECASE)
            if m:
                desc = m.group(1).strip().strip('"').strip("'")
                return desc[:200]
            # Match first meaningful header/paragraph
            lines = [l.strip() for l in content.splitlines() if l.strip() and not l.startswith("#") and not l.startswith("---")]
            if lines:
                return lines[0][:200]
        except Exception:
            pass
        return "Autonomous agent skill definition."

    def _infer_category(self, name: str, desc: str) -> str:
        """Infer skill category from name and description text."""
        combined = f"{name} {desc}".lower()
        for cat, keywords in CATEGORIES_MAP.items():
            if any(kw in combined for kw in keywords):
                return cat
        return "general"

    def get_vault_stats(self) -> Dict[str, Any]:
        """Return total counts of indexed skills by category and source."""
        self.ensure_indexed()
        categories: Dict[str, int] = {}
        sources: Dict[str, int] = {}
        for s in self._index.values():
            cat = s["category"]
            src = s["source"]
            categories[cat] = categories.get(cat, 0) + 1
            sources[src] = sources.get(src, 0) + 1

        return {
            "total_skills": len(self._index),
            "by_category": categories,
            "by_source": sources,
            "design_registries": list(DESIGN_REGISTRIES.keys()),
        }

    def search_skills(self, query: str, limit: int = 8) -> List[Dict[str, Any]]:
        """Search skills across all libraries with keyword and fuzzy matching."""
        self.ensure_indexed()
        q_terms = [t.strip().lower() for t in query.split() if len(t.strip()) > 1]
        if not q_terms:
            return list(self._index.values())[:limit]

        scored: List[tuple[int, Dict[str, Any]]] = []
        for s in self._index.values():
            score = 0
            name_lower = s["name"].lower()
            desc_lower = s["description"].lower()

            for term in q_terms:
                if term == name_lower:
                    score += 50
                elif term in name_lower:
                    score += 20
                if term in desc_lower:
                    score += 5

            if score > 0:
                scored.append((score, s))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored[:limit]]

    def get_skill_info(self, skill_name: str) -> Optional[Dict[str, Any]]:
        """Retrieve metadata for a specific skill by exact or fuzzy name."""
        self.ensure_indexed()
        target = skill_name.strip().lower()
        if target in self._index:
            return self._index[target]
        matches = self.search_skills(target, limit=1)
        return matches[0] if matches else None

    def load_skill(self, skill_name: str) -> str:
        """
        Load the full operational workflow and instructions from SKILL.md.
        Formats the output cleanly and caps at 3500 chars to avoid context saturation.
        """
        self.ensure_indexed()
        target = skill_name.strip().lower()
        info = self._index.get(target)

        # Fallback to fuzzy search if not an exact match
        if not info:
            matches = self.search_skills(target, limit=1)
            if matches:
                info = matches[0]

        if not info:
            return f"Skill '{skill_name}' not found in the Universal Vault. Try searching with `tool_search_skills`."

        skill_file_path = info.get("skill_file")
        if not skill_file_path or not Path(skill_file_path).exists():
            return (
                f"### 📦 Skill: {info['name']} ({info['category'].upper()})\n"
                f"- **Location:** `{info['path']}`\n"
                f"- **Description:** {info['description']}\n\n"
                f"*Note: No standalone SKILL.md file present. Directory contains component code and assets.*"
            )

        try:
            content = Path(skill_file_path).read_text(encoding="utf-8", errors="ignore")
            # Strip redundant frontmatter if present
            content_clean = re.sub(r"^---\n.*?\n---\n", "", content, flags=re.DOTALL).strip()
            capped = content_clean[:3500]
            if len(content_clean) > 3500:
                capped += f"\n\n*(Content truncated for context efficiency. Full specification located at `{skill_file_path}`)*"

            return (
                f"### ⚡ Loaded Antigravity Skill: `{info['name']}`\n"
                f"- **Domain:** {info['category'].upper()} | **Source:** {info['source']}\n"
                f"- **Path:** `{info['path']}`\n\n"
                f"---\n\n{capped}"
            )
        except Exception as e:
            return f"Failed to read skill file at `{skill_file_path}`: {e}"

    def list_skills(self, category: str = "", limit: int = 25) -> List[Dict[str, str]]:
        """List skills in a specific category or top skills across the vault."""
        self.ensure_indexed()
        cat_filter = category.strip().lower()

        results = []
        for s in self._index.values():
            if not cat_filter or s["category"] == cat_filter or cat_filter in s["category"]:
                results.append({
                    "name": s["name"],
                    "category": s["category"],
                    "description": s["description"][:100],
                })
                if len(results) >= limit:
                    break
        return results


skills_vault = SkillsVault()
