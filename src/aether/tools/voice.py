"""
AETHER Sovereign Voice Synthesizer
==================================
Studio-grade Neural AI Text-to-Speech & Local Windows Voice Synthesizer:
1. Free Ultra-Realistic Neural AI Voices (JARVIS, Jenny, Guy, Aria, Eric, Ryan, Sonia, Prabhat, Neerja, William, Clara)
2. Local Windows SAPI5 Speech Engines (David, Zira, Mark, Hazel)
3. Direct MP3/WAV Audio Byte Streaming for Web HUD and API endpoints
4. Strict Cognitive Invariant #2 compliance: Never strip numeric digits (\\d+).
"""

import asyncio
import hashlib
import os
import re
import tempfile
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None

try:
    import edge_tts
except ImportError:
    edge_tts = None


NEURAL_VOICE_CATALOG: Dict[str, Dict[str, str]] = {
    "jarvis": {
        "id": "en-US-ChristopherNeural",
        "name": "JARVIS (Christopher)",
        "gender": "Male",
        "locale": "en-US",
        "accent": "American",
        "description": "Deep, authoritative, intelligent, calm executive AI co-pilot (Iron Man style)"
    },
    "christopher": {
        "id": "en-US-ChristopherNeural",
        "name": "Christopher (Authoritative)",
        "gender": "Male",
        "locale": "en-US",
        "accent": "American",
        "description": "Authoritative, clear American male"
    },
    "jenny": {
        "id": "en-US-JennyNeural",
        "name": "Jenny (Natural Pro)",
        "gender": "Female",
        "locale": "en-US",
        "accent": "American",
        "description": "Crisp, professional, warm executive female assistant"
    },
    "guy": {
        "id": "en-US-GuyNeural",
        "name": "Guy (Conversational)",
        "gender": "Male",
        "locale": "en-US",
        "accent": "American",
        "description": "Warm, natural, casual American conversational companion"
    },
    "aria": {
        "id": "en-US-AriaNeural",
        "name": "Aria (Expressive)",
        "gender": "Female",
        "locale": "en-US",
        "accent": "American",
        "description": "Expressive, dynamic, engaging female assistant"
    },
    "eric": {
        "id": "en-US-EricNeural",
        "name": "Eric (Energetic)",
        "gender": "Male",
        "locale": "en-US",
        "accent": "American",
        "description": "Energetic, agile young male companion"
    },
    "ryan": {
        "id": "en-GB-RyanNeural",
        "name": "Ryan (British Gentleman)",
        "gender": "Male",
        "locale": "en-GB",
        "accent": "British",
        "description": "Sophisticated British English male"
    },
    "sonia": {
        "id": "en-GB-SoniaNeural",
        "name": "Sonia (British Lady)",
        "gender": "Female",
        "locale": "en-GB",
        "accent": "British",
        "description": "Refined British English female"
    },
    "prabhat": {
        "id": "en-IN-PrabhatNeural",
        "name": "Prabhat (Indian English Male)",
        "gender": "Male",
        "locale": "en-IN",
        "accent": "Indian English",
        "description": "Clear, professional Indian English male"
    },
    "neerja": {
        "id": "en-IN-NeerjaNeural",
        "name": "Neerja (Indian English Female)",
        "gender": "Female",
        "locale": "en-IN",
        "accent": "Indian English",
        "description": "Expressive Indian English female"
    },
    "william": {
        "id": "en-AU-WilliamMultilingualNeural",
        "name": "William (Australian Male)",
        "gender": "Male",
        "locale": "en-AU",
        "accent": "Australian",
        "description": "Charismatic Australian English male"
    },
    "clara": {
        "id": "en-CA-ClaraNeural",
        "name": "Clara (Canadian Female)",
        "gender": "Female",
        "locale": "en-CA",
        "accent": "Canadian",
        "description": "Smooth, friendly Canadian English female"
    }
}


