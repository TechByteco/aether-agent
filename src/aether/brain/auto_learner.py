"""
AETHER Autonomous Auto-Learning Cortex
=======================================
Enables continuous, self-directed learning without manual intervention:
1. Turn Introspection: Analyzes every user prompt & response to extract preferences, corrections, and rules.
2. Error Introspection (Reflexion): Synthesizes avoidance rules from tool execution failures so mistakes are never repeated.
3. Design & Architecture Distillation: Captures anti-slop visual patterns, Tailwind/Framer standards, and system blueprints.
4. Synthetic Dataset Curation: Automatically formats high-value trajectories into ChatML JSONL for local model fine-tuning.
5. Operates asynchronously in background threads with zero latency impact (<2ms).
"""

import json
import logging
import re
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from aether.config import config
from aether.memory.persona import persona
from aether.memory.store import memory

logger = logging.getLogger("aether.auto_learner")

# Regex patterns for real-time user correction and preference extraction
CORRECTION_PATTERNS = [
    r"(?:don't|do not|never)\s+(?:use|do|write|run)\s+([^.\n]+)",
    r"(?:instead of)\s+([^,\n]+)[,\s]+(?:use|do|prefer)\s+([^.\n]+)",
    r"(?:always|make sure to|remember to)\s+([^.\n]+)",
    r"(?:you should|please)\s+(?:use|prefer|set)\s+([^.\n]+)",
    r"(?:use|prefer)\s+([a-zA-Z0-9_\-\.]+)\s+(?:instead of|rather than|not)\s+([a-zA-Z0-9_\-\.]+)",
]

PREFERENCE_PATTERNS = [
    r"(?:i prefer|i like|my preference is)\s+([^.\n]+)",
    r"(?:my project uses|we use|our stack is)\s+([^.\n]+)",
    r"(?:my name is|call me)\s+([a-zA-Z0-9_\s]+)",
]

DESIGN_KEYWORDS = [
    "tailwind", "framer motion", "gsap", "obsidian", "dark mode",
    "bento grid", "lucide", "microinteraction", "spring physics", "shader"
]


