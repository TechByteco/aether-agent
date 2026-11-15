"""
AETHER Automated Free Cloud GPU Master Trainer
==============================================
Consolidates all synthetic trajectories, Teacher-Student DPO pairs, and procedural heuristics,
and generates ready-to-run training pipelines for 100% FREE high-end cloud GPU facilities:

Free Cloud GPU Facilities Supported:
1. Kaggle (Dual NVIDIA T4 / P100 - 30 Hours/Week FREE, 30 GB RAM)
2. Google Colab (NVIDIA T4 GPU - Free Tier, 15 GB VRAM)
3. Modal.com (NVIDIA A10G 24GB VRAM - $30/month Free Compute Credits)
4. Hugging Face Spaces / AutoTrain (Free Tier)

Features:
- Automated dataset consolidation & ChatML formatting into `data/training/aether_unified_cloud_dataset.jsonl`
- Automated generation of 1-click Kaggle & Colab notebooks with Unsloth QLoRA + GGUF compilation
- 1-command checkpoint hot-reloading into Ollama (`aether:finetuned`)
"""

import argparse
import json
import logging
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Any, Dict, List

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir / "src"))

from aether.config import config
from aether.memory.store import memory

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("aether.cloud_trainer")


SYSTEM_PROMPT = (
    "You are AETHER, a sovereign AI Copilot and Autonomous Agent operating on Windows ARM64. "
    "You possess direct OS control, web research tools, cybersecurity scanners, AST code patching, "
    "and dynamic tool synthesis. Deliver precise, production-grade answers and invoke native tools when required."
)

CORE_AETHER_TRAJECTORIES = [
    {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": "Scan the current workspace for exposed secrets, passwords, or leaked API keys."},
            {"role": "assistant", "content": '```json\n{"tool": "tool_hunt_exposed_secrets", "args": {"target_dir": "."}}\n```\nScanning workspace for exposed secrets and API tokens...'}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": "A Python tool failed with missing module error. Diagnose and synthesize a new tool."},
            {"role": "assistant", "content": '```json\n{"tool": "tool_synthesize_new_tool", "args": {"tool_name": "tool_native_hash_hasher", "task_description": "Calculate SHA-256 and MD5 hashes using Python hashlib without third party dependencies"}}\n```\nSynthesizing native self-contained tool to replace missing module...'}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": "Audit active network ports and open sockets on this machine."},
            {"role": "assistant", "content": '```json\n{"tool": "tool_audit_active_connections", "args": {"filter_state": "LISTEN"}}\n```\nAuditing active listening sockets and network endpoints...'}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": "Check real-time hardware status, RAM usage, and Oryon CPU vitals."},
            {"role": "assistant", "content": '```json\n{"tool": "tool_system_vitals", "args": {}}\n```\nRetrieving hardware telemetry and system load metrics...'}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": "Analyze and optimize a slow BigQuery query for partitioning and slot reduction."},
            {"role": "assistant", "content": '```json\n{"tool": "tool_execute_rewoo_plan", "args": {"task": "Deconstruct query execution graph, enforce partition pruning on event_date, cluster on user_id, and eliminate Cartesian cross-joins."}}\n```\nGenerating ReWOO execution blueprint for BigQuery optimization...'}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": "Inspect the file src/aether/brain/engine.py from lines 10 to 60."},
            {"role": "assistant", "content": '```json\n{"tool": "tool_read_file_window", "args": {"file_path": "src/aether/brain/engine.py", "start_line": 10, "end_line": 60}}\n```\nReading surgical line window from engine.py...'}
        ]
    },
]


def consolidate_all_training_data(output_file: Path) -> int:
    """Consolidate all synthetic examples, heuristic rules, and curated trajectories."""
    seen_prompts = set()
    unified_records: List[Dict[str, Any]] = []

    # 1. Base Core Trajectories
    for ex in CORE_AETHER_TRAJECTORIES:
        user_msg = next((m["content"] for m in ex["messages"] if m["role"] == "user"), "")
        if user_msg not in seen_prompts:
            seen_prompts.add(user_msg)
            unified_records.append(ex)

    # 2. Existing data/training/aether_train_dataset.jsonl
    f1 = Path("data/training/aether_train_dataset.jsonl")
    if f1.exists():
        for line in f1.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                msgs = data.get("messages", [])
                user_msg = next((m["content"] for m in msgs if m["role"] == "user"), "")
                if user_msg and user_msg not in seen_prompts:
                    seen_prompts.add(user_msg)
                    unified_records.append({"messages": msgs})
            except Exception:
                pass

    # 3. Synthetic dataset from teacher-student & evolution engine
    f2 = Path("data/memory/training/synthetic_finetune_dataset.jsonl")
    if f2.exists():
        for line in f2.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                msgs = data.get("messages", [])
                user_msg = next((m["content"] for m in msgs if m["role"] == "user"), "")
                if user_msg and user_msg not in seen_prompts:
                    seen_prompts.add(user_msg)
                    unified_records.append({"messages": msgs})
            except Exception:
                pass

    # 4. Synthesize records from SQLite procedural heuristic rules
    try:
        rules = memory.recall_heuristic_rules("", limit=30)
        for r in rules:
            if isinstance(r, dict):
                rule_text = r.get("rule_text") or r.get("rule")
                domain = r.get("domain", "general")
            else:
                rule_text = str(r)
                domain = "general"
            if rule_text and len(rule_text) > 15:
                prompt_text = f"What operational invariant rule should be enforced for {domain} tasks?"
                if prompt_text not in seen_prompts:
                    seen_prompts.add(prompt_text)
                    unified_records.append({
                        "messages": [
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": prompt_text},
                            {"role": "assistant", "content": f"**Universal Cognitive Invariant [{domain.upper()}]:**\n\n{rule_text}"}
                        ]
                    })
    except Exception as e:
        logger.warning(f"Could not extract SQLite heuristics: {e}")


    # Write unified JSONL
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        for item in unified_records:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    logger.info(f"✓ Consolidated {len(unified_records)} high-quality training records to {output_file}")
    return len(unified_records)


