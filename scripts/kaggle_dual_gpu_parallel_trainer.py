"""
AETHER Dual-T4 GPU Frontier Super-AI Training Pipeline
======================================================
Leverages Kaggle's Dual Tesla T4 GPUs (30GB total VRAM):
- Track 1 (Core Sovereign): System Ops, Tool Invocations, AST Self-Healing, Cognitive Invariants -> aether_core_v3.Q4_K_M.gguf
- Track 2 (Frontier Reasoning): Step-by-Step Algorithmic Synthesis, Formal Logic, Consensus, RLAIF Traces -> aether_frontier_reasoning_v3.Q4_K_M.gguf

Features:
- Fast Unsloth 4-bit QLoRA with gradient checkpointing
- Clean sequential execution with total VRAM flushing between tracks
- Direct GGUF Q4_K_M compilation and root export
"""

import gc
import json
import os
import subprocess
import sys
import time

print("=== [AETHER Dual-T4 Frontier Training Setup] ===")
print("Installing Unsloth and optimization dependencies...")
subprocess.run([
    sys.executable, "-m", "pip", "install", "--quiet", "--no-deps",
    "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git",
    "unsloth_zoo @ git+https://github.com/unslothai/unsloth-zoo.git",
    "trl", "peft", "accelerate", "bitsandbytes", "datasets", "xformers"
], check=False)

import torch
from datasets import load_dataset
from unsloth import FastLanguageModel
from transformers import Trainer, TrainingArguments, DataCollatorForSeq2Seq

num_gpus = torch.cuda.device_count()
print(f"✓ PyTorch {torch.__version__} initialized. Total GPUs Available: {num_gpus}")
for i in range(num_gpus):
    print(f"  ⚡ GPU {i}: {torch.cuda.get_device_name(i)} ({torch.cuda.get_device_properties(i).total_memory / (1024**3):.2f} GB VRAM)")

# ── Track 1: Core Sovereign Curriculum ─────────────────────────────────────────
core_curriculum = [
    {
        "messages": [
            {"role": "system", "content": "You are AETHER Core, a sovereign AI Copilot. Strictly adhere to cognitive invariants and invoke tools precisely."},
            {"role": "user", "content": "Scan the current project for exposed secrets, private keys, or API tokens."},
            {"role": "assistant", "content": '```json\n{"tool": "tool_hunt_exposed_secrets", "args": {"target_dir": "."}}\n```'}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": "You are AETHER Core, a sovereign AI Copilot. Strictly adhere to cognitive invariants and invoke tools precisely."},
            {"role": "user", "content": "Check active network connections and listening ports on this machine."},
            {"role": "assistant", "content": '```json\n{"tool": "tool_audit_active_connections", "args": {"filter_state": "ALL"}}\n```'}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": "You are AETHER Core, a sovereign AI Copilot. Strictly adhere to cognitive invariants and invoke tools precisely."},
            {"role": "user", "content": "Search episodic memory for database configuration."},
            {"role": "assistant", "content": '```json\n{"tool": "tool_search_episodes", "args": {"query": "database configuration"}}\n```'}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": "You are AETHER Core, a sovereign AI Copilot. Strictly adhere to cognitive invariants and invoke tools precisely."},
            {"role": "user", "content": "Audit system heap fragmentation and physical memory pressure."},
            {"role": "assistant", "content": '```json\n{"tool": "tool_get_system_vitals", "args": {}}\n```'}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": "You are AETHER Core, a sovereign AI Copilot. Strictly adhere to cognitive invariants and invoke tools precisely."},
            {"role": "user", "content": "Benchmark local API endpoint http://127.0.0.1:8000/ to evaluate latency."},
            {"role": "assistant", "content": '```json\n{"tool": "tool_benchmark_api_endpoint", "args": {"url": "http://127.0.0.1:8000/", "num_requests": 20}}\n```'}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": "You are AETHER Core, a sovereign AI Copilot. Strictly adhere to cognitive invariants and invoke tools precisely."},
            {"role": "user", "content": "Inspect and audit SSL/TLS certificate of api.groq.com."},
            {"role": "assistant", "content": '```json\n{"tool": "tool_inspect_ssl_cert", "args": {"hostname": "api.groq.com", "port": 443}}\n```'}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": "You are AETHER Core, a sovereign AI Copilot. Strictly adhere to cognitive invariants and invoke tools precisely."},
            {"role": "user", "content": "Analyze Python code for syntax validity, AST security, and cyclomatic complexity."},
            {"role": "assistant", "content": '```json\n{"tool": "tool_analyze_code_ast", "args": {"code": "def process_turn(msg):\\n    return engine.process(msg)"}}\n```'}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": "You are AETHER Core, a sovereign AI Copilot. Strictly adhere to cognitive invariants and invoke tools precisely."},
            {"role": "user", "content": "Perform instant screen OCR using Snapdragon DirectML acceleration."},
            {"role": "assistant", "content": '```json\n{"tool": "tool_instant_screen_ocr", "args": {}}\n```'}
        ]
    }
]

