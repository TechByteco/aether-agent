"""Visual benchmark demonstrating token compression across popular web sites."""

import asyncio
from obscura_engine import AsyncObscuraAgentEngine


TEST_URLS = [
    ("Hacker News", "https://news.ycombinator.com"),
    ("Python Documentation", "https://docs.python.org/3/"),
    ("Wikipedia (Web Browser)", "https://en.wikipedia.org/wiki/Web_browser"),
]


async def run_benchmarks():
    print("=" * 80)
    print(" Obscura Enchanted Agent Engine - Token Compression Benchmark Suite")
    print("=" * 80)
    print(f"{'Site Name':<25} | {'Raw Tokens':<12} | {'Distilled':<12} | {'Savings %':<10} | {'Action Refs'}")
    print("-" * 80)

    engine = AsyncObscuraAgentEngine()
    await engine.initialize()

    for name, url in TEST_URLS:
        try:
            snap = await engine.navigate(url)
            print(
                f"{name:<25} | "
                f"~{snap.estimated_raw_tokens:<11,} | "
                f"~{snap.estimated_distilled_tokens:<11,} | "
                f"{snap.token_savings_pct:>7.1f}%   | "
                f"{len(snap.interactive_elements)} controls"
            )
        except Exception as e:
            print(f"{name:<25} | Error: {e}")

    print("-" * 80)
    metrics = engine.session_pool.get_metrics()
    print(f"Total prompt tokens saved across benchmark: ~{metrics.total_tokens_saved:,} tokens")
    print("=" * 80)
    await engine.close()


if __name__ == "__main__":
    asyncio.run(run_benchmarks())
