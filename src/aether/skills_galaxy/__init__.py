"""
AETHER Sovereign Skills Galaxy Package
======================================
Exposes 200 fully implemented and verified sovereign skills across:
- Windows 11 OS, UI & Hardware Deep Mastery (1 - 45)
- Networking, Package Management & Application Automation (46 - 95)
- Process Forensics, File Intelligence & Cryptography (96 - 120)
- Cognitive Reasoning, RLAIF, Media & Vision Automation (121 - 155)
- Systems Architecture, Venture Modeling & Math Computing (156 - 190)
- Continuous Model Training & Meta-Evolution (191 - 200)
"""

from aether.skills_galaxy.registry import (SKILLS_GALAXY_REGISTRY,
                                           collect_all_skills,
                                           generate_skills_training_dataset,
                                           get_skills_catalog,
                                           verify_all_skills)

__all__ = [
    "SKILLS_GALAXY_REGISTRY",
    "collect_all_skills",
    "get_skills_catalog",
    "verify_all_skills",
    "generate_skills_training_dataset",
]
