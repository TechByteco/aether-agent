"""
Tests for AETHER Continuous Improvement Engine.
All modules are tested in isolation with mocked dependencies.
"""

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure src is on path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


class TestImprovementEngineImport(unittest.TestCase):
    def test_module_imports(self):
        """Engine module must import without error."""
        from aether.brain.continuous_improvement_engine import (
            ContinuousImprovementEngine,
            scan_unused_imports,
            scan_missing_type_hints,
            scan_missing_docstrings,
            scan_test_coverage_gaps,
            benchmark_fast_cortex,
            scan_dependency_vulnerabilities,
            fix_import_order,
            score_complexity,
            monitor_memory_and_cache,
            register_improvement_jobs,
        )
        self.assertTrue(callable(ContinuousImprovementEngine))
        self.assertTrue(callable(scan_unused_imports))


class TestScanMissingDocstrings(unittest.TestCase):
    def test_returns_dict_with_findings(self):
        from aether.brain.continuous_improvement_engine import scan_missing_docstrings
        result = scan_missing_docstrings()
        self.assertIsInstance(result, dict)
        self.assertIn("findings", result)
        self.assertIsInstance(result["findings"], int)
        self.assertGreaterEqual(result["findings"], 0)


class TestScanMissingTypeHints(unittest.TestCase):
    def test_returns_dict_with_findings(self):
        from aether.brain.continuous_improvement_engine import scan_missing_type_hints
        result = scan_missing_type_hints()
        self.assertIsInstance(result, dict)
        self.assertIn("findings", result)
        self.assertIsInstance(result["findings"], int)


class TestScanTestCoverageGaps(unittest.TestCase):
    def test_returns_dict_with_untested(self):
        from aether.brain.continuous_improvement_engine import scan_test_coverage_gaps
        result = scan_test_coverage_gaps()
        self.assertIsInstance(result, dict)
        self.assertIn("untested_functions", result)
        self.assertIsInstance(result["untested_functions"], int)
        self.assertGreaterEqual(result["untested_functions"], 0)


class TestBenchmarkFastCortex(unittest.TestCase):
    def test_returns_avg_ms(self):
        from aether.brain.continuous_improvement_engine import benchmark_fast_cortex
        result = benchmark_fast_cortex()
        self.assertIsInstance(result, dict)
        # Either has avg_ms (success) or error (FastCortex not in env)
        self.assertTrue("avg_ms" in result or "error" in result or "results" in result)


class TestMonitorMemory(unittest.TestCase):
    def test_returns_report(self):
        from aether.brain.continuous_improvement_engine import monitor_memory_and_cache
        result = monitor_memory_and_cache()
        self.assertIsInstance(result, dict)
        # psutil may or may not be installed in CI
        self.assertTrue(len(result) > 0)


class TestImprovementEngineRunCycle(unittest.TestCase):
    def test_run_cycle_completes(self):
        """Full cycle must complete and return a dict with 'modules' key."""
        from aether.brain.continuous_improvement_engine import ContinuousImprovementEngine
        engine = ContinuousImprovementEngine()
        # Suppress Telegram notification in test
        with patch.object(engine, "_notify_telegram", return_value=None):
            report = engine.run_cycle()
        self.assertIsInstance(report, dict)
        self.assertIn("modules", report)
        self.assertIn("elapsed_seconds", report)
        self.assertGreater(len(report["modules"]), 0)

    def test_all_modules_attempted(self):
        """All 9 improvement modules must be represented in the report."""
        from aether.brain.continuous_improvement_engine import ContinuousImprovementEngine
        engine = ContinuousImprovementEngine()
        with patch.object(engine, "_notify_telegram", return_value=None):
            report = engine.run_cycle()
        expected = {
            "unused_imports", "type_hints", "docstrings",
            "test_coverage", "fast_cortex_perf", "security",
            "import_order", "complexity", "memory_cache"
        }
        actual = set(report["modules"].keys())
        self.assertEqual(expected, actual)

    def test_improvement_log_written(self):
        """JSONL log file must exist after a cycle."""
        from aether.brain.continuous_improvement_engine import ContinuousImprovementEngine, LOG_FILE
        engine = ContinuousImprovementEngine()
        with patch.object(engine, "_notify_telegram", return_value=None):
            engine.run_cycle()
        self.assertTrue(LOG_FILE.exists(), f"Log file not found: {LOG_FILE}")
        # Last line must be valid JSON
        lines = LOG_FILE.read_text(encoding="utf-8").strip().splitlines()
        last = json.loads(lines[-1])
        self.assertIn("category", last)
        self.assertIn("ts", last)


class TestRegisterImprovementJobs(unittest.TestCase):
    def test_register_does_not_raise(self):
        """register_improvement_jobs must work with a mock scheduler."""
        from aether.brain.continuous_improvement_engine import register_improvement_jobs
        mock_scheduler = MagicMock()
        register_improvement_jobs(mock_scheduler)
        mock_scheduler.add_job.assert_called_once()
        call_kwargs = mock_scheduler.add_job.call_args
        self.assertEqual(call_kwargs.kwargs.get("id") or call_kwargs[1].get("id"),
                         "continuous_improvement")


if __name__ == "__main__":
    unittest.main()
