"""
AETHER Agency Training Synthesizer
==================================
Transforms the 290+ specialized AI agency agent personas and methodologies
into:
1. Permanent procedural memory rules in AETHER's SQLite FTS5 database (`heuristic_rules`)
2. Fine-tuning instruction dataset (`data/training/agency_agents_training.jsonl`)
3. Automated Kaggle Tesla T4 GPU fine-tuning dispatch via `kaggle_controller`

This allows AETHER and LEON to absorb all specialized agency skills permanently
into offline local models (Llama 3.2 3B, Qwen 2.5 3B, etc.).
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger("aether.agency_training")

_WORKSPACE = Path(__file__).resolve().parents[3]
_TRAINING_DIR = _WORKSPACE / "data" / "training"
_TRAINING_DIR.mkdir(parents=True, exist_ok=True)


class AgencyTrainingSynthesizer:
    """Ingests agency personas into AETHER episodic memory and fine-tuning datasets."""

    def __init__(self) -> None:
        self.output_dataset = _TRAINING_DIR / "agency_agents_training.jsonl"

    def extract_heuristics_and_rules(self, max_agents: int = 100) -> int:
        """
        Extract core principles, equations, and rules from agency agents
        and inject them into AETHER's SQLite conscious memory store.
        """
        from aether.brain.agency_specialists_engine import agency_engine
        from aether.memory.store import memory

        agents = agency_engine.list_agents()
        rules_added = 0

        for a in agents[:max_agents]:
            full = agency_engine.get_agent(a["slug"])
            if not full or not full.get("prompt_body"):
                continue

            body = full["prompt_body"]
            div = full["division"]
            name = full["name"]

            # 1. Store atomic fact about this specialist
            memory.remember_fact("agency_specialist", a["slug"], f"{name}: {a['description']}")

            # 2. Extract bullet points that represent rules or principles
            bullets = re.findall(r"^[*-]\s+\*\*([^*]+)\*\*:\s*(.+)$", body, re.MULTILINE)
            for title, rule_text in bullets[:4]:
                rule_str = f"[{div.upper()}:{name}] {title}: {rule_text}"
                try:
                    memory.add_heuristic_rule(rule_str, domain=div)
                    rules_added += 1
                except Exception as e:
                    logger.debug(f"Failed to add rule: {e}")

        logger.info(f"Injected {rules_added} agency procedural rules into SQLite FTS5 memory.")
        return rules_added

    def synthesize_finetuning_dataset(self) -> Dict[str, Any]:
        """
        Compile instruction-tuning dataset from all agency agents.
        Format: Alpaca JSONL (instruction, input, output).
        """
        from aether.brain.agency_specialists_engine import agency_engine

        agents = agency_engine.list_agents()
        records: List[Dict[str, str]] = []

        for a in agents:
            full = agency_engine.get_agent(a["slug"])
            if not full or not full.get("prompt_body"):
                continue

            name = full["name"]
            div = full["division"]
            desc = full["description"]
            body = full["prompt_body"]

            # Sample 1: Persona adoption instruction
            records.append({
                "instruction": f"Act as the {name} ({full['emoji']}) in the {div.title()} division.",
                "input": f"What is your core mission, operating philosophy, and deliverables?",
                "output": f"I am the {name}. {desc}\n\nCore Principles & Methodology:\n{body[:1500]}",
            })

            # Sample 2: Tactical execution instruction
            records.append({
                "instruction": f"As {name}, analyze a request in {div} and provide a production-grade action plan.",
                "input": f"How do you evaluate and structure high-converting solutions for {div}?",
                "output": f"Operating within the {div} framework:\n1. Philosophy: {full.get('vibe', 'Systematic execution')}\n2. Core Methodology:\n{body[:1800]}",
            })

        # Save to JSONL
        with self.output_dataset.open("w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

        logger.info(f"Synthesized {len(records)} instruction training samples to {self.output_dataset}")
        return {
            "dataset_path": str(self.output_dataset),
            "samples_count": len(records),
            "status": "ready_for_training",
        }

    def trigger_kaggle_agency_training(self) -> Dict[str, Any]:
        """Dispatch the agency dataset to Kaggle GPU for fine-tuning."""
        from aether.brain.kaggle_controller import kaggle_controller

        # First ensure dataset is synthesized
        synth_res = self.synthesize_finetuning_dataset()
        dataset_path = Path(synth_res["dataset_path"])

        try:
            # Dispatch to Kaggle
            res = kaggle_controller.train_model(
                base_model="unsloth/Llama-3.2-3B-Instruct",
                dataset_path=dataset_path,
                epochs=2,
            )
            return {
                "status": "dispatched",
                "kaggle_result": res,
                "dataset_samples": synth_res["samples_count"],
            }
        except Exception as e:
            logger.warning(f"Kaggle dispatch note: {e}")
            return {
                "status": "dataset_ready_local",
                "dataset_path": str(dataset_path),
                "samples_count": synth_res["samples_count"],
                "note": f"Dataset ready for Kaggle/local training. ({e})",
            }


agency_training_synthesizer = AgencyTrainingSynthesizer()
