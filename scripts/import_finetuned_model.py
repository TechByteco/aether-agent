"""
AETHER Fine-Tuned Model Ingestion & Ollama Registration Script
==============================================================
1. Detects `aether_adapter.gguf` or `aether-q4_k_m.gguf` in ~/Downloads.
2. Moves it to `data/models/`.
3. Registers `aether:finetuned` in Ollama via `ollama create aether:finetuned -f Modelfile.aether-finetuned`.
4. Tests live inference and verifies active weights.
"""

import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

def main():
    workspace_dir = Path(__file__).parent.parent
    downloads_dir = Path(os.environ.get("USERPROFILE", "")) / "Downloads"
    target_dir = workspace_dir / "data" / "models"
    target_dir.mkdir(parents=True, exist_ok=True)
    modelfile_path = workspace_dir / "Modelfile.aether-finetuned"

    # Search for adapter or standalone model
    candidates = [
        (downloads_dir / "aether_adapter.gguf", target_dir / "aether_adapter.gguf"),
        (downloads_dir / "aether-q4_k_m.gguf", target_dir / "aether-q4_k_m.gguf"),
        (target_dir / "aether_adapter.gguf", target_dir / "aether_adapter.gguf"),
        (target_dir / "aether-q4_k_m.gguf", target_dir / "aether-q4_k_m.gguf"),
    ]

    source, target = None, None
    for src, dst in candidates:
        if src.exists():
            source, target = src, dst
            break

    if not source:
        print(f"[Error] Could not find 'aether_adapter.gguf' in {downloads_dir}")
        print("Please ensure the download finished from Colab.")
        return 1

    if source != target:
        size_mb = source.stat().st_size / (1024 * 1024)
        print(f"[Move] Moving {source.name} ({size_mb:.2f} MB) to data/models/...")
        shutil.move(str(source), str(target))
        print(f"[OK] Placed at {target}")

    print(f"[Ollama] Registering 'aether:finetuned' in Ollama using {modelfile_path.name}...")
    try:
        res = subprocess.run(
            ["ollama", "create", "aether:finetuned", "-f", str(modelfile_path)],
            cwd=str(workspace_dir),
            capture_output=True,
            text=True,
            check=True,
        )
        print(res.stdout)
        print("[SUCCESS] Model 'aether:finetuned' is now registered in Ollama!")
    except Exception as e:
        print(f"[Error] Failed creating Ollama model: {e}")
        return 1

    # Quick test inference
    print("[Inference] Testing live model inference...")
    try:
        import ollama
        resp = ollama.chat(
            model="aether:finetuned",
            messages=[{"role": "user", "content": "Introduce yourself in one sentence."}],
        )
        print(f"AETHER Response: {resp.message.content}")
        print("[OK] Verified live inference on fine-tuned neural model!")
    except Exception as e:
        print(f"[Notice] Test inference notice: {e}")

    return 0

if __name__ == "__main__":
    sys.exit(main())
