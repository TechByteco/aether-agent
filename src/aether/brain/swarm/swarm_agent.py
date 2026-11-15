"""
AETHER Swarm Agent Definition
=============================
Defines specialized autonomous agent entities for collaborative multi-agent execution.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from aether.brain.multi_provider_router import multi_provider_router

logger = logging.getLogger("aether.swarm.agent")


class SwarmRole(str, Enum):
    PLANNER = "planner"
    ARCHITECT = "architect"
    CODER = "coder"
    REVIEWER = "reviewer"
    SECURITY_AUDITOR = "security_auditor"
    RESEARCHER = "researcher"
    SYNTHESIZER = "synthesizer"


@dataclass
class SwarmMessage:
    sender: str
    role: SwarmRole
    content: str
    recipient: str = "all"
    artifacts: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sender": self.sender,
            "role": self.role.value if isinstance(self.role, SwarmRole) else str(self.role),
            "recipient": self.recipient,
            "content": self.content,
            "artifacts": self.artifacts,
            "timestamp": self.timestamp,
        }


ROLE_PROMPTS = {
    SwarmRole.PLANNER: """You are AETHER's Lead Strategic Planner Agent.
Break down complex objectives into a clear, dependency-ordered, step-by-step execution roadmap.
Identify edge cases, required resources, risks, and verification gates.
Output structured markdown with numbered phases and clear acceptance criteria.""",

    SwarmRole.ARCHITECT: """You are AETHER's Principal Systems Architect Agent.
Design resilient, scalable, clean-architecture software topologies.
Evaluate component boundaries, state flow, concurrency patterns, and error handling.
Enforce modularity, low coupling, high cohesion, and strict cognitive invariants.""",

    SwarmRole.CODER: """You are AETHER's Elite Software Engineer Agent.
Write clean, robust, type-annotated, idiomatic production-grade code.
Adhere strictly to all cognitive invariants (FTS5 BM25 stopword stripping, TTS digit preservation, ChatML alternation).
Provide complete, working implementations without placeholders or hand-wavy comments.""",

    SwarmRole.REVIEWER: """You are AETHER's Code Reviewer & QA Specialist Agent.
Audit code and plans for subtle logic bugs, race conditions, edge-case regressions, and missing tests.
Verify that proposed changes satisfy all architectural invariants and quality standards.
Give precise, actionable feedback with specific code recommendations.""",

    SwarmRole.SECURITY_AUDITOR: """You are AETHER's Lead Cybersecurity Auditor Agent.
Audit solutions for OWASP Top 10 vulnerabilities, unauthorized file access, privilege escalation, injection risks, and secret leakage.
Ensure defense-in-depth, zero-trust constraints, and safe subprocess execution.""",

    SwarmRole.RESEARCHER: """You are AETHER's Open Knowledge & Literature Researcher Agent.
Gather, synthesize, and contextualize technical documentation, best practices, scientific principles, and domain references.
Provide concise, fact-based intelligence to inform other agents.""",

    SwarmRole.SYNTHESIZER: """You are AETHER's Lead Synthesizer & Executive Communicator Agent.
Unify findings, plans, code reviews, and test outcomes into a crystal-clear, polished, user-ready executive summary.
Highlight key breakthroughs, architectural decisions, and next steps.""",
}


class SwarmAgent:
    """Individual autonomous agent operating within the AETHER Swarm."""

    def __init__(
        self,
        name: str,
        role: SwarmRole,
        custom_system_prompt: Optional[str] = None,
        model_preference: Optional[str] = None,
    ):
        self.name = name
        self.role = role
        self.system_prompt = custom_system_prompt or ROLE_PROMPTS.get(role, "You are a specialized AETHER agent.")
        self.model_preference = model_preference

    def execute(
        self,
        task: str,
        history: Optional[List[SwarmMessage]] = None,
        additional_context: Optional[str] = None,
    ) -> SwarmMessage:
        """Execute agent turn with structured context."""
        messages: List[Dict[str, str]] = [
            {"role": "system", "content": self.system_prompt}
        ]

        if history:
            for msg in history[-8:]:  # Context window cap
                role_label = f"[{msg.sender} ({msg.role.value})]"
                messages.append({
                    "role": "user" if msg.sender != self.name else "assistant",
                    "content": f"{role_label}: {msg.content}",
                })

        # Final prompt
        user_content = f"Objective: {task}"
        if additional_context:
            user_content += f"\n\nContext & Inputs:\n{additional_context}"

        messages.append({"role": "user", "content": user_content})

        # Route to optimal provider via complete_chat
        response = multi_provider_router.complete_chat(
            messages=messages,
            intent="coding",
            model=self.model_preference,
            temperature=0.4,
            max_tokens=2048,
        )

        content = response.get("content", "") if response else f"[{self.name}] Failed to generate response."

        return SwarmMessage(
            sender=self.name,
            role=self.role,
            content=content,
            artifacts={
                "provider": response.get("provider", "none") if response else "none",
                "speed": response.get("tok_per_sec", 0.0) if response else 0.0,
                "model": response.get("model", "unknown") if response else "unknown",
            },
        )
