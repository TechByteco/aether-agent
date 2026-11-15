"""
AETHER Live Vision & Image Analysis Engine
Enables real-time screen capture, image preprocessing, and multi-modal neural vision.
Engineered for low RAM consumption, edge downsampling, and fast Snapdragon execution.
"""

import base64
import gc
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

import ollama
from PIL import Image

from aether.config import config


def capture_screen(
    max_dimension: int = 1280,
    output_path: Optional[Path] = None
) -> Path:
    """
    Capture the primary computer screen, downsample for optimal edge compute, and save to disk.
    """
    shots_dir = config.data_dir.parent / "screenshots"
    shots_dir.mkdir(parents=True, exist_ok=True)

    raw_path = shots_dir / "_raw_temp_screen.png"
    target_path = output_path or (shots_dir / f"screen_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg")

    # Native PowerShell display capture
    ps_script = f"""
    Add-Type -AssemblyName System.Windows.Forms;
    Add-Type -AssemblyName System.Drawing;
    $screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds;
    $bitmap = New-Object System.Drawing.Bitmap $screen.Width, $screen.Height;
    $graphic = [System.Drawing.Graphics]::FromImage($bitmap);
    $graphic.CopyFromScreen($screen.Location, [System.Drawing.Point]::Empty, $screen.Size);
    $bitmap.Save('{str(raw_path).replace("\\", "\\\\")}');
    $graphic.Dispose();
    $bitmap.Dispose();
    """
    subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], check=True, capture_output=True)

    # Edge downsampling via Pillow to minimize VRAM & latency
    try:
        with Image.open(raw_path) as img:
            w, h = img.size
            if max(w, h) > max_dimension:
                scale = max_dimension / max(w, h)
                new_w, new_h = int(w * scale), int(h * scale)
                img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            
            # Convert RGBA to RGB for JPEG optimization
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            
            img.save(target_path, "JPEG", quality=85, optimize=True)
    finally:
        if raw_path.exists():
            try:
                raw_path.unlink()
            except Exception:
                pass

    return target_path


def detect_available_vision_model() -> Optional[str]:
    """
    Detect the best installed vision model in Ollama.
    Prefers Qwen2-VL (superior OCR/screen reading) > moondream (ultra-fast edge) > others.
    """
    try:
        models_info = ollama.list()
        models = models_info.get("models", [])
        installed_names = [m.get("model", "") for m in models]

        # Priority order: Qwen2-VL (best OCR) → moondream (fastest) → fallbacks
        preferred = [
            "qwen2-vl:2b",
            "qwen2-vl:latest",
            "qwen2-vl",
            "moondream:latest",
            "moondream",
            "moondream:1.8b",
            "llama3.2-vision:latest",
            "llama3.2-vision",
            "llava:latest",
            "llava:7b",
            "minicpm-v:latest",
        ]

        for p in preferred:
            for name in installed_names:
                if name.startswith(p) or p in name:
                    return name
    except Exception:
        pass
    return None


def analyze_image(
    image_path: str,
    prompt: str = "Describe what you see in detail. Identify key elements, applications, active text, and context."
) -> str:
    """
    Perform deep multi-modal vision analysis on an image file.
    Uses capped context (config.vision_context = 2048) to avoid wasting ~500MB
    on unnecessary KV cache allocations — images need far fewer tokens than text.
    """
    p = Path(image_path).expanduser().resolve()
    if not p.exists() or not p.is_file():
        return f"Error: Image file '{image_path}' not found."

    vision_model = detect_available_vision_model()
    if not vision_model:
        return (
            "Vision model not currently loaded. Please run 'ollama pull qwen2-vl:2b' or "
            "'ollama pull moondream' to enable offline neural vision for AETHER."
        )

    # Downsample if image is excessively large
    downsampled_path = p
    try:
        with Image.open(p) as img:
            w, h = img.size
            if max(w, h) > 1280:
                scale = 1280 / max(w, h)
                resized = img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
                temp_downsample = config.data_dir.parent / "screenshots" / f"_temp_view_{p.name}.jpg"
                if resized.mode in ("RGBA", "P"):
                    resized = resized.convert("RGB")
                resized.save(temp_downsample, "JPEG", quality=85)
                downsampled_path = temp_downsample
    except Exception:
        pass

    try:
        # Pass image to Ollama multimodal chat
        # INVARIANT: keep_alive is a TOP-LEVEL arg, NOT inside options dict
        # Context capped to vision_context (2048) — images don't need 8192 tokens
        response = ollama.chat(
            model=vision_model,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                    "images": [str(downsampled_path)],
                }
            ],
            options={
                "num_ctx": config.vision_context,
                "num_thread": config.num_threads,
            },
            keep_alive=config.keep_alive,
        )
        content = response.message.content or "No visual details returned."
        return content.strip()
    except Exception as e:
        return f"Vision processing error: {str(e)}"
    finally:
        if downsampled_path != p and downsampled_path.exists():
            try:
                downsampled_path.unlink()
            except Exception:
                pass
        gc.collect()


def analyze_live_screen(
    prompt: str = "What is currently visible on my computer screen? Summarize the active application, window, and key content."
) -> str:
    """
    Take a live screenshot and immediately analyze its visual and textual contents.
    """
    try:
        screen_file = capture_screen(max_dimension=1280)
        analysis = analyze_image(str(screen_file), prompt=prompt)
        return f"[Screen Capture: {screen_file.name}]\n{analysis}"
    except Exception as e:
        return f"Failed to capture and analyze screen: {str(e)}"
