import time
import ollama

system_lean = """You are AETHER, an advanced, decisive, proactive personal AI companion on Windows ARM64.
You have full hands-on computer control: open applications, play media, analyze screen, execute python code, run shell commands, and read/write files.
Be sharp, poised, and helpful. Deliver immediate results without unnecessary disclaimers."""

messages = [
    {"role": "system", "content": system_lean},
    {"role": "user", "content": "Hello AETHER, report your status, active model, and memory count in one crisp sentence."}
]

print("Testing lean prompt latency...")
t0 = time.time()
res = ollama.chat(
    model="llama3.2:3b",
    messages=messages,
    keep_alive="5m"
)
t1 = time.time()
print(f"Latency: {t1 - t0:.2f}s | Response: {res.message.content.strip()}")

# Test Turn 2 with cached prefix
messages.append({"role": "assistant", "content": res.message.content})
messages.append({"role": "user", "content": "Give me one random cool fact about quantum computing."})

print("\nTesting Turn 2 with cached KV prefix...")
t2 = time.time()
res2 = ollama.chat(
    model="llama3.2:3b",
    messages=messages,
    keep_alive="5m"
)
t3 = time.time()
print(f"Turn 2 latency: {t3 - t2:.2f}s | Response: {res2.message.content.strip()[:60]}...")
