"""Autonomous multi-step browsing agent demonstrating the Obscura Enchanted Agent Engine."""

import asyncio
from obscura_engine import AsyncObscuraAgentEngine, ActionType, BrowserAction


async def main():
    print("Initializing Obscura Enchanted Agent Engine...")
    engine = AsyncObscuraAgentEngine(max_tabs=5)
    tab = await engine.initialize(agent_id="researcher-01")
    print(f"Session established: Tab {tab.tab_id} (Memory cap: {tab.memory_mb} MB)")

    # Step 1: Navigate to Hacker News
    print("\n--- Step 1: Navigating to Hacker News ---")
    snapshot = await engine.navigate("https://news.ycombinator.com")
    print(f"Page Title: {snapshot.title}")
    print(f"Raw Characters: {snapshot.raw_char_count:,} ➔ Distilled Characters: {snapshot.distilled_char_count:,}")
    print(f"Token Savings: {snapshot.token_savings_pct}% (Raw ~{snapshot.estimated_raw_tokens} ➔ Distilled ~{snapshot.estimated_distilled_tokens} tokens)")
    print(f"Identified Actionable Controls: {len(snapshot.interactive_elements)}")

    # Print first few lines of distilled markdown
    print("\n[Preview of Distilled Snapshot Markdown]:")
    print("\n".join(snapshot.markdown.splitlines()[:15]))

    # Step 2: Extract top stories structured data
    print("\n--- Step 2: Extracting Top Stories Structured Data ---")
    stories = engine.extract_structured_data(
        query_selector="tr.athing",
        fields={
            "rank": "span.rank",
            "title": "span.titleline > a",
            "site": "span.sitestr"
        }
    )
    print(f"Extracted {len(stories)} stories. Top 3:")
    for s in stories[:3]:
        print(f"  {s.get('rank', '')} {s.get('title', '')} ({s.get('site', 'news.ycombinator.com')})")

    # Step 3: Perform an action using deterministic ref tag
    if snapshot.interactive_elements:
        first_ref = snapshot.interactive_elements[0].ref_id
        print(f"\n--- Step 3: Performing Atomic Action on [@ref:{first_ref}] ---")
        action_res = await engine.act(BrowserAction(action=ActionType.CLICK, ref=first_ref))
        print("Action Execution Result:", action_res)

        # Step 4: Emit DOM diff instead of full page snapshot
        print("\n--- Step 4: Calculating State Mutation Diff ---")
        diff = engine.diff_snapshot()
        print(f"Diff Summary: {diff.summary}")
        print("Diff Payload:\n", diff.diff_markdown[:300])

    # Step 5: Report session performance metrics
    metrics = engine.session_pool.get_metrics()
    print("\n--- Session Performance Metrics ---")
    print(f"Active Tabs: {metrics.active_tabs}")
    print(f"Total Actions Executed: {metrics.total_actions_executed}")
    print(f"Total Tokens Saved for LLM: {metrics.total_tokens_saved:,} tokens")
    print(f"RAM Usage: {metrics.memory_usage_mb} MB")

    await engine.close()
    print("\nBrowser closed successfully.")


if __name__ == "__main__":
    asyncio.run(main())
