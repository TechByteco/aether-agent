"""
AETHER Multi-Agent Swarm Orchestrator Engine
============================================
Coordinates specialized autonomous agents (Planner, Architect, Coder,
Reviewer, Security Auditor, Researcher, Synthesizer) to solve complex tasks
through sequential pipelines, dialectic debate, and collaborative execution.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional

from aether.brain.ast_guard import ast_guard
from aether.brain.swarm.swarm_agent import SwarmAgent, SwarmMessage, SwarmRole
from aether.memory.store import memory
from aether.tools.code_sandbox import execute_python_code

logger = logging.getLogger("aether.swarm.engine")


class SwarmEngine:
    """Orchestrator for autonomous multi-agent teamwork and collaborative execution."""

    def __init__(self):
        self.agents: Dict[SwarmRole, SwarmAgent] = {
            SwarmRole.PLANNER: SwarmAgent("PlannerPrime", SwarmRole.PLANNER),
            SwarmRole.ARCHITECT: SwarmAgent("ArchitectNode", SwarmRole.ARCHITECT),
            SwarmRole.CODER: SwarmAgent("CoderCore", SwarmRole.CODER),
            SwarmRole.REVIEWER: SwarmAgent("ReviewerSentinel", SwarmRole.REVIEWER),
            SwarmRole.SECURITY_AUDITOR: SwarmAgent("SecurityVanguard", SwarmRole.SECURITY_AUDITOR),
            SwarmRole.RESEARCHER: SwarmAgent("KnowledgeScout", SwarmRole.RESEARCHER),
            SwarmRole.SYNTHESIZER: SwarmAgent("SynthesisDirector", SwarmRole.SYNTHESIZER),
        }
        self.mission_history: List[Dict[str, Any]] = []

    def get_agent(self, role: SwarmRole) -> SwarmAgent:
        """Get or create agent for a specific role."""
        if role not in self.agents:
            self.agents[role] = SwarmAgent(f"{role.value.capitalize()}Agent", role)
        return self.agents[role]

    def run_sequential_pipeline(
        self,
        task: str,
        roles: Optional[List[SwarmRole]] = None,
        execute_code_sandbox: bool = True,
    ) -> Dict[str, Any]:
        """
        Execute a sequential multi-agent pipeline:
        Planner -> Architect -> Coder -> Reviewer -> (Sandbox) -> Synthesizer.
        """
        pipeline_roles = roles or [
            SwarmRole.PLANNER,
            SwarmRole.ARCHITECT,
            SwarmRole.CODER,
            SwarmRole.REVIEWER,
            SwarmRole.SYNTHESIZER,
        ]

        logger.info(f"🐝 [Swarm Pipeline] Starting mission: '{task[:60]}...' with {len(pipeline_roles)} agents.")
        transcript: List[SwarmMessage] = []
        mission_id = f"mission_{int(datetime.now(timezone.utc).timestamp())}"

        for role in pipeline_roles:
            agent = self.get_agent(role)
            logger.info(f"🐝 [Swarm Turn] Executing {agent.name} ({role.value})...")
            
            # Formulate turn context from preceding messages
            context_summary = "\n\n".join(
                [f"### [{msg.sender} - {msg.role.value}]\n{msg.content}" for msg in transcript]
            )

            msg = agent.execute(task=task, history=transcript, additional_context=context_summary)
            transcript.append(msg)

            # If this is the coder and sandbox execution is requested, validate code
            if role == SwarmRole.CODER and execute_code_sandbox:
                code_blocks = self._extract_python_code(msg.content)
                if code_blocks:
                    # AST validation
                    ast_ok, ast_msg, ast_analysis = ast_guard.validate_or_repair_code(code_blocks[0])
                    msg.artifacts["ast_valid"] = ast_ok
                    msg.artifacts["ast_message"] = ast_msg

                    # Sandbox execution
                    sandbox_res = execute_python_code(code_blocks[0])
                    msg.artifacts["sandbox_output"] = sandbox_res[:500]

        # Record mission in memory
        mission_record = {
            "mission_id": mission_id,
            "task": task,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "pipeline": [r.value for r in pipeline_roles],
            "transcript": [m.to_dict() for m in transcript],
            "summary": transcript[-1].content if transcript else "",
        }
        self.mission_history.append(mission_record)

        # Store in episodic memory
        try:
            memory.add_episode(
                user_message=f"[Swarm Mission] {task}",
                assistant_response=mission_record["summary"],
                tools_used=[f"swarm_{r.value}" for r in pipeline_roles],
            )
        except Exception as e:
            logger.warning(f"Failed to record swarm mission in memory: {e}")

        return mission_record

    def run_dialectic_debate(
        self,
        topic: str,
        rounds: int = 2,
    ) -> Dict[str, Any]:
        """
        Execute a dialectic consensus debate between Architect, Security Auditor, and Reviewer.
        """
        debate_agents = [
            self.get_agent(SwarmRole.ARCHITECT),
            self.get_agent(SwarmRole.SECURITY_AUDITOR),
            self.get_agent(SwarmRole.REVIEWER),
        ]

        transcript: List[SwarmMessage] = []
        for r in range(rounds):
            for agent in debate_agents:
                context_summary = "\n\n".join(
                    [f"### [{msg.sender} ({msg.role.value})]\n{msg.content}" for msg in transcript]
                )
                msg = agent.execute(
                    task=f"Debate topic: {topic}. Analyze, critique previous arguments, and reach rigorous consensus.",
                    history=transcript,
                    additional_context=context_summary,
                )
                transcript.append(msg)

        # Final synthesis
        synthesizer = self.get_agent(SwarmRole.SYNTHESIZER)
        final_summary = synthesizer.execute(
            task=f"Synthesize the debate on '{topic}' and state the definitive architectural verdict.",
            history=transcript,
        )
        transcript.append(final_summary)

        return {
            "topic": topic,
            "rounds": rounds,
            "transcript": [m.to_dict() for m in transcript],
            "verdict": final_summary.content,
        }

    async def run_swarm_stream(
        self,
        task: str,
        roles: Optional[List[SwarmRole]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Async generator yielding real-time agent turn events for live WebSocket streaming.
        """
        pipeline_roles = roles or [
            SwarmRole.PLANNER,
            SwarmRole.ARCHITECT,
            SwarmRole.CODER,
            SwarmRole.REVIEWER,
            SwarmRole.SYNTHESIZER,
        ]

        yield {
            "type": "swarm_started",
            "task": task,
            "roles": [r.value for r in pipeline_roles],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        transcript: List[SwarmMessage] = []
        loop = asyncio.get_event_loop()

        for idx, role in enumerate(pipeline_roles):
            agent = self.get_agent(role)
            yield {
                "type": "agent_started",
                "index": idx,
                "role": role.value,
                "agent_name": agent.name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            context_summary = "\n\n".join(
                [f"### [{msg.sender} - {msg.role.value}]\n{msg.content}" for msg in transcript]
            )

            # Run in thread pool executor to not block asyncio event loop
            msg = await loop.run_in_executor(
                None,
                lambda a=agent, ctx=context_summary: a.execute(
                    task=task,
                    history=transcript,
                    additional_context=ctx,
                )
            )
            transcript.append(msg)

            yield {
                "type": "agent_finished",
                "index": idx,
                "role": role.value,
                "agent_name": agent.name,
                "content": msg.content,
                "artifacts": msg.artifacts,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        yield {
            "type": "swarm_completed",
            "task": task,
            "summary": transcript[-1].content if transcript else "",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _extract_python_code(self, text: str) -> List[str]:
        """Helper to extract python blocks."""
        import re
        return re.findall(r"```(?:python)?\s*(.*?)\s*```", text, re.DOTALL)


swarm_engine = SwarmEngine()
