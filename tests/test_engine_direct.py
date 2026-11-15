import time
import sys, os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))
os.chdir(str(ROOT_DIR))

from aether.brain.engine import engine

user_msg = "Hello AETHER, report your status, active model, and memory count in one crisp sentence."
print("Preparing messages...")
messages = engine._prepare_turn_messages(user_msg)
print(f"Total messages: {len(messages)}")
for i, m in enumerate(messages):
    print(f"  [{i}] {m['role']}: {len(m['content'])} chars | preview: {m['content'][:60]}...")

import ollama
active_model = engine.resolve_active_model()
print(f"\nCalling ollama.chat with active model {active_model}...")
t0 = time.time()
res = ollama.chat(
    model=active_model,
    messages=messages,
    keep_alive="5m"
)
t1 = time.time()
print(f"Response in {t1 - t0:.2f}s:")
print(res.message.content)
