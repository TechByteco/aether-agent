"""Self-contained test runner executing all unit tests with zero external test framework dependency."""

import asyncio
import sys
import traceback

# Import core test functions
from tests.test_distiller import (
    test_distiller_strips_noise_and_svg,
    test_distiller_form_controls,
    test_distiller_markdown_table,
)
from tests.test_diff_engine import (
    test_diff_engine_detects_mutations,
    test_diff_engine_no_change,
)
from tests.test_session_pool import (
    test_session_pool_acquisition_and_lru,
    test_session_pool_metrics,
)
from tests.test_mcp_server import (
    test_mcp_initialize,
    test_mcp_tools_list,
    test_mcp_tools_call_stats,
)
from tests.test_production_features import (
    test_snapshot_cache,
    test_retry_policy,
    test_rate_limiter,
    test_telemetry_metrics,
    test_page_analyzer,
    test_js_executor,
)
from tests.test_api_server import (
    test_api_health,
    test_api_metrics,
    test_api_sessions_lifecycle,
    test_api_snapshot_and_diff,
)


def run_all():
    sync_tests = [
        ("test_distiller_strips_noise_and_svg", test_distiller_strips_noise_and_svg),
        ("test_distiller_form_controls", test_distiller_form_controls),
        ("test_distiller_markdown_table", test_distiller_markdown_table),
        ("test_diff_engine_detects_mutations", test_diff_engine_detects_mutations),
        ("test_diff_engine_no_change", test_diff_engine_no_change),
        ("test_snapshot_cache", test_snapshot_cache),
        ("test_retry_policy", test_retry_policy),
        ("test_telemetry_metrics", test_telemetry_metrics),
        ("test_page_analyzer", test_page_analyzer),
        ("test_js_executor", test_js_executor),
        ("test_api_health", test_api_health),
        ("test_api_metrics", test_api_metrics),
        ("test_api_sessions_lifecycle", test_api_sessions_lifecycle),
        ("test_api_snapshot_and_diff", test_api_snapshot_and_diff),
    ]

    async_tests = [
        ("test_session_pool_acquisition_and_lru", test_session_pool_acquisition_and_lru),
        ("test_session_pool_metrics", test_session_pool_metrics),
        ("test_mcp_initialize", test_mcp_initialize),
        ("test_mcp_tools_list", test_mcp_tools_list),
        ("test_mcp_tools_call_stats", test_mcp_tools_call_stats),
        ("test_rate_limiter", test_rate_limiter),
    ]

    passed = 0
    failed = 0

    print("==================================================")
    print(" Running Obscura Enchanted Agent Engine Test Suite")
    print("==================================================")

    for name, func in sync_tests:
        try:
            func()
            print(f" PASS: {name}")
            passed += 1
        except Exception as e:
            print(f" FAIL: {name}")
            traceback.print_exc()
            failed += 1

    for name, func in async_tests:
        try:
            asyncio.run(func())
            print(f" PASS: {name}")
            passed += 1
        except Exception as e:
            print(f" FAIL: {name}")
            traceback.print_exc()
            failed += 1

    print("==================================================")
    print(f"Total: {passed + failed} | Passed: {passed} | Failed: {failed}")
    print("==================================================")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    run_all()
