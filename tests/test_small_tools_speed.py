import time
import ollama

def tool_calc(expression: str) -> str:
    """Calculate math expression."""
    return str(eval(expression))

def tool_search(query: str) -> str:
    """Search the web."""
    return "search results for " + query

tools_small = [tool_calc, tool_search]

print("Benchmarking with 2 compact tools...")
t0 = time.time()
r = ollama.chat(
    model="llama3.2:3b",
    messages=[{"role": "user", "content": "What is 25 * 4?"}],
    tools=tools_small,
    keep_alive="5m"
)
t1 = time.time()
print(f"2 tools latency: {t1 - t0:.2f}s | calls: {r.message.tool_calls}")
