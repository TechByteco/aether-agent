"""
AETHER & LEON Model Registration Script
=======================================
Registers 'aether:leon' and 'leon:latest' into local Ollama runtime.
"""

from pathlib import Path
import subprocess
import sys

def register_leon():
    models_dir = Path("data/models").resolve()
    gguf_path = models_dir / "Llama-3.2-3B-Instruct.Q4_K_M.gguf"
    if not gguf_path.exists():
        gguf_path = models_dir / "aether_core_v3_gguf" / "Llama-3.2-3B-Instruct.Q4_K_M.gguf"

    if not gguf_path.exists():
        print(f"Error: GGUF file not found in {models_dir}")
        sys.exit(1)

    modelfile_content = f"""FROM {gguf_path.as_posix()}
PARAMETER temperature 0.3
PARAMETER top_p 0.9
PARAMETER stop "<|eot_id|>"
PARAMETER stop "<|start_header_id|>"
PARAMETER stop "<|end_header_id|>"

TEMPLATE \"\"\"<|start_header_id|>system<|end_header_id|>
{{{{ .System }}}}<|eot_id|>{{{{ if .Prompt }}}}<|start_header_id|>user<|end_header_id|>
{{{{ .Prompt }}}}<|eot_id|>{{{{ end }}}}<|start_header_id|>assistant<|end_header_id|>
\"\"\"

SYSTEM \"\"\"You are LEON, an Executive AI Companion and Senior Deep-Tech Engineering Partner for visionary builders and entrepreneurs. You excel at distributed architecture, unit economics modeling, cap table simulations, PRD creation, and zero-latency tool calling. Provide crisp, decisive, production-grade responses.\"\"\"
"""

    modelfile_path = models_dir / "Modelfile.leon"
    modelfile_path.write_text(modelfile_content, encoding="utf-8")
    print(f"[OK] Modelfile written to: {modelfile_path}")

    for name in ["aether:leon", "leon:latest"]:
        print(f"Registering '{name}' in Ollama...")
        cmd = ["ollama", "create", name, "-f", str(modelfile_path)]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            print(f"[OK] Successfully registered '{name}' in Ollama.")
        else:
            print(f"Error registering '{name}': {res.stderr}")

if __name__ == "__main__":
    register_leon()
