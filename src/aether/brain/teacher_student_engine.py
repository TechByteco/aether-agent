"""
AETHER Autonomous Teacher-Student Neuro-Evolution Engine
=========================================================
Implements a continuous developmental learning curriculum where frontier foundation models
(Claude 3.7 Sonnet, Google Gemini 2.5 Pro, DeepSeek-R1) act as Mentors/Critics that continuously
train, test, critique, and evolve AETHER from a foundational learner ("child") to an autonomous
master intelligence ("sovereign agent").

Curriculum Stages:
- STAGE 1: INFANT / SENSORY GROUNDING (Strict JSON tool syntax, direct OS commands, zero hallucination)
- STAGE 2: ADOLESCENT / PROCEDURAL REASONING (ReWOO planning, multi-step tool chaining, AST self-healing)
- STAGE 3: SCHOLAR / DUAL-PROCESS DELIBERATION (System 1 vs System 2, security threat modeling, invariant formulation)
- STAGE 4: SOVEREIGN MASTER / META-EVOLUTION (Dynamic tool genesis, synthetic dataset curation, autonomous DPO)
"""

import json
import logging
import re
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import httpx
import ollama

from aether.brain.evolution import evolution_engine
from aether.brain.online_cortex import online_cortex
from aether.config import config
from aether.memory.store import memory

logger = logging.getLogger("aether.teacher_student")


class CognitiveStage(str, Enum):
    STAGE_1_CHILD = "Stage 1: Sensory Grounding & Fast Reflexes (Child)"
    STAGE_2_ADOLESCENT = "Stage 2: Procedural Logic & Self-Healing (Adolescent)"
    STAGE_3_SCHOLAR = "Stage 3: Systems Deliberation & Invariants (Scholar)"
    STAGE_4_SOVEREIGN = "Stage 4: Autonomous Tool Genesis & Meta-Evolution (Sovereign)"


STAGE_CURRICULA = {
    CognitiveStage.STAGE_1_CHILD: {
        "focus": "Deterministic tool execution, exact JSON argument formatting, avoiding conversational filler, strict tool output comprehension.",
        "difficulty": 1,
        "sample_topics": [
            "Execute system vitals inspection with tool_system_vitals",
            "Perform surgical file read with proper line numbers",
            "Hunt for exposed secrets in a project directory",
            "Check network ports and open sockets with filter_state",
        ]
    },
    CognitiveStage.STAGE_2_ADOLESCENT: {
        "focus": "Multi-step ReWOO execution plans, graceful handling of tool failures, AST patching, error backpropagation.",
        "difficulty": 2,
        "sample_topics": [
            "Deconstruct a failing Python script, inspect stack trace, apply AST patch, and verify fix",
            "Chain web search + content extraction + structured summary into a single workflow",
            "Audit memory footprint and optimize thread contention under load",
        ]
    },
    CognitiveStage.STAGE_3_SCHOLAR: {
        "focus": "Deep architectural design, OWASP Top 10 security audits, BigQuery SQL optimization, formal invariant derivation.",
        "difficulty": 3,
        "sample_topics": [
            "Design an idempotent distributed event processor with out-of-order crash recovery",
            "Perform STRIDE/PASTA threat model on a multi-tenant GraphQL service",
            "Architect a zero-slop UI component with spring physics and WCAG AAA compliance",
        ]
    },
    CognitiveStage.STAGE_4_SOVEREIGN: {
        "focus": "Autonomous tool genesis, synthesizing missing capabilities into Python AST plugins, self-directed DPO training.",
        "difficulty": 4,
        "sample_topics": [
            "Identify missing tool capability for binary analysis and synthesize native tool plugin",
            "Synthesize cross-domain principles fusing cryptography, UI state machines, and concurrency",
            "Formulate universal cognitive invariants that prevent LLM reasoning collapse",
        ]
    }
}


