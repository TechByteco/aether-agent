"""Extended type definitions for large-scale production use."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ActionType(str, Enum):
    CLICK = "click"
    TYPE = "type"
    SELECT = "select"
    HOVER = "hover"
    SCROLL = "scroll"
    PRESS_KEY = "press_key"
    CLEAR = "clear"
    DOUBLE_CLICK = "double_click"
    RIGHT_CLICK = "right_click"
    FOCUS = "focus"
    BLUR = "blur"
    UPLOAD = "upload"


class PageType(str, Enum):
    ARTICLE = "article"
    SEARCH_RESULTS = "search_results"
    PRODUCT_LISTING = "product_listing"
    LOGIN_FORM = "login_form"
    CHECKOUT = "checkout"
    DASHBOARD = "dashboard"
    ERROR_PAGE = "error_page"
    GENERIC = "generic"


class InteractiveElement(BaseModel):
    """An interactive control on the page with a deterministic agent reference."""
    ref_id: str = Field(description="Deterministic integer ref tag (e.g. '1', '14')")
    tag_name: str = Field(description="HTML tag name (e.g. 'button', 'input', 'a')")
    role: Optional[str] = Field(default=None, description="ARIA or semantic role")
    text: str = Field(default="", description="Visible text or label")
    selector: str = Field(description="Unambiguous CSS selector targeting this element")
    attributes: Dict[str, str] = Field(default_factory=dict, description="HTML attributes")
    value: Optional[str] = Field(default=None, description="Current value of input or textarea")
    is_clickable: bool = Field(default=True)
    aria_label: Optional[str] = Field(default=None)
    is_disabled: bool = Field(default=False)
    is_visible: bool = Field(default=True)


class DistilledSnapshot(BaseModel):
    """Token-optimized semantic snapshot of a web page for LLM ingestion."""
    url: str
    title: str
    markdown: str = Field(description="Token-compressed Markdown with [@ref:id] tags")
    interactive_elements: List[InteractiveElement] = Field(default_factory=list)
    raw_char_count: int = 0
    distilled_char_count: int = 0
    estimated_raw_tokens: int = 0
    estimated_distilled_tokens: int = 0
    token_savings_pct: float = 0.0
    page_type: Optional[str] = None
    language: Optional[str] = None
    meta: Dict[str, str] = Field(default_factory=dict, description="OG/meta tags")
    content_hash: Optional[str] = None


class DomDiff(BaseModel):
    """Semantic mutations in the DOM between two consecutive agent turns."""
    previous_url: str
    current_url: str
    has_changed: bool
    summary: str
    added_elements: List[InteractiveElement] = Field(default_factory=list)
    modified_elements: List[InteractiveElement] = Field(default_factory=list)
    removed_ref_ids: List[str] = Field(default_factory=list)
    diff_markdown: str = Field(default="")
    navigation_occurred: bool = False


class BrowserAction(BaseModel):
    """An atomic action requested by an autonomous agent."""
    action: ActionType
    ref: Optional[str] = Field(default=None, description="Ref ID from DistilledSnapshot")
    selector: Optional[str] = Field(default=None, description="Fallback CSS selector")
    value: Optional[str] = Field(default=None)
    key: Optional[str] = Field(default=None)
    scroll_delta_y: Optional[int] = Field(default=None)
    scroll_delta_x: Optional[int] = Field(default=None)
    timeout_ms: int = Field(default=10000)
    expect_navigation: bool = Field(default=False)


class FormFieldEntry(BaseModel):
    """A field to populate in a batch form fill operation."""
    ref_or_selector: str
    value: str
    field_type: Optional[str] = "text"
    clear_first: bool = True


class TabSession(BaseModel):
    """Metadata tracking a single agent tab in the session pool."""
    tab_id: str
    agent_id: str
    url: str = "about:blank"
    title: str = ""
    memory_mb: float = 30.0
    created_at: float
    last_accessed: float
    is_active: bool = True
    request_count: int = 0
    total_tokens_saved: int = 0
    navigation_history: List[str] = Field(default_factory=list)
    tags: Dict[str, str] = Field(default_factory=dict)


class EngineMetrics(BaseModel):
    """Real-time performance metrics."""
    active_tabs: int
    total_tabs_created: int
    memory_usage_mb: float
    total_tokens_saved: int
    average_token_compression_pct: float
    total_actions_executed: int
    total_navigations: int = 0
    total_cache_hits: int = 0
    cache_hit_rate_pct: float = 0.0
    uptime_seconds: float
    requests_per_minute: float = 0.0


class CrawlPolicy(BaseModel):
    """Policy controlling autonomous crawl behavior."""
    max_pages: int = 100
    max_depth: int = 5
    allowed_domains: List[str] = Field(default_factory=list)
    blocked_patterns: List[str] = Field(default_factory=list)
    crawl_delay_ms: int = 1000
    respect_robots_txt: bool = True
    follow_external_links: bool = False


class AgentConfig(BaseModel):
    """Full agent configuration for large-scale deployments."""
    agent_id: str
    max_tabs: int = 5
    timeout_seconds: float = 30.0
    stealth_mode: bool = True
    cache_enabled: bool = True
    retry_on_failure: bool = True
    max_retries: int = 3
    crawl_policy: Optional[CrawlPolicy] = None
    api_key: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