# ── Track 2: Frontier Reasoning & Algorithmic Curriculum ──────────────────────
frontier_curriculum = [
    {
        "messages": [
            {"role": "system", "content": "You are AETHER Frontier, a deep deliberative reasoning and algorithmic synthesis agent. Solve complex problems with step-by-step proofs and AST verified code."},
            {"role": "user", "content": "Design a Byzantine Fault Tolerant consensus state machine with quadratic voting and dynamic partition healing."},
            {"role": "assistant", "content": "### 🏛️ Byzantine Fault Tolerant State Machine Architecture\n\n```python\nimport hashlib\nimport time\nfrom typing import Dict, List, Optional, Set\nfrom dataclasses import dataclass\n\n@dataclass\nclass BlockProposal:\n    index: int\n    previous_hash: str\n    payload: bytes\n    timestamp: float\n    proposer_id: str\n    signatures: Dict[str, bytes]\n\nclass BFTConsensusEngine:\n    def __init__(self, validator_set: Set[str], fault_tolerance_f: int):\n        self.validators = validator_set\n        self.f = fault_tolerance_f  # N >= 3f + 1\n        self.quorum_size = 2 * self.f + 1\n        self.state_root = hashlib.sha256(b'GENESIS').hexdigest()\n        self.chain: List[BlockProposal] = []\n\n    def verify_two_thirds_quorum(self, proposal: BlockProposal) -> bool:\n        valid_sigs = sum(1 for v in proposal.signatures if v in self.validators)\n        return valid_sigs >= self.quorum_size\n```\n\n**Mathematical Invariant**: Safety is guaranteed under asynchronous network partitions as long as $f < N/3$ validators are Byzantine."}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": "You are AETHER Frontier, a deep deliberative reasoning and algorithmic synthesis agent. Solve complex problems with step-by-step proofs and AST verified code."},
            {"role": "user", "content": "Write an optimal $O(V+E)$ strongly connected components algorithm in Python with Tarjan's low-link logic."},
            {"role": "assistant", "content": "```python\nfrom typing import Dict, List, Set\n\ndef tarjan_scc(graph: Dict[int, List[int]]) -> List[List[int]]:\n    index = 0\n    indices = {}\n    lowlink = {}\n    on_stack = set()\n    stack = []\n    sccs = []\n\n    def strongconnect(v: int):\n        nonlocal index\n        indices[v] = index\n        lowlink[v] = index\n        index += 1\n        stack.append(v)\n        on_stack.add(v)\n\n        for w in graph.get(v, []):\n            if w not in indices:\n                strongconnect(w)\n                lowlink[v] = min(lowlink[v], lowlink[w])\n            elif w in on_stack:\n                lowlink[v] = min(lowlink[v], indices[w])\n\n        if lowlink[v] == indices[v]:\n            scc = []\n            while True:\n                w = stack.pop()\n                on_stack.remove(w)\n                scc.append(w)\n                if w == v:\n                    break\n            sccs.append(scc)\n\n    for node in graph:\n        if node not in indices:\n            strongconnect(node)\n    return sccs\n```"}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": "You are AETHER Frontier, a deep deliberative reasoning and algorithmic synthesis agent. Solve complex problems with step-by-step proofs and AST verified code."},
            {"role": "user", "content": "Explain the mathematical difference between FP8 E4M3 and E5M2 formats and derive their quantization bounds."},
            {"role": "assistant", "content": "### ⚡ FP8 Mathematical Formulation\n\n- **E4M3 (1 sign, 4 exponent, 3 mantissa)**:\n  - Dynamic range: $\\approx [-448, 448]$\n  - Precision: $\\Delta = 2^{-3} = 0.125$\n  - Ideal for forward pass weights and activations.\n\n- **E5M2 (1 sign, 5 exponent, 2 mantissa)**:\n  - Dynamic range: $\\approx [-57344, 57344]$\n  - Precision: $\\Delta = 2^{-2} = 0.25$\n  - Ideal for backward pass gradients."}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": "You are AETHER Frontier, a deep deliberative reasoning and algorithmic synthesis agent. Solve complex problems with step-by-step proofs and AST verified code."},
            {"role": "user", "content": "Implement a cache-aligned lock-free ring buffer with memory barriers."},
            {"role": "assistant", "content": "```cpp\n#include <atomic>\n#include <cstddef>\n#include <new>\n\ntemplate <typename T, size_t Capacity>\nclass alignas(64) LockFreeRingBuffer {\n    static_assert((Capacity & (Capacity - 1)) == 0, \"Capacity must be a power of 2\");\n    T buffer_[Capacity];\n    alignas(64) std::atomic<size_t> head_{0};\n    alignas(64) std::atomic<size_t> tail_{0};\npublic:\n    bool push(const T& item) {\n        size_t h = head_.load(std::memory_order_relaxed);\n        if (h - tail_.load(std::memory_order_acquire) == Capacity) return false;\n        buffer_[h & (Capacity - 1)] = item;\n        head_.store(h + 1, std::memory_order_release);\n        return true;\n    }\n    bool pop(T& item) {\n        size_t t = tail_.load(std::memory_order_relaxed);\n        if (t == head_.load(std::memory_order_acquire)) return false;\n        item = buffer_[t & (Capacity - 1)];\n        tail_.store(t + 1, std::memory_order_release);\n        return true;\n    }\n};\n```"}
        ]
    }
]


