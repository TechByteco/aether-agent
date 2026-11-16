# ==============================================================================
# AETHER FAST KAGGLE CODE CELL
# Copy and paste this single script into a new Kaggle Code Notebook (with GPU T4 enabled)
# ==============================================================================

# 1. Install Unsloth
!pip install --no-deps "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"
!pip install --no-deps xformers "trl<0.9.0" peft accelerate bitsandbytes datasets

# 2. Write training dataset directly in Kaggle
import json

training_data = [
    {
        "messages": [
            {"role": "system", "content": "You are AETHER, a sovereign AI Copilot and Autonomous Agent. You possess direct OS control, web research tools, cybersecurity scanners, and system vitals inspection. Deliver precise, production-grade answers and invoke native tools when required."},
            {"role": "user", "content": "Scan the current project for exposed secrets or API keys."},
            {"role": "assistant", "content": '```json\n{"tool": "tool_hunt_exposed_secrets", "args": {"target_dir": "."}}\n```'}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": "You are AETHER, a sovereign AI Copilot and Autonomous Agent. You possess direct OS control, web research tools, cybersecurity scanners, and system vitals inspection. Deliver precise, production-grade answers and invoke native tools when required."},
            {"role": "user", "content": "Check active network connections and listening ports on this machine."},
            {"role": "assistant", "content": '```json\n{"tool": "tool_audit_active_connections", "args": {"filter_state": "ALL"}}\n```'}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": "You are AETHER, a sovereign AI Copilot and Autonomous Agent. You possess direct OS control, web research tools, cybersecurity scanners, and system vitals inspection. Deliver precise, production-grade answers and invoke native tools when required."},
            {"role": "user", "content": "Benchmark the API endpoint http://127.0.0.1:8000/ to check latency and throughput."},
            {"role": "assistant", "content": '```json\n{"tool": "tool_benchmark_api_endpoint", "args": {"url": "http://127.0.0.1:8000/", "num_requests": 10}}\n```'}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": "You are AETHER, a sovereign AI Copilot and Autonomous Agent. You possess direct OS control, web research tools, cybersecurity scanners, and system vitals inspection. Deliver precise, production-grade answers and invoke native tools when required."},
            {"role": "user", "content": "Audit the codebase architecture in src/aether for god files and complexity debt."},
            {"role": "assistant", "content": '```json\n{"tool": "tool_audit_codebase_architecture", "args": {"target_dir": "src/aether"}}\n```'}
        ]
    }
]

with open("aether_train_dataset.jsonl", "w", encoding="utf-8") as f:
    for item in training_data:
        f.write(json.dumps(item) + "\n")

print("✓ Dataset written: aether_train_dataset.jsonl")

# 3. Load base model & configure QLoRA
from unsloth import FastLanguageModel
import torch
from datasets import load_dataset
from trl import SFTTrainer
from transformers import TrainingArguments

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name = "unsloth/Llama-3.2-3B-Instruct",
    max_seq_length = 4096,
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

# Format prompts
dataset = load_dataset("json", data_files="aether_train_dataset.jsonl", split="train")

def format_prompts(examples):
    texts = []
    for msgs in examples["messages"]:
        text = tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=False)
        texts.append(text)
    return { "text" : texts }

dataset = dataset.map(format_prompts, batched = True)

# 4. Train
trainer = SFTTrainer(
    model = model,
    tokenizer = tokenizer,
    train_dataset = dataset,
    dataset_text_field = "text",
    max_seq_length = 4096,
    dataset_num_proc = 2,
    packing = False,
    args = TrainingArguments(
        per_device_train_batch_size = 2,
        gradient_accumulation_steps = 4,
        warmup_steps = 5,
        max_steps = 30,
        learning_rate = 2e-4,
        fp16 = not torch.cuda.is_bf16_supported(),
        bf16 = torch.cuda.is_bf16_supported(),
        logging_steps = 1,
        optim = "adamw_8bit",
        weight_decay = 0.01,
        lr_scheduler_type = "linear",
        seed = 3407,
        output_dir = "outputs",
    ),
)

trainer.train()

# 5. Export directly to GGUF
model.save_pretrained_gguf("aether_trained_model", tokenizer, quantization_method = "q4_k_m")
print("🎉 Model successfully trained and exported to: aether_trained_model/unsloth.Q4_K_M.gguf")