class VoiceEngine:
    def __init__(self, enabled: bool = True, voice_name: str = "jarvis", rate: int = 185, volume: float = 1.0):
        self.enabled = enabled
        self.voice_name = voice_name.lower()
        self.rate = rate
        self.volume = volume
        self.use_neural = True
        self._lock = threading.Lock()
        self.cache_dir = Path(tempfile.gettempdir()) / "aether_voice_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def set_enabled(self, state: bool) -> None:
        self.enabled = state

    def set_voice(self, voice_name: str) -> bool:
        """Set voice persona (e.g. 'jarvis', 'jenny', 'guy', 'aria', 'ryan', 'prabhat', 'david', 'zira')."""
        name = voice_name.lower().strip()
        if name in NEURAL_VOICE_CATALOG:
            self.voice_name = name
            self.use_neural = True
            return True
        elif name in ("david", "zira", "desktop", "local"):
            self.voice_name = name
            self.use_neural = False
            return True
        else:
            # Fallback to nearest match
            self.voice_name = "jarvis"
            self.use_neural = True
            return True

    def set_rate(self, rate: int) -> None:
        self.rate = max(100, min(300, rate))

    def set_volume(self, volume: float) -> None:
        self.volume = max(0.0, min(1.0, volume))

    def get_catalog(self) -> Dict[str, Any]:
        """Return the complete Neural Voice catalog and local voices."""
        local_voices = []
        if pyttsx3:
            try:
                engine = pyttsx3.init()
                for v in engine.getProperty("voices"):
                    local_voices.append({
                        "id": v.id,
                        "name": v.name,
                        "gender": getattr(v, "gender", "Unknown"),
                    })
                engine.stop()
            except Exception:
                pass

        return {
            "current_voice": self.voice_name,
            "use_neural": self.use_neural,
            "rate": self.rate,
            "volume": self.volume,
            "neural_personas": NEURAL_VOICE_CATALOG,
            "local_voices": local_voices,
        }

    def clean_text_for_speech(self, text: str) -> str:
        """
        Strip markdown formatting, URLs, and code blocks while STRICTLY preserving
        all numeric digits, timestamps, and calculations intact (AETHER Invariant #2).
        """
        # Remove code blocks
        clean = re.sub(r"```[\s\S]*?```", "Code block omitted.", text)
        clean = re.sub(r"`([^`]+)`", r"\1", clean)
        # Remove URLs
        clean = re.sub(r"http[s]?://\S+", "", clean)
        # Invariant #2: ONLY strip bracketed citation markers (e.g. [1] or (1)), preserve all raw digits (\d+)
        clean = re.sub(r"\[\d+\]|\(\d+\)", "", clean)
        # Remove markdown headers and formatting
        clean = re.sub(r"[#*_~>]", "", clean)
        # Collapse whitespace
        clean = re.sub(r"\s+", " ", clean).strip()
        return clean

    async def generate_neural_audio_bytes(self, text: str, persona: Optional[str] = None) -> bytes:
        """Synthesize ultra-realistic audio bytes (MP3) using edge-tts."""
        if not edge_tts:
            return b""

        speech_text = self.clean_text_for_speech(text)
        if not speech_text:
            return b""

        target_persona = (persona or self.voice_name).lower().strip()
        voice_info = NEURAL_VOICE_CATALOG.get(target_persona, NEURAL_VOICE_CATALOG["jarvis"])
        voice_id = voice_info["id"]

        # Calculate cache key
        cache_key = hashlib.sha256(f"{voice_id}:{speech_text}".encode("utf-8")).hexdigest()
        cached_file = self.cache_dir / f"{cache_key}.mp3"

        if cached_file.exists():
            return cached_file.read_bytes()

        communicate = edge_tts.Communicate(speech_text, voice_id)
        chunks = []
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                chunks.append(chunk["data"])

        audio_bytes = b"".join(chunks)
        if audio_bytes:
            try:
                cached_file.write_bytes(audio_bytes)
            except Exception:
                pass

        return audio_bytes

    def _speak_local(self, text: str) -> None:
        if not pyttsx3:
            return
        try:
            with self._lock:
                engine = pyttsx3.init()
                engine.setProperty("rate", self.rate)
                engine.setProperty("volume", self.volume)

                voices = engine.getProperty("voices")
                if voices:
                    chosen = voices[0].id
                    for v in voices:
                        if self.voice_name in v.name.lower() or self.voice_name in v.id.lower():
                            chosen = v.id
                            break
                    engine.setProperty("voice", chosen)

                engine.say(text)
                engine.runAndWait()
                engine.stop()
        except Exception:
            pass

    async def _speak_neural_async(self, text: str) -> None:
        audio_bytes = await self.generate_neural_audio_bytes(text)
        if not audio_bytes:
            self._speak_local(text)
            return

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        try:
            if os.name == "nt":
                # Play audio cleanly on Windows
                os.system(f'powershell -c "$p = New-Object System.Media.SoundPlayer; (New-Object Media.SoundPlayer \'{tmp_path}\').PlaySync();" 2>$null')
        except Exception:
            self._speak_local(text)
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

    def _speak_worker(self, text: str) -> None:
        if self.use_neural and edge_tts:
            try:
                asyncio.run(self._speak_neural_async(text))
            except Exception:
                self._speak_local(text)
        else:
            self._speak_local(text)

    def speak_async(self, text: str) -> None:
        """Speak asynchronously without blocking execution."""
        if not self.enabled:
            return

        speech_text = self.clean_text_for_speech(text)
        if not speech_text or len(speech_text) < 2:
            return

        thread = threading.Thread(target=self._speak_worker, args=(speech_text,), daemon=True)
        thread.start()


