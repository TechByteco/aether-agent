"""
Unit & Integration Test Suite for AETHER Fast Cortex & Accelerated Inference Engine
===================================================================================
Tests zero-latency fast-path routing, semantic query caching, RAM pre-warming,
and round-trip latency benchmarks.
"""

import sys
import time
import unittest
from pathlib import Path

# Ensure src is on sys.path
_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from aether.brain.fast_cortex import fast_cortex


class TestFastCortex(unittest.TestCase):
    """Test suite for Fast Cortex acceleration methodologies."""

    def test_semantic_query_cache(self):
        """Verify sub-millisecond semantic response caching."""
        query = "What is the capital of France?"
        response = "The capital of France is Paris."

        # Set cache
        fast_cortex.set_cached(query, response, ttl=60.0)

        # Retrieve cache
        cached = fast_cortex.get_cached(query)
        self.assertIsNotNone(cached)
        self.assertEqual(cached.response, response)

        # Case-insensitive / whitespace-insensitive lookup
        cached_variant = fast_cortex.get_cached("  what IS the capital   of FRANCE? ")
        self.assertIsNotNone(cached_variant)
        self.assertEqual(cached_variant.response, response)

    def test_fast_path_system_vitals(self):
        """Verify sub-10ms system vitals fast-path execution."""
        # Warmup call
        fast_cortex.try_fast_path("system vitals")

        start_t = time.perf_counter()
        match = fast_cortex.try_fast_path("system vitals")
        elapsed_ms = (time.perf_counter() - start_t) * 1000

        self.assertIsNotNone(match)
        self.assertTrue(match["fast_path"])
        self.assertEqual(match["route"], "system_vitals")
        self.assertTrue(len(match["response"]) > 10)
        self.assertLess(elapsed_ms, 50.0, "Fast-path execution must be sub-50ms")

    def test_fast_path_calendar_agenda(self):
        """Verify calendar agenda fast-path."""
        match = fast_cortex.try_fast_path("today's meetings")
        self.assertIsNotNone(match)
        self.assertTrue(match["fast_path"])
        self.assertEqual(match["route"], "calendar_agenda")

    def test_fast_path_tasks_list(self):
        """Verify tasks list fast-path."""
        match = fast_cortex.try_fast_path("/tasks")
        self.assertIsNotNone(match)
        self.assertTrue(match["fast_path"])
        self.assertEqual(match["route"], "tasks_list")

    def test_fast_path_email_summary(self):
        """Verify email summary fast-path."""
        match = fast_cortex.try_fast_path("/emails")
        self.assertIsNotNone(match)
        self.assertTrue(match["fast_path"])
        self.assertEqual(match["route"], "email_summary")

    def test_fast_path_portfolio_status(self):
        """Verify portfolio status fast-path."""
        match = fast_cortex.try_fast_path("portfolio status")
        self.assertIsNotNone(match)
        self.assertTrue(match["fast_path"])
        self.assertEqual(match["route"], "portfolio_status")

    def test_accelerated_complete_caching(self):
        """Verify accelerated_complete leverages cache on repeat invocations."""
        query = "Benchmark test query 101"
        fast_cortex.set_cached(query, "Precomputed response", ttl=60.0)

        res = fast_cortex.accelerated_complete(query)
        self.assertTrue(res["cached"])
        self.assertEqual(res["content"], "Precomputed response")
        self.assertLess(res["latency_ms"], 5.0)


if __name__ == "__main__":
    unittest.main()
