import asyncio
from obscura_engine.session_pool import SessionPool


async def test_session_pool_acquisition_and_lru():
    # Pool with limit of 2 tabs
    pool = SessionPool(max_active_tabs=2, max_memory_mb_per_tab=30.0)

    tab1 = await pool.acquire_tab(agent_id="agent-1", tab_id="tab-1")
    assert tab1.tab_id == "tab-1"
    assert len(pool.list_tabs()) == 1

    await asyncio.sleep(0.01)
    tab2 = await pool.acquire_tab(agent_id="agent-2", tab_id="tab-2")
    assert tab2.tab_id == "tab-2"
    assert len(pool.list_tabs()) == 2

    # Acquiring 3rd tab must evict tab1 (the LRU tab)
    await asyncio.sleep(0.01)
    tab3 = await pool.acquire_tab(agent_id="agent-3", tab_id="tab-3")
    assert len(pool.list_tabs()) == 2
    assert pool.get_tab("tab-1") is None
    assert pool.get_tab("tab-2") is not None
    assert pool.get_tab("tab-3") is not None


async def test_session_pool_metrics():
    pool = SessionPool(max_active_tabs=5, max_memory_mb_per_tab=32.0)
    await pool.acquire_tab(agent_id="test-agent")
    pool.record_action()
    pool.record_token_savings(1500)

    metrics = pool.get_metrics()
    assert metrics.active_tabs == 1
    assert metrics.memory_usage_mb == 32.0
    assert metrics.total_tokens_saved == 1500
    assert metrics.total_actions_executed == 1
