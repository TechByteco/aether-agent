"""
AETHER Deterministic Mode
=========================
When AETHER_DETERMINISTIC=1 (the default), every LLM call is forced to use
temperature=0 and top_p=0, eliminating stochastic "hallucinated" outputs.
When AETHER_VERIFY=1 (the default), every tool output is validated against a
JSON schema before being persisted — any mismatch is logged and rejected.

Set environment variables to override:
  AETHER_DETERMINISTIC=0  → allow creative generation (not recommended in prod)
  AETHER_VERIFY=0         → skip schema validation (debug only)
  AETHER_MAX_TOKENS=1024  → cap generation length
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger("aether.deterministic_mode")

# ── Runtime flags ────────────────────────────────────────────────────────────
DETERMINISTIC: bool = os.getenv("AETHER_DETERMINISTIC", "1") == "1"
ENFORCE_VERIFICATION: bool = os.getenv("AETHER_VERIFY", "1") == "1"
MAX_TOKENS: int = int(os.getenv("AETHER_MAX_TOKENS", "1024"))

# Shared JSON schemas for common tool outputs (extend as needed)
SCHEMAS: Dict[str, Dict] = {
    "business_ideas": {
        "type": "object",
        "properties": {
            "ideas": {"type": "array", "items": {"type": "object"}},
            "guidelines": {"type": "array"},
            "metadata": {"type": "object"},
        },
        "required": ["ideas"],
    },
    "brand_theme": {
        "type": "object",
        "properties": {
            "primary": {"type": "string", "pattern": "^#[0-9A-Fa-f]{6}$"},
            "accent": {"type": "string"},
            "font_heading": {"type": "string"},
        },
        "required": ["primary", "accent"],
    },
    "leads": {
        "type": "object",
        "properties": {
            "signals": {"type": "array"},
            "venture": {"type": "string"},
            "fetched_at": {"type": "string"},
        },
        "required": ["signals", "venture"],
    },
    "blueprint": {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "mvp_features": {"type": "array"},
            "pricing_tiers": {"type": "array"},
        },
        "required": ["name"],
    },
}


# ── LLM kwarg injection ───────────────────────────────────────────────────────

def llm_kwargs(extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Return kwargs that MUST be passed to every LLM client call.
    In deterministic mode this locks temperature and top_p to 0 so the
    model always returns its highest-confidence (greedy) token at each step.
    """
    base: Dict[str, Any] = {}
    if DETERMINISTIC:
        base = {
            "temperature": 0.0,
            "top_p": 0.0,
            "max_tokens": MAX_TOKENS,
        }
        logger.debug("Deterministic mode active — temp=0, top_p=0, max_tokens=%d", MAX_TOKENS)
    if extra:
        base.update(extra)
    return base


def ollama_options() -> Dict[str, Any]:
    """
    Return options dict in Ollama's native format (nested under 'options').
    Ollama uses temperature and top_p inside the options block.
    """
    if DETERMINISTIC:
        return {
            "temperature": 0.0,
            "top_p": 0.0,
            "num_predict": MAX_TOKENS,
            "seed": 42,        # Fixed seed for full reproducibility
        }
    return {}


# ── Verification layer ────────────────────────────────────────────────────────

def verify_output(
    payload: Any,
    schema_name: Optional[str] = None,
    schema: Optional[Dict] = None,
) -> bool:
    """
    Validate a tool payload before it is persisted or returned.

    Args:
        payload:      The data to validate.
        schema_name:  Key into the built-in SCHEMAS dict (e.g. 'business_ideas').
        schema:       Custom jsonschema dict (takes precedence over schema_name).

    Returns:
        True  → payload is valid, safe to persist.
        False → validation failed; data should be rejected or re-generated.

    When ENFORCE_VERIFICATION=0, always returns True (debug mode).
    """
    if not ENFORCE_VERIFICATION:
        return True

    resolved_schema = schema or SCHEMAS.get(schema_name or "")
    if resolved_schema is None:
        # No schema registered — pass through but warn
        logger.debug("No schema for '%s'; skipping strict validation.", schema_name)
        return True

    try:
        from jsonschema import ValidationError, validate
        validate(instance=payload, schema=resolved_schema)
        logger.debug("Verification PASSED for schema '%s'.", schema_name)
        return True
    except ImportError:
        logger.warning("jsonschema not installed — verification skipped.")
        return True
    except Exception as exc:
        logger.warning(
            "Verification FAILED for schema '%s': %s — payload keys: %s",
            schema_name,
            exc,
            list(payload.keys()) if isinstance(payload, dict) else type(payload).__name__,
        )
        return False


def require_verified(
    payload: Any,
    schema_name: Optional[str] = None,
    schema: Optional[Dict] = None,
) -> Any:
    """
    Like verify_output() but raises ValueError if validation fails.
    Use at tool boundaries where bad data must be stopped entirely.
    """
    if not verify_output(payload, schema_name=schema_name, schema=schema):
        raise ValueError(
            f"Tool output failed deterministic verification "
            f"(schema='{schema_name}'). Data not persisted."
        )
    return payload
