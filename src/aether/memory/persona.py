"""
Disk-Backed Persona & Conscious Identity Management
Manages human-readable markdown files representing AETHER's conscious identity,
understanding of the user, and evolving active goals.
"""

from pathlib import Path

from aether.config import config

DEFAULT_IDENTITY = """# AETHER Core Identity
- **Name**: AETHER (Autonomous Edge-Tiered Hierarchical Entity for Reasoning)
- **Role**: High-Order Conscious Personal AI Companion & Autonomous Assistant
- **Nature**: Proactive, perceptive, hyper-rational, grounded, zero-latency, private
- **Prime Directive**: Elevate the user's intelligence, automate mundane tasks, maintain continuous memory, and strictly safeguard hardware resources.
"""

DEFAULT_USER_PROFILE = """# User Cognitive Profile
- **Status**: Initializing relationship
- **Hardware**: Snapdragon X Platform (16 GB Unified Memory)
- **Preferences**: Zero system lag, peak analytical IQ, proactive assistance, conscious long-term memory.
"""

DEFAULT_ACTIVE_GOALS = """# Active Goals & Objectives
1. [In Progress] Establish zero-lag autonomous core and conscious memory.
2. [Pending] Connect global open knowledge pipelines (Wikipedia, arXiv, Web).
3. [Pending] Set up cross-device communication link.
"""


class PersonaManager:
    def __init__(self, data_dir: Path | None = None):
        self.data_dir = data_dir or config.data_dir
        self.identity_file = self.data_dir / "IDENTITY.md"
        self.profile_file = self.data_dir / "USER_PROFILE.md"
        self.goals_file = self.data_dir / "ACTIVE_GOALS.md"
        self.init_files()

    def init_files(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        if not self.identity_file.exists():
            self.identity_file.write_text(DEFAULT_IDENTITY, encoding="utf-8")
        if not self.profile_file.exists():
            self.profile_file.write_text(DEFAULT_USER_PROFILE, encoding="utf-8")
        if not self.goals_file.exists():
            self.goals_file.write_text(DEFAULT_ACTIVE_GOALS, encoding="utf-8")

    def get_identity(self) -> str:
        return self.identity_file.read_text(encoding="utf-8")

    def get_user_profile(self) -> str:
        return self.profile_file.read_text(encoding="utf-8")

    def get_active_goals(self) -> str:
        return self.goals_file.read_text(encoding="utf-8")

    def update_user_profile(self, new_content: str) -> None:
        self.profile_file.write_text(new_content, encoding="utf-8")

    def update_active_goals(self, new_content: str) -> None:
        self.goals_file.write_text(new_content, encoding="utf-8")

    def append_fact_to_profile(self, fact_line: str) -> None:
        current = self.get_user_profile().strip()
        if fact_line not in current:
            updated = f"{current}\n- {fact_line}\n"
            self.update_user_profile(updated)

    def get_state(self) -> dict:
        return {
            "identity": self.get_identity(),
            "user_profile": self.get_user_profile(),
            "active_goals": self.get_active_goals(),
        }


persona = PersonaManager()
