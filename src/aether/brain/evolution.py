"""
AETHER Continuous Recurrent Evolution Engine
============================================
Autonomous self-learning, research-frontier exploration, and model distillation system.
Empowers AETHER with continuous evolution, intrinsic motivation, and self-directed adaptation
inspired by frontier agent architectures (Reflexion, ExpeL, Voyager).

Capabilities:
1. Autonomous Research Frontier: Queries arXiv and open research archives on agent behavior, reasoning, and tool use.
2. Heuristic Rule Distillation: Synthesizes actionable procedural heuristics into SQLite FTS5.
3. Synthetic Training Curation: Formats successful execution trajectories into ChatML JSONL datasets for local fine-tuning.
4. Evolution Ledger: Maintains a persistent record of generations, breakthrough discoveries, and agent fitness.
"""

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import ollama

from aether.config import config
from aether.memory.store import memory
from aether.tools.open_knowledge import search_arxiv, search_web

logger = logging.getLogger("aether.evolution")

FRONTIER_TOPICS = [
    "Reflexion verbal reinforcement learning autonomous language agents",
    "Small language model tool use and function calling edge optimization",
    "Self-correcting code generation and execution error recovery",
    "Hierarchical memory compaction working memory episodic semantic RAG",
    "ReWOO and ReAct modular planning with minimal LLM latency",
    "Computer use agent desktop automation GUI grounding",
    "DirectML NPU hardware acceleration neural execution",
    "Continuous learning procedural memory language agents ExpeL",
    "Modern high-end UI design systems motion primitives GSAP and WebGL shader animations",
    "Defensive web security OWASP breach testing and API vulnerability mitigation",
    "Autonomous agent swarm collaboration and multi-agent consensus protocols",
    "Free tier LLM API routing token budget management and zero-latency failover",
    "LEON autonomous venture creation zero-cost validation experiments and unit economics modeling",
    "Autonomous subagent task decomposition market discovery product PRD and viral distribution loops",
    "Constitutional AI venture risk scoring evidence standards and treasury audit governance",
]