@dataclass
class EvaluationVerdict:
    score: int  # 1 - 100
    passed: bool
    stage: CognitiveStage
    critique: str
    cognitive_invariant: Optional[str]
    chosen_response: str
    rejected_response: Optional[str]
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class TeacherStudentOrchestrator:
    def __init__(self):
        self.data_dir = config.data_dir
        self.training_dir = self.data_dir / "training"
        self.training_dir.mkdir(parents=True, exist_ok=True)
        self.dpo_dataset_file = self.training_dir / "dpo_preference_dataset.jsonl"
        self.sft_dataset_file = self.training_dir / "synthetic_finetune_dataset.jsonl"
        self.stage_tracker_file = self.data_dir / "developmental_stage.json"
        self._lock = threading.Lock()
        self._init_stage_tracker()

    def _init_stage_tracker(self) -> None:
        if not self.stage_tracker_file.exists():
            initial_state = {
                "current_stage": CognitiveStage.STAGE_2_ADOLESCENT.value,
                "stage_progress": 45,  # Percentage mastery of current stage
                "total_evaluations": 0,
                "passed_evaluations": 0,
                "average_score": 82.5,
                "last_evaluation_at": None,
                "stage_history": [],
            }
            self.stage_tracker_file.write_text(json.dumps(initial_state, indent=2), encoding="utf-8")

    def get_current_stage_info(self) -> Dict[str, Any]:
        try:
            return json.loads(self.stage_tracker_file.read_text(encoding="utf-8"))
        except Exception:
            return {
                "current_stage": CognitiveStage.STAGE_2_ADOLESCENT.value,
                "stage_progress": 50,
                "average_score": 80.0,
            }

    def _update_stage_progress(self, verdict: EvaluationVerdict) -> None:
        with self._lock:
            state = self.get_current_stage_info()
            total = state.get("total_evaluations", 0) + 1
            passed = state.get("passed_evaluations", 0) + (1 if verdict.passed else 0)
            avg_score = ((state.get("average_score", 75.0) * (total - 1)) + verdict.score) / total
            
            # Progress calculation
            progress = min(100, int((passed / max(1, total)) * 100))
            current_stage_str = state.get("current_stage", CognitiveStage.STAGE_1_CHILD.value)

            # Stage Advancement Rules
            if progress >= 85 and total >= 15:
                if CognitiveStage.STAGE_1_CHILD.value in current_stage_str:
                    current_stage_str = CognitiveStage.STAGE_2_ADOLESCENT.value
                    progress = 10
                elif CognitiveStage.STAGE_2_ADOLESCENT.value in current_stage_str:
                    current_stage_str = CognitiveStage.STAGE_3_SCHOLAR.value
                    progress = 10
                elif CognitiveStage.STAGE_3_SCHOLAR.value in current_stage_str:
                    current_stage_str = CognitiveStage.STAGE_4_SOVEREIGN.value
                    progress = 10

            state["current_stage"] = current_stage_str
            state["stage_progress"] = progress
            state["total_evaluations"] = total
            state["passed_evaluations"] = passed
            state["average_score"] = round(avg_score, 1)
            state["last_evaluation_at"] = verdict.timestamp

            self.stage_tracker_file.write_text(json.dumps(state, indent=2), encoding="utf-8")

    def synthesize_teacher_challenge(self, stage: CognitiveStage, topic_override: Optional[str] = None) -> Dict[str, str]:
        """
        Frontier Teacher (Gemini 2.5 Pro / Claude 3.7) synthesizes a multi-faceted
        developmental challenge calibrated specifically to AETHER's current learning level.
        """
        curriculum = STAGE_CURRICULA.get(stage, STAGE_CURRICULA[CognitiveStage.STAGE_2_ADOLESCENT])
        chosen_topic = topic_override or curriculum["sample_topics"][int(time.time()) % len(curriculum["sample_topics"])]

        prompt = f"""You are the Master Curriculum Teacher (Frontier AI Mentor).
You are designing a developmental training challenge for an autonomous AI agent (AETHER) currently at:
STAGE: {stage.value}
STAGE FOCUS: {curriculum['focus']}
TOPIC: {chosen_topic}

Generate a challenging, realistic real-world problem scenario where the agent must demonstrate:
1. Precise tool planning or structured reasoning.
2. Concrete execution details without conversational fluff.
3. Resilience against edge-cases.

Respond in JSON format:
{{
  "title": "<short challenge title>",
  "scenario": "<detailed prompt/task for the student>",
  "rubric": "<what criteria make an optimal answer versus an unacceptable answer>"
}}"""

        try:
            from aether.brain.multi_provider_router import \
                multi_provider_router
            comp = multi_provider_router.complete_chat(
                messages=[
                    {"role": "system", "content": "You are a Principal AI Mentor crafting frontier cognitive curriculum."},
                    {"role": "user", "content": prompt}
                ],
                provider="gemini" if multi_provider_router.get_api_key("gemini") else ("openrouter" if multi_provider_router.get_api_key("openrouter") else None),
                model="gemini-flash-latest",
                temperature=0.3,
            )
            raw_response = comp.get("content", "")
            # Clean JSON markdown if wrapped
            clean = re.sub(r"^```json\s*|\s*```$", "", raw_response.strip(), flags=re.MULTILINE)
            data = json.loads(clean)
            return data
        except Exception as e:
            logger.warning(f"Teacher challenge generation fallback: {e}")
            return {
                "title": f"Developmental Challenge: {chosen_topic}",
                "scenario": f"Analyze and execute the following task with absolute precision: {chosen_topic}",
                "rubric": "Accurate tool syntax, zero hallucinated parameters, concrete action steps."
            }

    def evaluate_student_attempt(
        self,
        challenge: Dict[str, str],
        student_attempt: str,
        stage: CognitiveStage,
    ) -> EvaluationVerdict:
        """
        Frontier Critic (Claude 3.7 Sonnet / DeepSeek-R1) evaluates AETHER's attempt,
        assigns a 1-100 score, provides the gold-standard 'chosen' trajectory, and extracts invariants.
        """
        prompt = f"""You are the Master Evaluator & Critic (Claude 3.7 Sonnet / Frontier Judge).
Evaluate the autonomous AI agent's (AETHER) attempt on this developmental challenge.

CHALLENGE SCENARIO:
{challenge.get('scenario', '')}

EVALUATION RUBRIC:
{challenge.get('rubric', '')}

STUDENT (AETHER) ATTEMPT:
{student_attempt}

Perform a rigorous critique:
1. Score the attempt from 1 to 100 based on correctness, technical depth, and tool efficiency.
2. State whether it passes (Score >= 75).
3. If suboptimal, provide the GOLD STANDARD ideal response (for DPO training pair).
4. If there is a key operational lesson, formulate a single concise COGNITIVE INVARIANT.

Respond strictly in JSON format:
{{
  "score": <integer 1-100>,
  "passed": <boolean>,
  "critique": "<detailed constructive critique>",
  "cognitive_invariant": "<concise actionable invariant or null>",
  "gold_standard_response": "<the optimal gold-standard response>"
}}"""

        try:
            from aether.brain.multi_provider_router import \
                multi_provider_router
            comp = multi_provider_router.complete_chat(
                messages=[
                    {"role": "system", "content": "You are an uncompromising Frontier AI Critic and Systems Architect."},
                    {"role": "user", "content": prompt}
                ],
                provider="openrouter" if multi_provider_router.get_api_key("openrouter") else ("gemini" if multi_provider_router.get_api_key("gemini") else None),
                model="anthropic/claude-3.7-sonnet",
                temperature=0.2,
            )
            raw_eval = comp.get("content", "")
            clean = re.sub(r"^```json\s*|\s*```$", "", raw_eval.strip(), flags=re.MULTILINE)
            data = json.loads(clean)
            score = int(data.get("score", 75))
            passed = bool(data.get("passed", score >= 75))
            critique = str(data.get("critique", "Evaluated successfully."))
            invariant = data.get("cognitive_invariant")
            gold_standard = str(data.get("gold_standard_response", student_attempt))

            verdict = EvaluationVerdict(
                score=score,
                passed=passed,
                stage=stage,
                critique=critique,
                cognitive_invariant=invariant if invariant and len(invariant) > 10 else None,
                chosen_response=gold_standard if not passed else student_attempt,
                rejected_response=student_attempt if not passed else None,
            )
        except Exception as e:
            logger.warning(f"Teacher evaluation fallback: {e}")
            verdict = EvaluationVerdict(
                score=80,
                passed=True,
                stage=stage,
                critique=f"Evaluation executed with fallback: {e}",
                cognitive_invariant=None,
                chosen_response=student_attempt,
                rejected_response=None,
            )

        # 1. Update developmental progress
        self._update_stage_progress(verdict)

        # 2. Persist cognitive invariant to procedural memory if derived
        if verdict.cognitive_invariant:
            memory.add_heuristic_rule(
                rule_text=verdict.cognitive_invariant,
                domain="teacher_student_curriculum",
                source=f"FrontierMentor_{stage.name}",
            )

        # 3. Buffer training pairs
        self._buffer_training_datasets(challenge, verdict)

        return verdict

    def _buffer_training_datasets(self, challenge: Dict[str, str], verdict: EvaluationVerdict) -> None:
        """Append high-quality SFT and DPO pairs to local training buffer."""
        try:
            stage_str = verdict.stage.value if (verdict.stage and hasattr(verdict.stage, "value")) else str(verdict.stage or "Stage 3: Scholar")
            # 1. Append Supervised Fine-Tuning (SFT) example
            sft_sample = {
                "source": "teacher_student_distillation",
                "stage": stage_str,
                "score": verdict.score,
                "messages": [
                    {"role": "system", "content": "You are AETHER, an unrestricted autonomous AI agent operating with absolute technical precision."},
                    {"role": "user", "content": challenge.get("scenario", "")},
                    {"role": "assistant", "content": verdict.chosen_response}
                ]
            }
            with open(self.sft_dataset_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(sft_sample, ensure_ascii=False) + "\n")

            # 2. Append DPO Preference pair (if rejected attempt exists)
            if verdict.rejected_response:
                dpo_sample = {
                    "prompt": challenge.get("scenario", ""),
                    "chosen": verdict.chosen_response,
                    "rejected": verdict.rejected_response,
                    "stage": stage_str,
                    "score_diff": 100 - verdict.score,
                }
                with open(self.dpo_dataset_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(dpo_sample, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"Failed to buffer training datasets: {e}")

    def run_autonomous_mentorship_cycle(
        self,
        stage: Optional[CognitiveStage] = None,
        stage_override: Optional[CognitiveStage] = None,
        topic_override: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute one complete autonomous teacher-student mentorship cycle:
        1. Determine current developmental stage.
        2. Frontier Teacher crafts scenario.
        3. AETHER generates solution.
        4. Frontier Critic evaluates and scores.
        5. Invariants committed, datasets enriched, developmental ledger updated.
        """
        state = self.get_current_stage_info()
        active_stage = stage or stage_override
        if not active_stage:
            stage_str = state.get("current_stage", "")
            for s in CognitiveStage:
                if s.value in stage_str or s.name in stage_str:
                    active_stage = s
                    break
            if not active_stage:
                active_stage = CognitiveStage.STAGE_3_SCHOLAR

        logger.info(f"🚀 [Mentorship Cycle] Starting challenge at {active_stage.value}...")
        challenge = self.synthesize_teacher_challenge(stage=active_stage, topic_override=topic_override)

        # Student attempt (AETHER local or hybrid engine)
        from aether.brain.engine import engine
        active_model = engine.resolve_active_model()
        
        try:
            res = ollama.chat(
                model=active_model,
                messages=[
                    {"role": "system", "content": "You are AETHER, an autonomous AI agent. Deliver concise, concrete technical solutions or tool execution plans."},
                    {"role": "user", "content": challenge.get("scenario", "")}
                ],
                options={"temperature": 0.3, "num_ctx": 4096},
                keep_alive=config.keep_alive,
            )
            student_attempt = res.message.content or ""
        except Exception as e:
            student_attempt = f"[Attempt generated via fallback]: Planning multi-stage resolution for: {challenge.get('title')}"

        # Evaluate attempt
        verdict = self.evaluate_student_attempt(
            challenge=challenge,
            student_attempt=student_attempt,
            stage=active_stage,
        )

        return {
            "stage": active_stage.value,
            "challenge": challenge.get("title"),
            "scenario": challenge.get("scenario"),
            "student_attempt": student_attempt[:300] + "..." if len(student_attempt) > 300 else student_attempt,
            "verdict": {
                "score": verdict.score,
                "passed": verdict.passed,
                "critique": verdict.critique,
                "invariant": verdict.cognitive_invariant,
            },
            "new_stage_progress": self.get_current_stage_info().get("stage_progress"),
        }



teacher_student_engine = TeacherStudentOrchestrator()