class AutoLearner:
    def __init__(self):
        self.data_dir = config.data_dir
        self.training_dir = self.data_dir / "training"
        self.training_dir.mkdir(parents=True, exist_ok=True)
        self.dataset_file = self.training_dir / "synthetic_finetune_dataset.jsonl"
        self._lock = threading.Lock()

    def introspect_turn_async(
        self,
        user_message: str,
        assistant_response: str,
        tool_events: Optional[List[Dict[str, Any]]] = None,
        session_id: str = "default",
    ) -> None:
        """Launch turn introspection in a non-blocking background daemon thread."""
        t = threading.Thread(
            target=self.introspect_turn,
            args=(user_message, assistant_response, tool_events, session_id),
            name="AETHER-AutoLearner",
            daemon=True,
        )
        t.start()

    def introspect_turn(
        self,
        user_message: str,
        assistant_response: str,
        tool_events: Optional[List[Dict[str, Any]]] = None,
        session_id: str = "default",
    ) -> Dict[str, Any]:
        """
        Synchronously evaluate a single turn:
        1. Scan for explicit user corrections or negative constraints.
        2. Scan for user preferences or identity facts.
        3. Evaluate tool execution errors to derive avoidance heuristics.
        4. Detect design patterns and UI tokens.
        5. Curate high-quality outputs into the synthetic fine-tuning dataset.
        """
        learned_items = {
            "rules_learned": [],
            "facts_stored": [],
            "avoidance_rules": [],
            "dataset_curated": False,
        }

        u_lower = user_message.lower().strip()

        # 1. User Correction Introspection
        for pattern in CORRECTION_PATTERNS:
            m = re.search(pattern, u_lower)
            if m:
                extracted = m.group(0).strip()
                if len(extracted) > 10:
                    clean_rule = f"User Directive: {extracted.capitalize()}."
                    rule_id = memory.add_heuristic_rule(clean_rule, domain="correction")
                    learned_items["rules_learned"].append({"id": rule_id, "rule": clean_rule})
                    logger.info(f"[AutoLearner] Learned user correction #{rule_id}: {clean_rule}")
                break

        # 2. User Preferences & Personal Facts Introspection
        for pattern in PREFERENCE_PATTERNS:
            m = re.search(pattern, u_lower)
            if m:
                fact_val = m.group(1).strip() if m.groups() else m.group(0).strip()
                if len(fact_val) > 2:
                    memory.remember_fact("user_preference", "preference", fact_val)
                    persona.append_fact_to_profile(f"Preference: {fact_val}")
                    learned_items["facts_stored"].append(fact_val)
                    logger.info(f"[AutoLearner] Stored user preference: {fact_val}")
                break

        # 3. Tool Execution & Error Introspection (Reflexion)
        if tool_events:
            for ev in tool_events:
                tool_name = ev.get("tool", "")
                result_str = str(ev.get("result", ""))
                is_error = ev.get("is_error", False) or "error:" in result_str.lower() or "exception:" in result_str.lower()

                if is_error and len(result_str) > 15:
                    avoidance_rule = self._derive_avoidance_rule(tool_name, result_str)
                    if avoidance_rule:
                        rule_id = memory.add_heuristic_rule(avoidance_rule, domain="avoidance")
                        learned_items["avoidance_rules"].append({"id": rule_id, "rule": avoidance_rule})
                        logger.info(f"[AutoLearner] Derived error avoidance heuristic #{rule_id}: {avoidance_rule}")

        # 4. Design & Aesthetic Pattern Introspection
        if any(kw in u_lower or kw in assistant_response.lower() for kw in DESIGN_KEYWORDS):
            if "```" in assistant_response:
                design_rule = "When creating animated interfaces, use OLED dark palette (#09090b), 1px border (rgba(255,255,255,0.08)), Framer Motion spring physics, and Tailwind CSS."
                existing = memory.recall_heuristic_rules("design palette framer motion", limit=1)
                if not existing:
                    r_id = memory.add_heuristic_rule(design_rule, domain="design")
                    learned_items["rules_learned"].append({"id": r_id, "rule": design_rule})

        # 5. Synthetic Fine-Tuning Dataset Curation
        # If the turn generated substantial, structured, high-value code or reasoning (>250 chars)
        if len(assistant_response) > 250 and ("```" in assistant_response or len(assistant_response.splitlines()) > 5):
            self.curate_training_example(
                user_message=user_message,
                assistant_response=assistant_response,
                domain="reasoning" if "```" not in assistant_response else "coding",
            )
            learned_items["dataset_curated"] = True

        return learned_items

    def _derive_avoidance_rule(self, tool_name: str, error_text: str) -> Optional[str]:
        """Derive an actionable procedural avoidance rule from an error string."""
        err_lower = error_text.lower()

        if "no module named" in err_lower:
            m = re.search(r"no module named ['\"]?([a-zA-Z0-9_\-]+)['\"]?", err_lower)
            mod = m.group(1) if m else "package"
            return f"When importing '{mod}' in Python sandbox, verify installation or import guards before running."

        if "filenotfounderror" in err_lower or "cannot find the file" in err_lower:
            return f"Before accessing files with {tool_name}, always verify file existence or search directory trees with tool_find_files."

        if "permission denied" in err_lower or "unauthorizedaccess" in err_lower:
            return f"When executing PowerShell commands in {tool_name}, use .cmd executables (e.g. npm.cmd) or run with elevated permissions."

        if "connection refused" in err_lower or "target machine actively refused" in err_lower:
            return "When connecting to local gateways (e.g. FreeLLMAPI port 3001), verify the service is running before dispatching requests."

        # Generic concise error rule
        cleaned = re.sub(r'[\r\n]+', ' ', error_text[:120]).strip()
        return f"Avoid failure in {tool_name}: Ensure inputs avoid error pattern: '{cleaned}'"

    def curate_training_example(
        self,
        user_message: str,
        assistant_response: str,
        domain: str = "general",
    ) -> None:
        """Append an instruction-tuning sample into synthetic_finetune_dataset.jsonl."""
        try:
            sample = {
                "timestamp": datetime.now().isoformat(),
                "domain": domain,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are AETHER, an elite autonomous AI companion and principal systems technologist operating with Claude and Antigravity standards."
                    },
                    {
                        "role": "user",
                        "content": user_message.strip()
                    },
                    {
                        "role": "assistant",
                        "content": assistant_response.strip()
                    }
                ]
            }
            with self._lock:
                with open(self.dataset_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(sample, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.debug(f"Failed to append synthetic training example: {e}")

    def get_learning_metrics(self) -> Dict[str, Any]:
        """Aggregate real-time auto-learning statistics from SQLite and dataset files."""
        dataset_count = 0
        if self.dataset_file.exists():
            try:
                with open(self.dataset_file, "r", encoding="utf-8") as f:
                    dataset_count = sum(1 for line in f if line.strip())
            except Exception:
                dataset_count = 0

        # Query rules from SQLite
        all_rules = memory.recall_heuristic_rules("", limit=100)
        by_domain = {}
        for r in all_rules:
            # Each r is text or dictionary
            by_domain["total"] = by_domain.get("total", 0) + 1

        facts = memory.recall_facts()

        return {
            "total_rules_in_memory": len(all_rules),
            "total_facts_stored": len(facts),
            "synthetic_dataset_samples": dataset_count,
            "recent_rules": all_rules[:6] if all_rules else [],
            "status": "Active (Continuous Introspection Enabled)",
        }


auto_learner = AutoLearner()