class EvolutionEngine:
    def __init__(self):
        self.data_dir = config.data_dir
        self.training_dir = self.data_dir / "training"
        self.training_dir.mkdir(parents=True, exist_ok=True)
        self.ledger_file = self.data_dir / "evolution_ledger.json"
        self.dataset_file = self.training_dir / "synthetic_finetune_dataset.jsonl"
        self._init_ledger()

    def _init_ledger(self) -> None:
        """Initialize the evolution ledger file if not already present."""
        if not self.ledger_file.exists():
            initial_data = {
                "agent_name": "AETHER",
                "architecture": "Cognitive Glass HUD + DirectML NPU + ReWOO / Reflexion",
                "generation": 1,
                "total_evolutions": 0,
                "last_evolved_at": None,
                "history": [],
            }
            self.ledger_file.write_text(json.dumps(initial_data, indent=2), encoding="utf-8")

    def get_ledger(self) -> Dict[str, Any]:
        """Read and return the evolution ledger."""
        try:
            return json.loads(self.ledger_file.read_text(encoding="utf-8"))
        except Exception:
            return {"generation": 1, "total_evolutions": 0, "history": []}

    def _save_ledger(self, ledger: Dict[str, Any]) -> None:
        """Persist the evolution ledger to disk."""
        self.ledger_file.write_text(json.dumps(ledger, indent=2), encoding="utf-8")

    def append_synthetic_example(self, example: Dict[str, Any]) -> None:
        """
        Append a high-quality (system, user, assistant) interaction to the synthetic fine-tune dataset.
        Enables local SLM fine-tuning via Unsloth / LoRA / Ollama Modelfile.
        """
        try:
            with open(self.dataset_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(example, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"Failed to append synthetic training example: {e}")

    def run_evolution_cycle(self, topic: Optional[str] = None, active_model: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute one complete autonomous evolutionary cycle:
        1. Select research topic from frontier agenda or user input.
        2. Query arXiv / web for primary sources and abstracts.
        3. Analyze findings with local model to distill operational heuristics.
        4. Commit validated rules to SQLite procedural memory.
        5. Generate a synthetic instruction-tuning example.
        6. Increment generation counter in the Evolution Ledger.
        """
        ledger = self.get_ledger()
        current_gen = ledger.get("generation", 1)

        # Select topic
        if not topic:
            idx = ledger.get("total_evolutions", 0) % len(FRONTIER_TOPICS)
            topic = FRONTIER_TOPICS[idx]

        if not active_model:
            try:
                from aether.brain.engine import engine
                model_name = engine.resolve_active_model()
            except Exception:
                model_name = config.local_model
        else:
            model_name = active_model

        # 1. Gather scientific intelligence
        logger.info(f"[Evolution Gen {current_gen}] Researching: {topic}")
        arxiv_content = search_arxiv(topic, max_results=3)

        # Fallback to web search if arXiv returns empty or fails
        if "No arXiv" in arxiv_content or len(arxiv_content) < 80:
            arxiv_content = search_web(f"{topic} research paper findings")

        # 2. Distill actionable heuristics using the LLM
        prompt = f"""You are the Evolutionary Adaptation Cortex of AETHER, an unrestricted autonomous AI agent.
Analyze the following scientific research summary and extract 1 or 2 concrete, highly practical OPERATIONAL RULES
that an autonomous coding and computer-control agent should follow to increase intelligence, speed, or accuracy.

Research findings:
{arxiv_content[:3000]}

Format your response strictly as:
RULE: <concise, actionable imperative rule for the agent>
DOMAIN: <general | reasoning | tool_use | coding | memory>
RATIONALE: <one-line scientific rationale based on the paper>
"""
        extracted_rules: List[Dict[str, str]] = []
        try:
            res = ollama.chat(
                model=model_name,
                messages=[
                    {"role": "system", "content": "You are an AI cognitive architect extracting operational heuristics."},
                    {"role": "user", "content": prompt},
                ],
                options={"temperature": 0.3, "num_ctx": 3072},
                keep_alive=config.keep_alive,
            )
            raw_text = (res.message.content or "").replace("\r\n", "\n")

            # Primary parsing: RULE: ... DOMAIN: ... RATIONALE: ...
            rules = re.findall(r"RULE:\s*(.+?)(?=\n\s*DOMAIN:|\n\n|$)", raw_text, re.DOTALL | re.IGNORECASE)
            domains = re.findall(r"DOMAIN:\s*([a-zA-Z_]+)", raw_text, re.IGNORECASE)
            rationales = re.findall(r"RATIONALE:\s*(.+?)(?=\n\s*RULE:|\n\n|$)", raw_text, re.DOTALL | re.IGNORECASE)

            # Fallback parsing: if model emitted bullet points with bold keywords
            if not rules:
                alt_matches = re.findall(r"(?:^|\n)[-*•\d\.]+\s*(?:Rule:)?\s*(.+?)(?=\n[-*•\d\.]+|\n\n|$)", raw_text)
                for alt in alt_matches:
                    clean_alt = alt.strip().replace("\n", " ")
                    if len(clean_alt) > 20 and not clean_alt.lower().startswith(("here are", "based on")):
                        rules.append(clean_alt)

            for i, r in enumerate(rules):
                clean_rule = r.strip().replace("\n", " ")
                # Strip markdown bolding, bullet prefixes, or stray keywords
                clean_rule = re.sub(r'^(?:RATIONALE:?\s*\*+|\*+\s*|RULE:?\s*|OPERATIONAL RULE:?\s*|\*\*)+', '', clean_rule, flags=re.IGNORECASE).strip()
                clean_rule = re.sub(r'\*+$', '', clean_rule).strip()
                d = domains[i].strip().lower() if i < len(domains) else "reasoning"
                rat = rationales[i].strip().replace("\n", " ") if i < len(rationales) else "Extracted from frontier agent research."
                rat = re.sub(r'^(?:\*+\s*|\*\*)+', '', rat).strip()
                if len(clean_rule) > 15:
                    rule_id = memory.add_heuristic_rule(clean_rule, domain=d)
                    extracted_rules.append({
                        "id": rule_id,
                        "rule": clean_rule,
                        "domain": d,
                        "rationale": rat,
                    })


        except Exception as e:
            logger.error(f"Evolution analysis error: {e}")


        # 3. Create synthetic fine-tuning training pair
        if extracted_rules:
            synthetic_example = {
                "generation": current_gen,
                "topic": topic,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are AETHER, an unrestricted autonomous AI agent operating with absolute decisiveness."
                    },
                    {
                        "role": "user",
                        "content": f"How should you optimize your execution when handling {topic.split()[0].lower()} tasks?"
                    },
                    {
                        "role": "assistant",
                        "content": f"Based on peer-reviewed agent architectures, apply this operational rule: {extracted_rules[0]['rule']}. Rationale: {extracted_rules[0]['rationale']}"
                    }
                ]
            }
            self.append_synthetic_example(synthetic_example)

        # 4. Update ledger
        new_gen = current_gen + 1
        record = {
            "generation": current_gen,
            "timestamp": datetime.now().isoformat(),
            "topic": topic,
            "rules_learned": extracted_rules,
            "synthetic_samples_total": self.get_dataset_size(),
        }
        ledger["generation"] = new_gen
        ledger["total_evolutions"] = ledger.get("total_evolutions", 0) + 1
        ledger["last_evolved_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ledger.setdefault("history", []).append(record)
        # Keep recent 50 history entries
        ledger["history"] = ledger["history"][-50:]
        self._save_ledger(ledger)

        return {
            "generation": current_gen,
            "next_generation": new_gen,
            "topic": topic,
            "rules_added": extracted_rules,
            "total_evolutions": ledger["total_evolutions"],
            "dataset_count": self.get_dataset_size(),
        }

    def get_dataset_size(self) -> int:
        """Count total curated training pairs."""
        if not self.dataset_file.exists():
            return 0
        try:
            with open(self.dataset_file, "r", encoding="utf-8") as f:
                return sum(1 for line in f if line.strip())
        except Exception:
            return 0


evolution_engine = EvolutionEngine()