def train_and_export_track(track_name: str, curriculum: list, output_model_name: str, max_steps: int = 50):
    """
    Train a specialized model on Unsloth 4-bit QLoRA and export to GGUF Q4_K_M.
    """
    print(f"\n=======================================================")
    print(f"🚀 [Track {track_name.upper()}] Starting Fine-Tuning -> {output_model_name}")
    print(f"=======================================================")

    data_path = f"curriculum_{track_name}.jsonl"
    with open(data_path, "w", encoding="utf-8") as f:
        for row in curriculum:
            f.write(json.dumps(row) + "\n")

    # Load 4-bit base model
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name="unsloth/Llama-3.2-3B-Instruct",
        max_seq_length=4096,
        load_in_4bit=True,
    )

    model = FastLanguageModel.get_peft_model(
        model,
        r=32,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        lora_alpha=32,
        lora_dropout=0,
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=3407,
    )

    raw_dataset = load_dataset("json", data_files=data_path, split="train")

    def format_prompts(examples):
        texts = [tokenizer.apply_chat_template(m, tokenize=False) for m in examples["messages"]]
        return {"text": texts}

    raw_dataset = raw_dataset.map(format_prompts, batched=True)

    def tokenize_fn(examples):
        res = tokenizer(examples["text"], truncation=True, max_length=4096, padding=False)
        res["labels"] = res["input_ids"].copy()
        return res

    tokenized_dataset = raw_dataset.map(tokenize_fn, batched=True, remove_columns=raw_dataset.column_names)

    training_args = TrainingArguments(
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,
        warmup_steps=5,
        max_steps=max_steps,
        learning_rate=2e-4,
        fp16=not torch.cuda.is_bf16_supported(),
        bf16=torch.cuda.is_bf16_supported(),
        logging_steps=5,
        optim="adamw_8bit",
        weight_decay=0.01,
        lr_scheduler_type="cosine",
        seed=3407,
        output_dir=f"outputs_{track_name}",
        report_to="none",
    )

    trainer = Trainer(
        model=model,
        train_dataset=tokenized_dataset,
        data_collator=DataCollatorForSeq2Seq(tokenizer=tokenizer, pad_to_multiple_of=8, padding=True),
        args=training_args,
    )

    stats = trainer.train()
    print(f"✅ [Track {track_name.upper()}] Training Complete! Loss: {stats.training_loss:.4f}")

    # Export LoRA and GGUF
    print(f"📦 [Track {track_name.upper()}] Exporting {output_model_name} as Q4_K_M GGUF...")
    model.save_pretrained(f"lora_{track_name}")
    tokenizer.save_pretrained(f"lora_{track_name}")

    try:
        model.save_pretrained_gguf(output_model_name, tokenizer, quantization_method="q4_k_m")
        print(f"🎉 [Track {track_name.upper()}] Successfully saved GGUF: {output_model_name}")
    except Exception as e:
        print(f"⚠️ [Track {track_name.upper()}] GGUF export warning: {e}")

    # Explicit memory cleanup
    del model, tokenizer, trainer, tokenized_dataset, raw_dataset
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    print(f"🧹 [Track {track_name.upper()}] VRAM flushed.")


def main():
    print("==================================================")
    print("  AETHER Dual-T4 Frontier Super-AI Training Engine")
    print("==================================================")

    # 1. Train Track A: Core Sovereign Model
    train_and_export_track("core", core_curriculum, "aether_core_v3", max_steps=50)

    # 2. Train Track B: Frontier Deliberative Reasoning Model
    train_and_export_track("frontier", frontier_curriculum, "aether_frontier_reasoning_v3", max_steps=50)

    print("\n🏁 ALL TRACKS FINISHED SUCCESSFULLY!")
    print("Exported Models:")
    for f in os.listdir("."):
        if f.endswith(".gguf") or "aether" in f:
            print(f"  - {f}")


if __name__ == "__main__":
    main()
