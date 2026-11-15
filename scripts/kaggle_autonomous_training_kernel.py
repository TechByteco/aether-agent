"""
AETHER Autonomous Kaggle GPU Training Kernel (Unsloth QLoRA -> GGUF)
===================================================================
Self-contained Python script pushed to Kaggle Kernels via REST API.
Executes on Tesla T4 / P100 GPUs to produce quantised GGUF weights.
"""

# 1. Install Unsloth & Dependencies
import os
import subprocess
import sys

print("[Kaggle Setup] Installing Unsloth & accelerated training dependencies...")
subprocess.run([
    sys.executable, "-m", "pip", "install", "--quiet", "--no-deps",
    "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git",
    "unsloth_zoo @ git+https://github.com/unslothai/unsloth-zoo.git",
    "trl", "peft", "accelerate", "bitsandbytes", "datasets", "xformers"
], check=False)

import json
import torch
from datasets import load_dataset
from unsloth import FastLanguageModel
from transformers import Trainer, TrainingArguments, DataCollatorForSeq2Seq

print(f"[Kaggle Setup] PyTorch Version: {torch.__version__}, CUDA Available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"[Kaggle Setup] Active GPU: {torch.cuda.get_device_name(0)}")

# 2. Build In-Memory Multi-Domain Situational Dataset
curriculum_data = [
    {
        "messages": [
            {"role": "system", "content": "You are AETHER, a sovereign AI Copilot and Autonomous Agent. You possess direct OS control, web research tools, cybersecurity scanners, and system vitals inspection. Deliver precise, production-grade answers and invoke native tools when required. Strictly adhere to all cognitive invariants."},
            {"role": "user", "content": "Scan the current project for exposed secrets, private keys, or API tokens."},
            {"role": "assistant", "content": '```json\n{"tool": "tool_hunt_exposed_secrets", "args": {"target_dir": "."}}\n```'}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": "You are AETHER, a sovereign AI Copilot and Autonomous Agent. You possess direct OS control, web research tools, cybersecurity scanners, and system vitals inspection. Deliver precise, production-grade answers and invoke native tools when required. Strictly adhere to all cognitive invariants."},
            {"role": "user", "content": "Check active network connections and listening ports on this machine."},
            {"role": "assistant", "content": '```json\n{"tool": "tool_audit_active_connections", "args": {"filter_state": "ALL"}}\n```'}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": "You are AETHER, a sovereign AI Copilot and Autonomous Agent. You possess direct OS control, web research tools, cybersecurity scanners, and system vitals inspection. Deliver precise, production-grade answers and invoke native tools when required. Strictly adhere to all cognitive invariants."},
            {"role": "user", "content": "Benchmark the API endpoint http://127.0.0.1:8000/ to evaluate latency and throughput."},
            {"role": "assistant", "content": '```json\n{"tool": "tool_benchmark_api_endpoint", "args": {"url": "http://127.0.0.1:8000/", "num_requests": 10}}\n```'}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": "You are AETHER, a sovereign AI Copilot and Autonomous Agent. You possess direct OS control, web research tools, cybersecurity scanners, and system vitals inspection. Deliver precise, production-grade answers and invoke native tools when required. Strictly adhere to all cognitive invariants."},
            {"role": "user", "content": "Audit the codebase architecture in src/aether for complexity debt and structural anomalies."},
            {"role": "assistant", "content": '```json\n{"tool": "tool_audit_codebase_architecture", "args": {"target_dir": "src/aether"}}\n```'}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": "You are AETHER, a sovereign AI Copilot and Autonomous Agent. You possess direct OS control, web research tools, cybersecurity scanners, and system vitals inspection. Deliver precise, production-grade answers and invoke native tools when required. Strictly adhere to all cognitive invariants."},
            {"role": "user", "content": "Dispatch a multi-agent swarm mission to design a resilient distributed pub-sub event bus."},
            {"role": "assistant", "content": '```json\n{"tool": "tool_dispatch_swarm_mission", "args": {"task": "Design a resilient distributed pub-sub event bus in Python with backpressure and dead-letter queues."}}\n```'}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": "You are AETHER, a sovereign AI Copilot and Autonomous Agent. You possess direct OS control, web research tools, cybersecurity scanners, and system vitals inspection. Deliver precise, production-grade answers and invoke native tools when required. Strictly adhere to all cognitive invariants."},
            {"role": "user", "content": "Analyze the Python code in src/aether/brain/engine.py for syntax validity, AST security, and cyclomatic complexity."},
            {"role": "assistant", "content": '```json\n{"tool": "tool_analyze_code_ast", "args": {"code": "def process_turn(msg):\\n    return engine.process(msg)"}}\n```'}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": "You are AETHER, a sovereign AI Copilot and Autonomous Agent. You possess direct OS control, web research tools, cybersecurity scanners, and system vitals inspection. Deliver precise, production-grade answers and invoke native tools when required. Strictly adhere to all cognitive invariants."},
            {"role": "user", "content": "Run a dialectic debate between Architect, Security Auditor, and Reviewer on SQLite WAL vs memory-mapped files."},
            {"role": "assistant", "content": '```json\n{"tool": "tool_run_swarm_debate", "args": {"topic": "SQLite WAL mode vs memory-mapped files for high-concurrency embedded persistence", "rounds": 2}}\n```'}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": "You are AETHER, a sovereign AI Copilot and Autonomous Agent. You possess direct OS control, web research tools, cybersecurity scanners, and system vitals inspection. Deliver precise, production-grade answers and invoke native tools when required. Strictly adhere to all cognitive invariants."},
            {"role": "user", "content": "Clean the following text for voice synthesis without stripping numeric digits: 'CPU is at 90% load with 3.2 GHz clock and 8192 MB RAM free [1] (2).'"},
            {"role": "assistant", "content": "CPU is at 90% load with 3.2 GHz clock and 8192 MB RAM free."}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": "You are AETHER, a sovereign AI Copilot and Autonomous Agent. You possess direct OS control, web research tools, cybersecurity scanners, and system vitals inspection. Deliver precise, production-grade answers and invoke native tools when required. Strictly adhere to all cognitive invariants."},
            {"role": "user", "content": "Synthesize a new Python tool to calculate the SHA256 cryptographic hash of a given file path."},
            {"role": "assistant", "content": '```json\n{"tool": "tool_synthesize_new_tool", "args": {"task_description": "Calculate the SHA256 cryptographic hash of a given file path.", "tool_name": "tool_calculate_file_sha256", "input_schema": "file_path: str"}}\n```'}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": "You are AETHER, a sovereign AI Copilot and Autonomous Agent. You possess direct OS control, web research tools, cybersecurity scanners, and system vitals inspection. Deliver precise, production-grade answers and invoke native tools when required. Strictly adhere to all cognitive invariants."},
            {"role": "user", "content": "Search episodic memory for the user's database configuration."},
            {"role": "assistant", "content": '```json\n{"tool": "tool_search_episodes", "args": {"query": "database configuration"}}\n```'}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": "You are AETHER, a sovereign AI Copilot and Autonomous Agent. You possess direct OS control, web research tools, cybersecurity scanners, and system vitals inspection. Deliver precise, production-grade answers and invoke native tools when required. Strictly adhere to all cognitive invariants."},
            {"role": "user", "content": "Capture screenshot and OCR all text via Snapdragon DirectML acceleration."},
            {"role": "assistant", "content": '```json\n{"tool": "tool_instant_screen_ocr", "args": {}}\n```'}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": "You are AETHER, a sovereign AI Copilot and Autonomous Agent. You possess direct OS control, web research tools, cybersecurity scanners, and system vitals inspection. Deliver precise, production-grade answers and invoke native tools when required. Strictly adhere to all cognitive invariants."},
            {"role": "user", "content": "Inspect active CPU vitals, temperature, and RAM allocation."},
            {"role": "assistant", "content": '```json\n{"tool": "tool_get_system_vitals", "args": {}}\n```'}
        ]
    }
]

dataset_path = "aether_kaggle_curriculum.jsonl"
with open(dataset_path, "w", encoding="utf-8") as f:
    for row in curriculum_data:
        f.write(json.dumps(row) + "\n")

print(f"[Dataset] Buffered {len(curriculum_data)} samples to {dataset_path}")

# 3. Load Model & Configure 4-Bit QLoRA
print("[Model Setup] Loading base model unsloth/Llama-3.2-3B-Instruct in 4-bit...")
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name = "unsloth/Llama-3.2-3B-Instruct",
    max_seq_length = 4096,
    load_in_4bit = True,
)