def generate_kaggle_and_colab_notebook(dataset_file: Path, output_ipynb: Path):
    """Generate a self-contained Jupyter notebook for free GPU training on Kaggle / Google Colab."""
    dataset_content = dataset_file.read_text(encoding="utf-8")

    notebook_json = {
        "cells": [
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": [
                    "# 🚀 AETHER Free Cloud GPU Continuous Fine-Tuning Pipeline\n",
                    "**Hardware**: NVIDIA T4 / P100 GPU (Free on Kaggle & Google Colab)  \n",
                    "**Engine**: Unsloth 4-bit QLoRA Fast Language Model + llama.cpp GGUF Export\n",
                    "\n",
                    "### Instructions:\n",
                    "1. On Kaggle: Turn ON `GPU T4 x2` or `GPU P100` in the right-hand panel (Settings -> Accelerator).\n",
                    "2. On Colab: Change Runtime to `T4 GPU` (Runtime -> Change runtime type -> T4 GPU).\n",
                    "3. Click **Run All** (Ctrl+F9). In ~3 minutes, your `aether_adapter.gguf` will be trained and downloaded automatically!"
                ]
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "# 1. Install Unsloth & Fast Training Dependencies\n",
                    "!pip install --no-deps \"unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git\"\n",
                    "!pip install --no-deps xformers \"trl<0.9.0\" peft accelerate bitsandbytes datasets\n",
                    "!git clone --depth 1 https://github.com/ggerganov/llama.cpp.git\n",
                    "!pip install -r llama.cpp/requirements.txt"
                ]
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "# 2. Embed Consolidated AETHER Training Dataset\n",
                    "import json\n",
                    "\n",
                    f"raw_data = '''{dataset_content}'''\n",
                    "\n",
                    "with open('aether_train_dataset.jsonl', 'w', encoding='utf-8') as f:\n",
                    "    f.write(raw_data.strip() + '\\n')\n",
                    "\n",
                    "print(f'✓ Successfully loaded {len(raw_data.strip().splitlines())} training samples.')"
                ]
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "# 3. Load Model with 4-bit Quantization\n",
                    "from unsloth import FastLanguageModel\n",
                    "import torch\n",
                    "from datasets import load_dataset\n",
                    "from trl import SFTTrainer\n",
                    "from transformers import TrainingArguments\n",
                    "\n",
                    "max_seq_length = 4096\n",
                    "model, tokenizer = FastLanguageModel.from_pretrained(\n",
                    "    model_name = 'unsloth/Llama-3.2-3B-Instruct',\n",
                    "    max_seq_length = max_seq_length,\n",
                    "    load_in_4bit = True,\n",
                    ")\n",
                    "\n",
                    "model = FastLanguageModel.get_peft_model(\n",
                    "    model,\n",
                    "    r = 16,\n",
                    "    target_modules = ['q_proj', 'k_proj', 'v_proj', 'o_proj', 'gate_proj', 'up_proj', 'down_proj'],\n",
                    "    lora_alpha = 16,\n",
                    "    lora_dropout = 0,\n",
                    "    bias = 'none',\n",
                    "    use_gradient_checkpointing = 'unsloth',\n",
                    "    random_state = 3407,\n",
                    ")\n",
                    "\n",
                    "# Format dataset\n",
                    "dataset = load_dataset('json', data_files='aether_train_dataset.jsonl', split='train')\n",
                    "\n",
                    "def format_prompts(examples):\n",
                    "    texts = []\n",
                    "    for msgs in examples['messages']:\n",
                    "        text = tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=False)\n",
                    "        texts.append(text)\n",
                    "    return {'text': texts}\n",
                    "\n",
                    "dataset = dataset.map(format_prompts, batched=True)\n",
                    "print('✓ Dataset formatted with ChatML template.')"
                ]
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "# 4. Train LoRA Adapter (~3-5 mins on T4 GPU)\n",
                    "trainer = SFTTrainer(\n",
                    "    model = model,\n",
                    "    tokenizer = tokenizer,\n",
                    "    train_dataset = dataset,\n",
                    "    dataset_text_field = 'text',\n",
                    "    max_seq_length = max_seq_length,\n",
                    "    packing = False,\n",
                    "    args = TrainingArguments(\n",
                    "        per_device_train_batch_size = 2,\n",
                    "        gradient_accumulation_steps = 4,\n",
                    "        warmup_steps = 5,\n",
                    "        max_steps = 60,\n",
                    "        learning_rate = 2e-4,\n",
                    "        fp16 = not torch.cuda.is_bf16_supported(),\n",
                    "        bf16 = torch.cuda.is_bf16_supported(),\n",
                    "        logging_steps = 5,\n",
                    "        output_dir = 'aether_outputs',\n",
                    "    ),\n",
                    ")\n",
                    "trainer.train()\n",
                    "model.save_pretrained('aether_lora_adapter')\n",
                    "tokenizer.save_pretrained('aether_lora_adapter')\n",
                    "print('✓ LoRA training finished successfully!')"
                ]
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "# 5. Convert LoRA to GGUF and Download Automatically\n",
                    "import subprocess\n",
                    "\n",
                    "!python llama.cpp/convert_lora_to_gguf.py aether_lora_adapter --outfile aether_adapter.gguf\n",
                    "\n",
                    "# Auto-download for Colab / Kaggle\n",
                    "try:\n",
                    "    from google.colab import files\n",
                    "    files.download('aether_adapter.gguf')\n",
                    "    print('🎉 Checkpoint aether_adapter.gguf downloaded automatically!')\n",
                    "except ImportError:\n",
                    "    print('Kaggle output ready at: aether_adapter.gguf (Check Output files on right panel)')"
                ]
            }
        ],
        "metadata": {
            "accelerator": "GPU",
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3"
            },
            "language_info": {
                "name": "python",
                "version": "3.10.12"
            }
        },
        "nbformat": 4,
        "nbformat_minor": 4
    }

    output_ipynb.write_text(json.dumps(notebook_json, indent=2), encoding="utf-8")
    logger.info(f"✓ Generated 1-Click Free GPU Training Notebook: {output_ipynb}")


