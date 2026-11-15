"""
AETHER Training Dataset Exporter & Formatter
Exports curated execution trajectories, heuristic rules, and interaction memory
into standard JSONL formats for Unsloth / LLaMA-Factory / QLoRA fine-tuning.
"""

import json
from pathlib import Path
from aether.config import config
from aether.memory.store import memory
from aether.brain.evolution import evolution_engine

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "training"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

dataset_file = OUTPUT_DIR / "aether_train_dataset.jsonl"


def export_dataset():
    samples = []

    # 1. Include evolution engine synthetic pairs
    synthetic_file = evolution_engine.dataset_file
    if synthetic_file.exists():
        for line in synthetic_file.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    samples.append(json.loads(line))
                except Exception:
                    pass

    # 2. Add system prompt & tool-calling instruction pairs
    base_system = (
        "You are AETHER, a sovereign AI Copilot and Autonomous Agent. "
        "You possess direct OS control, web research tools, cybersecurity scanners, and system vitals inspection. "
        "Deliver precise, production-grade answers and invoke native tools when required."
    )

    # Core instruction samples
    core_instructs = [
        {
            "messages": [
                {"role": "system", "content": base_system},
                {"role": "user", "content": "Scan the current project for exposed secrets or API keys."},
                {"role": "assistant", "content": '```json\n{"tool": "tool_hunt_exposed_secrets", "args": {"target_dir": "."}}\n```'}
            ]
        },
        {
            "messages": [
                {"role": "system", "content": base_system},
                {"role": "user", "content": "Check active network connections and listening ports on this machine."},
                {"role": "assistant", "content": '```json\n{"tool": "tool_audit_active_connections", "args": {"filter_state": "ALL"}}\n```'}
            ]
        },
        {
            "messages": [
                {"role": "system", "content": base_system},
                {"role": "user", "content": "Benchmark the API endpoint http://127.0.0.1:8000/ to check latency and throughput."},
                {"role": "assistant", "content": '```json\n{"tool": "tool_benchmark_api_endpoint", "args": {"url": "http://127.0.0.1:8000/", "num_requests": 10}}\n```'}
            ]
        },
        {
            "messages": [
                {"role": "system", "content": base_system},
                {"role": "user", "content": "Audit the codebase architecture in src/aether for god files and complexity debt."},
                {"role": "assistant", "content": '```json\n{"tool": "tool_audit_codebase_architecture", "args": {"target_dir": "src/aether"}}\n```'}
            ]
        }
    ]

    samples.extend(core_instructs)

    # Write out unified dataset
    with open(dataset_file, "w", encoding="utf-8") as f:
        for sample in samples:
            f.write(json.dumps(sample, ensure_ascii=False) + "\n")

    print(f"✓ Exported {len(samples)} training samples to: {dataset_file}")
    return dataset_file


if __name__ == "__main__":
    export_dataset()