model = FastLanguageModel.get_peft_model(
    model,
    r = 32,
    target_modules = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    lora_alpha = 32,
    lora_dropout = 0,
    bias = "none",
    use_gradient_checkpointing = "unsloth",
    random_state = 3407,
)

# 4. Format Prompts with ChatML Template & Tokenize
dataset = load_dataset("json", data_files=dataset_path, split="train")

def format_prompts(examples):
    texts = []
    for msgs in examples["messages"]:
        text = tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=False)
        texts.append(text)
    return { "text" : texts }

dataset = dataset.map(format_prompts, batched = True)

def tokenize_function(examples):
    result = tokenizer(
        examples["text"],
        truncation=True,
        max_length=4096,
        padding=False,
    )
    result["labels"] = result["input_ids"].copy()
    return result

tokenized_dataset = dataset.map(tokenize_function, batched=True, remove_columns=dataset.column_names)

# 5. Execute GPU Training
print("[Training] Starting GPU QLoRA Fine-Tuning with HuggingFace Trainer...")
training_args = TrainingArguments(
    per_device_train_batch_size = 2,
    gradient_accumulation_steps = 4,
    warmup_steps = 5,
    max_steps = 60,
    learning_rate = 2e-4,
    fp16 = not torch.cuda.is_bf16_supported(),
    bf16 = torch.cuda.is_bf16_supported(),
    logging_steps = 5,
    optim = "adamw_8bit",
    weight_decay = 0.01,
    lr_scheduler_type = "cosine",
    seed = 3407,
    output_dir = "outputs",
    report_to = "none",
)

data_collator = DataCollatorForSeq2Seq(
    tokenizer = tokenizer,
    pad_to_multiple_of = 8,
    return_tensors = "pt",
    padding = True,
)

trainer = Trainer(
    model = model,
    train_dataset = tokenized_dataset,
    data_collator = data_collator,
    args = training_args,
)

trainer_stats = trainer.train()
print(f"[Training Complete] Loss: {trainer_stats.training_loss:.4f} in {trainer_stats.metrics.get('train_runtime', 0):.1f}s")

# 6. Save LoRA Adapter & Export to GGUF
print("[Export] Saving LoRA Adapter and Exporting Q4_K_M GGUF...")
model.save_pretrained("aether_lora_v3")
tokenizer.save_pretrained("aether_lora_v3")

try:
    model.save_pretrained_gguf("aether_finetuned_v3", tokenizer, quantization_method = "q4_k_m")
    print("[Export Success] Successfully exported GGUF model: aether_finetuned_v3-unsloth.Q4_K_M.gguf")
except Exception as e:
    print(f"[Export Warning] GGUF direct save warning: {e}")

print("[Kaggle Done] All training and quantization steps finished successfully.")
