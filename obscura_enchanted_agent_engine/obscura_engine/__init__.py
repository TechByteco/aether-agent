"""Obscura Enchanted Agent Engine.

Ultra-lightweight 30MB V8 headless browser engine designed for autonomous AI agents,
featuring Semantic DOM Token Distillation, Mutation Diff Tracking, Model Context Protocol (MCP),
and high-concurrency production REST + SSE streaming API.
"""

from .agent_memory import BrowsingMemory
from .cache import ResponseCache, RobotsTxtCache, SnapshotCache
from .client import AsyncObscuraAgentEngine
from .crawler import CrawlPolicy, CrawlResult, WebCrawler
from .diff_engine import DomDiffEngine
from .distiller import DomDistiller
from .js_executor import JsExecutor
from .logging_config import StructuredLogger, setup_logging
from .mcp_server import ObscuraMcpServer
from .page_analyzer import PageAnalyzer
from .rate_limiter import AgentRateLimiter, SlidingWindowRateLimiter
from .retry import NavigationError, RetryPolicy, with_retry
from .session_pool import SessionPool
from .telemetry import EngineCounter, EngineGauge, EngineHistogram, MetricsRegistry
from .types import (
    ActionType,
    AgentConfig,
    BrowserAction,
    DistilledSnapshot,
    DomDiff,
    EngineMetrics,
    FormFieldEntry,
    InteractiveElement,
    PageType,
    TabSession,
)

__version__ = "1.1.0"
__all__ = [
    # Core Engine
    "AsyncObscuraAgentEngine",
    "DomDistiller",
    "DomDiffEngine",
    "SessionPool",
    "ObscuraMcpServer",
    # Types
    "ActionType",
    "PageType",
    "InteractiveElement",
    "DistilledSnapshot",
    "DomDiff",
    "BrowserAction",
    "FormFieldEntry",
    "TabSession",
    "EngineMetrics",
    "CrawlPolicy",
    "AgentConfig",
    # Performance & Resilience
    "SnapshotCache",
    "ResponseCache",
    "RobotsTxtCache",
    "RetryPolicy",
    "NavigationError",
    "with_retry",
    "SlidingWindowRateLimiter",
    "AgentRateLimiter",
    # Intelligence & Evaluation
    "PageAnalyzer",
    "BrowsingMemory",
    "JsExecutor",
    "WebCrawler",
    "CrawlResult",
    # Observability & Logging
    "MetricsRegistry",
    "EngineCounter",
    "EngineHistogram",
    "EngineGauge",
    "StructuredLogger",
    "setup_logging",
]
