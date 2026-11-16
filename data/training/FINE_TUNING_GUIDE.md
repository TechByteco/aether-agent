# AETHER Autonomous Fine-Tuning Guide (Google Colab / Kaggle Free GPU)

This guide walks you through fine-tuning **AETHER** on **Google Colab** or **Kaggle** using **Unsloth (QLoRA)** on a free NVIDIA T4 GPU.

---

## 📋 Training Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       AETHER FINE-TUNING PIPELINE                           │
└─────────────────────────────────────────────────────────────────────────────┘
  1. Export Dataset locally  ➔  data/training/aether_train_dataset.jsonl
  2. Upload to Google Colab  ➔  Run Unsloth 2x Faster Fine-Tuning Script
  3. Export GGUF Weights     ➔  aether-custom-q4_k_m.gguf
  4. Import to Local Ollama  ➔  ollama create aether:custom -f Modelfile
```

---

## Step 1: Export Your Training Dataset

Your AETHER instance generates synthetic training pairs from autonomous evolution cycles and memory trajectories.

Export your current dataset by running:
```bash
python scripts/export_aether_training_data.py
```
This generates:
`data/training/aether_train_dataset.jsonl`

---

## Step 2: Open Google Colab (Free T4 GPU)

1. Open [colab.research.google.com](https://colab.research.google.com).
2. Create a **New Notebook**.
3. Set Runtime: **Runtime ➔ Change runtime type ➔ T4 GPU**.

---

## Step 3: Copy & Paste the Training Code into Colab

```python
# ==============================================================================
# 1. INSTALL UNSLOTH (Fast 2x QLoRA Training Engine)
# ==============================================================================
!pip install --no-deps "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"
!pip install --no-deps xformers "trl<0.9.0" peft accelerate bitsandbytes

# ==============================================================================
# 2. LOAD BASE MODEL (Llama 3.2 3B or Qwen 2.5 Coder 3B)
# ==============================================================================
from unsloth import FastLanguageModel
import torch

max_seq_length = 4096
dtype = None # Auto detection
load_in_4bit = True # 4bit quantization for minimal GPU memory

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name = "unsloth/Llama-3.2-3B-Instruct",
    max_seq_length = max_seq_length,
    dtype = dtype,
    load_in_4bit = load_in_4bit,
)

# Set up QLoRA Adapters
model = FastLanguageModel.get_peft_model(
    model,
    r = 16, # LoRA Rank
    target_modules = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    lora_alpha = 16,
    lora_dropout = 0,
    bias = "none",
    use_gradient_checkpointing = "unsloth",
    random_state = 3407,
)

# ==============================================================================
# 3. UPLOAD AND FORMAT DATASET
# ==============================================================================
from google.colab import files
uploaded = files.upload() # Upload your aether_train_dataset.jsonl file

from datasets import load_dataset
dataset = load_dataset("json", data_files="aether_train_dataset.jsonl", split="train")

def format_prompts(examples):
    texts = []
    for msgs in examples["messages"]:
        text = tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=False)
        texts.append(text)
    return { "text" : texts }

dataset = dataset.map(format_prompts, batched = True)

# ==============================================================================
# 4. START TRAINING
# ==============================================================================
from trl import SFTTrainer
from transformers import TrainingArguments

trainer = SFTTrainer(
    model = model,
    tokenizer = tokenizer,
    train_dataset = dataset,
    dataset_text_field = "text",
    max_seq_length = max_seq_length,
    dataset_num_proc = 2,
    packing = False, # Can make training 5x faster for short sequences
    args = TrainingArguments(
        per_device_train_batch_size = 2,
        gradient_accumulation_steps = 4,
        warmup_steps = 5,
        max_steps = 60, # Increase for larger datasets
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

# ==============================================================================
# 5. EXPORT DIRECTLY TO GGUF (FOR LOCAL OLLAMA / AETHER)
# ==============================================================================
model.save_pretrained_gguf("aether_model_gguf", tokenizer, quantization_method = "q4_k_m")
```

---

## Step 4: Import Trained GGUF into Local AETHER & Ollama

1. Download the generated `aether_model_gguf/unsloth.Q4_K_M.gguf` file from Colab to your laptop.
2. Place it in `c:\Users\saali\.ollama\models\` or your external drive.
3. Create a `Modelfile`:
   ```dockerfile
   FROM ./unsloth.Q4_K_M.gguf
   PARAMETER temperature 0.3
   PARAMETER num_ctx 4096
   SYSTEM "You are AETHER, fine-tuned on custom execution trajectories and cognitive heuristics."
   ```
4. Build model in terminal:
   ```bash
   ollama create aether:custom -f Modelfile
   ```
5. Select `aether:custom` in AETHER's web interface or set `local_model = "aether:custom"` in `config.py`!