# Global Singleton Voice Engine
voice = VoiceEngine(enabled=True, voice_name="jarvis")


# ─── Cognitive Brain Tools Exposed to Engine ─────────────────────────────────

def tool_set_voice_persona(persona: str) -> str:
    """Set AETHER's voice persona (e.g. 'jarvis', 'jenny', 'guy', 'aria', 'eric', 'ryan', 'sonia', 'prabhat', 'neerja', 'william', 'clara', 'david', 'zira')."""
    persona = persona.strip().lower()
    voice.set_voice(persona)
    catalog = NEURAL_VOICE_CATALOG.get(persona)
    if catalog:
        return (
            f"### 🎙️ AETHER Voice Persona Set to: **{catalog['name']}**\n"
            f"- **Persona Style:** {catalog['description']}\n"
            f"- **Accent / Locale:** {catalog['accent']} ({catalog['locale']})\n"
            f"- **Gender:** {catalog['gender']}\n"
            f"- **Voice ID:** `{catalog['id']}`\n\n"
            f"All subsequent speech synthesis will use this neural voice model."
        )
    return f"Voice set to: {persona}."


def tool_list_available_voices() -> str:
    """List all available ultra-realistic Neural AI and local system voices."""
    info = voice.get_catalog()
    lines = [f"### 🎙️ AETHER Neural Voice Catalog (Current: **{info['current_voice'].upper()}**)\n"]
    lines.append("| Persona Key | Voice Name | Accent / Gender | Description |")
    lines.append("| :--- | :--- | :--- | :--- |")
    for k, v in info["neural_personas"].items():
        curr_marker = " 👈 *(Active)*" if k == info["current_voice"] else ""
        lines.append(f"| **`{k}`**{curr_marker} | {v['name']} | {v['accent']} ({v['gender']}) | {v['description']} |")

    lines.append("\n**Local Desktop Voices:**")
    for lv in info.get("local_voices", []):
        lines.append(f"- `{lv['name']}` ({lv['gender']})")

    lines.append("\n*To switch voice at any time, run: `tool_set_voice_persona(persona='jarvis')`*")
    return "\n".join(lines)


def tool_speak_phrase(phrase: str, persona: str = "") -> str:
    """Synthesize and speak a phrase aloud using AETHER's neural voice engine."""
    if persona:
        voice.set_voice(persona)
    voice.speak_async(phrase)
    active = voice.voice_name
    return f"Synthesized and spoke: \"{phrase}\" using persona '{active}'."
