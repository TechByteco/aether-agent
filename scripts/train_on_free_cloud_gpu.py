# ==============================================================================
# 🚀 AETHER 1-CELL FREE CLOUD GPU TRAINER (Kaggle & Google Colab)
# Copy and paste this single script into a new Kaggle or Colab Code Cell!
# Set Accelerator: GPU T4 x2 or GPU P100 (Kaggle) / T4 GPU (Colab)
# ==============================================================================

# 1. Install Unsloth & Fast Dependencies (~45 secs)
import subprocess, sys

print("📦 Installing Unsloth & fast training engines...")
subprocess.run("pip install --no-deps 'unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git'", shell=True, check=True)
subprocess.run("pip install --no-deps xformers 'trl<0.9.0' peft accelerate bitsandbytes datasets", shell=True, check=True)
subprocess.run("git clone --depth 1 https://github.com/ggerganov/llama.cpp.git && pip install -r llama.cpp/requirements.txt", shell=True, check=True)

# 2. Write Unified AETHER Dataset
import json

DATASET = [
  {"messages": [{"role": "system", "content": "You are AETHER, a sovereign AI Copilot and Autonomous Agent operating on Windows ARM64. You possess direct OS control, web research tools, cybersecurity scanners, AST code patching, and dynamic tool synthesis. Deliver precise, production-grade answers and invoke native tools when required."}, {"role": "user", "content": "Scan the current workspace for exposed secrets, passwords, or leaked API keys."}, {"role": "assistant", "content": "```json\n{\"tool\": \"tool_hunt_exposed_secrets\", \"args\": {\"target_dir\": \".\"}}\n```\nScanning workspace for exposed secrets and API tokens..."}]},
  {"messages": [{"role": "system", "content": "You are AETHER, a sovereign AI Copilot and Autonomous Agent operating on Windows ARM64. You possess direct OS control, web research tools, cybersecurity scanners, AST code patching, and dynamic tool synthesis. Deliver precise, production-grade answers and invoke native tools when required."}, {"role": "user", "content": "A Python tool failed with missing module error. Diagnose and synthesize a new tool."}, {"role": "assistant", "content": "```json\n{\"tool\": \"tool_synthesize_new_tool\", \"args\": {\"tool_name\": \"tool_native_hash_hasher\", \"task_description\": \"Calculate SHA-256 and MD5 hashes using Python hashlib without third party dependencies\"}}\n```\nSynthesizing native self-contained tool to replace missing module..."}]},
  {"messages": [{"role": "system", "content": "You are AETHER, a sovereign AI Copilot and Autonomous Agent operating on Windows ARM64. You possess direct OS control, web research tools, cybersecurity scanners, AST code patching, and dynamic tool synthesis. Deliver precise, production-grade answers and invoke native tools when required."}, {"role": "user", "content": "Audit active network ports and open sockets on this machine."}, {"role": "assistant", "content": "```json\n{\"tool\": \"tool_audit_active_connections\", \"args\": {\"filter_state\": \"LISTEN\"}}\n```\nAuditing active listening sockets and network endpoints..."}]},
  {"messages": [{"role": "system", "content": "You are AETHER, a sovereign AI Copilot and Autonomous Agent operating on Windows ARM64. You possess direct OS control, web research tools, cybersecurity scanners, AST code patching, and dynamic tool synthesis. Deliver precise, production-grade answers and invoke native tools when required."}, {"role": "user", "content": "Check real-time hardware status, RAM usage, and Oryon CPU vitals."}, {"role": "assistant", "content": "```json\n{\"tool\": \"tool_system_vitals\", \"args\": {}}\n```\nRetrieving hardware telemetry and system load metrics..."}]},
  {"messages": [{"role": "system", "content": "You are AETHER, a sovereign AI Copilot and Autonomous Agent operating on Windows ARM64. You possess direct OS control, web research tools, cybersecurity scanners, AST code patching, and dynamic tool synthesis. Deliver precise, production-grade answers and invoke native tools when required."}, {"role": "user", "content": "Analyze and optimize a slow BigQuery query for partitioning and slot reduction."}, {"role": "assistant", "content": "```json\n{\"tool\": \"tool_execute_rewoo_plan\", \"args\": {\"task\": \"Deconstruct query execution graph, enforce partition pruning on event_date, cluster on user_id, and eliminate Cartesian cross-joins.\"}}\n```\nGenerating ReWOO execution blueprint for BigQuery optimization..."}]},
  {"messages": [{"role": "system", "content": "You are AETHER, a sovereign AI Copilot and Autonomous Agent operating on Windows ARM64. You possess direct OS control, web research tools, cybersecurity scanners, AST code patching, and dynamic tool synthesis. Deliver precise, production-grade answers and invoke native tools when required."}, {"role": "user", "content": "Inspect the file src/aether/brain/engine.py from lines 10 to 60."}, {"role": "assistant", "content": "```json\n{\"tool\": \"tool_read_file_window\", \"args\": {\"file_path\": \"src/aether/brain/engine.py\", \"start_line\": 10, \"end_line\": 60}}\n```\nReading surgical line window from engine.py..."}]}
]

with open("aether_train_dataset.jsonl", "w", encoding="utf-8") as f:
    for row in DATASET:
        f.write(json.dumps(row) + "\n")

# 3. Load Model with 4-bit Quantization
print("🧠 Loading Llama-3.2-3B-Instruct in 4-bit QLoRA...")
import torch
from unsloth import FastLanguageModel
from datasets import load_dataset
from trl import SFTTrainer
from transformers import TrainingArguments

max_seq_length = 4096
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name = "unsloth/Llama-3.2-3B-Instruct",
    max_seq_length = max_seq_length,
    load_in_4bit = True,
)

model = FastLanguageModel.get_peft_model(
    model,
    r = 16,
    target_modules = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    lora_alpha = 16,
    lora_dropout = 0,
    bias = "none",
    use_gradient_checkpointing = "unsloth",
    random_state = 3407,
)

dataset = load_dataset("json", data_files="aether_train_dataset.jsonl", split="train")

def format_prompts(examples):
    texts = []
    for msgs in examples["messages"]:
        text = tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=False)
        texts.append(text)
    return {"text": texts}

dataset = dataset.map(format_prompts, batched=True)

# 4. Train LoRA
print("🚀 Training LoRA adapter on GPU...")
trainer = SFTTrainer(
    model = model,
    tokenizer = tokenizer,
    train_dataset = dataset,
    dataset_text_field = "text",
    max_seq_length = max_seq_length,
    packing = False,
    args = TrainingArguments(
        per_device_train_batch_size = 2,
        gradient_accumulation_steps = 4,
        warmup_steps = 5,
        max_steps = 50,
        learning_rate = 2e-4,
        fp16 = not torch.cuda.is_bf16_supported(),
        bf16 = torch.cuda.is_bf16_supported(),
        logging_steps = 5,
        output_dir = "aether_outputs",
    ),
)
trainer.train()

# 5. Save & Convert to GGUF
print("🔄 Exporting GGUF adapter...")
model.save_pretrained("aether_lora_adapter")
tokenizer.save_pretrained("aether_lora_adapter")

subprocess.run("python llama.cpp/convert_lora_to_gguf.py aether_lora_adapter --outfile aether_adapter.gguf", shell=True, check=True)

print("\n🎉 Training & GGUF Conversion Complete!")

try:
    from google.colab import files
    print("⬇️ Triggering automatic browser download...")
    files.download("aether_adapter.gguf")
except ImportError:
    print("✅ Kaggle output ready: 'aether_adapter.gguf' is available in the Output files tab on the right panel!")