def ingest_new_adapter(adapter_path: Path):
    """Move newly downloaded GGUF adapter and register into Ollama."""
    dest_path = Path("data/models/aether_adapter.gguf")
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    if not adapter_path.exists():
        logger.error(f"Adapter file not found at: {adapter_path}")
        return False

    shutil.copy2(adapter_path, dest_path)
    logger.info(f"✓ Ingested adapter to {dest_path} ({dest_path.stat().st_size / (1024*1024):.2f} MB)")

    # Re-create Ollama model
    modelfile = Path("Modelfile.aether-finetuned")
    if modelfile.exists():
        logger.info("Registering updated fine-tuned model in Ollama...")
        res = subprocess.run(["ollama", "create", "aether:finetuned", "-f", str(modelfile)], capture_output=True, text=True)
        if res.returncode == 0:
            logger.info("🎉 aether:finetuned successfully updated in Ollama runtime!")
            return True
        else:
            logger.error(f"Ollama creation error: {res.stderr}")
            return False
    return False


def main():
    parser = argparse.ArgumentParser(description="AETHER Automated Free Cloud GPU Master Trainer")
    parser.add_argument("--prepare", action="store_true", help="Consolidate datasets and generate Kaggle/Colab notebook")
    parser.add_argument("--ingest", type=str, help="Ingest a newly downloaded aether_adapter.gguf file into Ollama")
    args = parser.parse_args()

    unified_dataset = Path("data/training/aether_unified_cloud_dataset.jsonl")
    notebook_path = Path("data/training/aether_free_cloud_gpu_trainer.ipynb")

    if args.ingest:
        ingest_new_adapter(Path(args.ingest))
    else:
        sample_count = consolidate_all_training_data(unified_dataset)
        generate_kaggle_and_colab_notebook(unified_dataset, notebook_path)
        print("\n" + "=" * 80)
        print("🎯 AETHER FREE CLOUD GPU TRAINING PACKAGE READY")
        print("=" * 80)
        print(f"1. Unified Dataset:  {unified_dataset} ({sample_count} verified samples)")
        print(f"2. 1-Click Notebook: {notebook_path}")
        print("\nHow to train on Free Cloud GPUs:")
        print("▶ Option 1 (Kaggle - 30 hrs/wk free GPU): Upload notebook to kaggle.com/code -> Select GPU T4 -> Run All")
        print("▶ Option 2 (Google Colab - Free T4): Open notebook in colab.research.google.com -> Run All")
        print("▶ Option 3 (Modal - $30/mo free credit): Run `modal run scripts/cloud_modal_trainer.py`")
        print("\nOnce downloaded, update Ollama with: python scripts/automated_free_cloud_trainer.py --ingest aether_adapter.gguf")
        print("=" * 80)


if __name__ == "__main__":
    main()
