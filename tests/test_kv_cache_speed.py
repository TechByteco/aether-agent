import time
import ollama

messages = [
    {"role": "system", "content": "You are AETHER, a concise personal AI companion."},
    {"role": "user", "content": "Ping 1"}
]

print("Turn 1 (uncached prefix)...")
t0 = time.time()
res1 = ollama.chat(model="llama3.2:3b", messages=messages, keep_alive="5m")
t1 = time.time()
print(f"Turn 1 took: {t1 - t0:.2f}s | {res1.message.content.strip()[:40]}")

messages.append({"role": "assistant", "content": res1.message.content})
messages.append({"role": "user", "content": "Ping 2"})

print("\nTurn 2 (cached prefix - testing KV reuse)...")
t2 = time.time()
res2 = ollama.chat(model="llama3.2:3b", messages=messages, keep_alive="5m")
t3 = time.time()
print(f"Turn 2 took: {t3 - t2:.2f}s | {res2.message.content.strip()[:40]}")
