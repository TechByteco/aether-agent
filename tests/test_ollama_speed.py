import time
import ollama

print("Testing direct Ollama chat with simple prompt...")
t0 = time.time()
res = ollama.chat(
    model="llama3.2:3b",
    messages=[{"role": "user", "content": "Say 'hello' in one word."}],
    keep_alive="5m"
)
t1 = time.time()
print(f"Direct prompt time: {t1 - t0:.2f}s | Response: {res.message.content.strip()}")
