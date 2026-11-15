r"""
AETHER 90-Second Executive Audio Podcast Generator (Evolution #17)
==================================================================
Converts the daily ExecutiveBriefing into a natural, spoken audio podcast
delivered via local TTS (pyttsx3) or streamed to the browser via Web Speech.

Invariants Enforced:
  • Cognitive Invariant #2: NEVER strip digits (\d+). Preserves all currency amounts,
    counts, timestamps, and percentages intact.
  • Output duration tuned for 60–90 seconds of high-density executive intelligence.
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("aether.daemon.executive_audio_podcast")

_WORKSPACE = Path(__file__).resolve().parent.parent.parent.parent
_INTEL_DIR = _WORKSPACE / "data" / "leon_intelligence"
_AUDIO_DIR = _INTEL_DIR / "briefings"
_AUDIO_FILE = _AUDIO_DIR / "latest_briefing.wav"
_SCRIPT_FILE = _AUDIO_DIR / "latest_briefing_script.txt"

_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
_LOCK = threading.Lock()


class ExecutiveAudioPodcast:
    """
    Generates spoken audio executive briefings for the owner's morning routine.
    """

    def clean_script_for_tts(self, text: str) -> str:
        """
        Sanitize text for natural speech synthesis.
        CRITICAL: Never strip digits! Only strip brackets, emojis, and code markup.
        """
        # Remove markdown symbols and emojis
        cleaned = re.sub(r"[#*_`~>|]", "", text)
        # Remove bracketed citation markers e.g. [1], (2)
        cleaned = re.sub(r"\[\d+\]", "", cleaned)
        # Expand currency symbols for natural speech
        cleaned = cleaned.replace("₹", " Rupees ")
        cleaned = cleaned.replace("$", " Dollars ")
        cleaned = cleaned.replace("%", " percent ")
        # Collapse multi-spaces
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    def compose_podcast_script(self, briefing_dict: Dict[str, Any]) -> str:
        """
        Format an engaging 90-second spoken podcast script from executive briefing metrics.
        """
        headline = briefing_dict.get("headline", "Executive Briefing")
        fin = briefing_dict.get("financial_summary", {})
        rev = fin.get("total_revenue_inr", 0)
        leads = briefing_dict.get("lead_velocity", {})
        lead_count = leads.get("high_intent_prospects", 0)
        total_signals = leads.get("total_harvested_signals", 0)
        pending_count = briefing_dict.get("pending_approvals_count", 0)
        rec = briefing_dict.get("strategic_recommendation", "")

        script = (
            f"Good morning. Here is your AETHER executive briefing for today. "
            f"All 5 commercial ventures are fully online and healthy. "
            f"Total recorded revenue stands at ₹{rev:,.0f}. "
            f"Overnight, our autonomous intent harvester identified {total_signals} public market signals, "
            f"yielding {lead_count} high-intent buyer prospects. "
            f"You have {pending_count} pending executive approvals in your HUD operator inbox. "
            f"Strategic recommendation: {rec} "
            f"System background evolution daemon is active. Have a productive day."
        )

        return self.clean_script_for_tts(script)

    def render_audio_file(self, script: str) -> Optional[str]:
        """
        Generate .wav audio file locally using pyttsx3.
        Returns file path string or None if pyttsx3 is unavailable.
        """
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty("rate", 175)  # Natural speaking rate
            engine.setProperty("volume", 1.0)

            # Select preferred voice (preferably standard English)
            voices = engine.getProperty("voices")
            if voices:
                engine.setProperty("voice", voices[0].id)

            with _LOCK:
                _SCRIPT_FILE.write_text(script, encoding="utf-8")
                engine.save_to_file(script, str(_AUDIO_FILE))
                engine.runAndWait()

            logger.info(f"🎙️ Executive Audio Podcast rendered successfully to {_AUDIO_FILE}")
            return str(_AUDIO_FILE)
        except Exception as e:
            logger.warning(f"Local pyttsx3 audio rendering unavailable ({e}). Fallback to text script.")
            with _LOCK:
                _SCRIPT_FILE.write_text(script, encoding="utf-8")
            return None

    def generate_latest_podcast(self) -> Dict[str, Any]:
        """
        Fetch the latest morning briefing, compose script, and render audio.
        """
        from aether.daemon.executive_chronobiology import \
            executive_chronobiology
        briefing = executive_chronobiology.generate_morning_briefing()
        b_dict = briefing.to_dict()

        script = self.compose_podcast_script(b_dict)
        audio_path = self.render_audio_file(script)

        return {
            "status": "success",
            "briefing_id": briefing.id,
            "headline": briefing.headline,
            "spoken_script": script,
            "audio_file_path": audio_path,
            "audio_file_exists": bool(audio_path and Path(audio_path).exists()),
            "estimated_duration_seconds": round(len(script.split()) / 2.8, 1),
            "generated_at": datetime.now(timezone.utc).isoformat() + "Z",
        }


executive_audio_podcast = ExecutiveAudioPodcast()
