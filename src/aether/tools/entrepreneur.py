"""
AETHER Engineer & Entrepreneur Executive Companion Tools
=========================================================
Equips AETHER with sovereign capabilities for visionary engineers & startup founders:
1. Venture Unit Economics & Runway Modeling
2. Institutional Investor Memos & Pitch Deck Strategy
3. Cap Table, SAFE Notes & Equity Dilution Simulations
4. Full-Stack Technical PRD & Architecture Synthesis
5. Founder Focus, Eisenhower Sprint & Blocker Resolution
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("aether.tools.entrepreneur")


def tool_model_venture_unit_economics(
    cac: float,
    arpu: float,
    gross_margin_pct: float,
    churn_rate_monthly: float,
    monthly_burn: float,
    cash_balance: float,
) -> Dict[str, Any]:
    """
    Model core venture SaaS/AI unit economics, payback periods, and runway.

    Args:
        cac: Customer Acquisition Cost in USD.
        arpu: Average Monthly Revenue Per User/Customer in USD.
        gross_margin_pct: Gross Margin Percentage (e.g. 80.0 for 80%).
        churn_rate_monthly: Monthly Churn Rate Percentage (e.g. 2.5 for 2.5%).
        monthly_burn: Net Monthly Cash Burn in USD.
        cash_balance: Current Cash/Treasury in USD.
    """
    margin_multiplier = max(0.01, gross_margin_pct / 100.0)
    churn_multiplier = max(0.001, churn_rate_monthly / 100.0)

    # Customer Lifetime in Months = 1 / Churn Rate
    customer_lifetime_months = 1.0 / churn_multiplier
    # LTV = ARPU * Gross Margin * Customer Lifetime
    ltv = arpu * margin_multiplier * customer_lifetime_months

    # CAC Payback Period (Months) = CAC / (ARPU * Gross Margin)
    monthly_gross_profit_per_customer = max(0.01, arpu * margin_multiplier)
    cac_payback_months = cac / monthly_gross_profit_per_customer

    # LTV to CAC Ratio
    ltv_cac_ratio = ltv / max(0.01, cac)

    # Runway in Months
    runway_months = cash_balance / max(1.0, monthly_burn) if monthly_burn > 0 else 999.0

    # Qualitative Assessment
    health = "ELITE"
    insights = []
    if ltv_cac_ratio >= 3.0:
        insights.append("✓ Strong LTV:CAC (> 3.0x), highly attractive for Venture Capital.")
    else:
        health = "WARNING"
        insights.append("⚠ LTV:CAC is below venture threshold (< 3.0x). Optimize acquisition channels or raise pricing.")

    if cac_payback_months <= 12.0:
        insights.append(f"✓ Fast CAC payback ({cac_payback_months:.1f} months <= 12 months). Efficient capital recycling.")
    else:
        insights.append(f"⚠ CAC payback period is long ({cac_payback_months:.1f} months). May cause working capital strain.")

    if runway_months < 6.0:
        health = "CRITICAL"
        insights.append(f"🚨 Runway is dangerously low ({runway_months:.1f} months). Immediate fundraising or burn cut required.")
    elif runway_months < 12.0:
        insights.append(f"ℹ Runway is {runway_months:.1f} months. Initiate fundraising conversations now.")
    else:
        insights.append(f"✓ Healthy runway ({runway_months:.1f} months).")

    return {
        "status": "success",
        "health_rating": health,
        "metrics": {
            "ltv_usd": round(ltv, 2),
            "cac_usd": round(cac, 2),
            "ltv_to_cac_ratio": round(ltv_cac_ratio, 2),
            "cac_payback_months": round(cac_payback_months, 1),
            "customer_lifetime_months": round(customer_lifetime_months, 1),
            "runway_months": round(runway_months, 1),
            "monthly_burn_usd": round(monthly_burn, 2),
            "cash_balance_usd": round(cash_balance, 2),
        },
        "strategic_insights": insights,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def tool_simulate_cap_table_and_dilution(
    founders: Dict[str, float],
    existing_shares: int,
    new_investment_usd: float,
    post_money_valuation_usd: float,
    unallocated_option_pool_pct: float = 10.0,
) -> Dict[str, Any]:
    """
    Simulate cap table equity ownership, post-money SAFE conversion, and option pool dilution.

    Args:
        founders: Mapping of founder names to current equity share percentages (e.g. {"Founder_A": 60.0, "Founder_B": 40.0}).
        existing_shares: Total currently issued shares before the round.
        new_investment_usd: Investment capital raised in USD.
        post_money_valuation_usd: Post-money valuation cap in USD.
        unallocated_option_pool_pct: Desired unallocated employee stock option pool percentage post-round.
    """
    investor_equity_pct = min(99.0, (new_investment_usd / max(1.0, post_money_valuation_usd)) * 100.0)
    pool_pct = max(0.0, min(50.0, unallocated_option_pool_pct))

    # Remaining equity for existing shareholders (Founders + existing team)
    remaining_founder_pool_pct = max(1.0, 100.0 - investor_equity_pct - pool_pct)

    founder_breakdown = {}
    for name, prev_pct in founders.items():
        new_ownership_pct = round((prev_pct / 100.0) * remaining_founder_pool_pct, 2)
        founder_breakdown[name] = {
            "previous_ownership_pct": prev_pct,
            "post_round_ownership_pct": new_ownership_pct,
            "dilution_pct": round(prev_pct - new_ownership_pct, 2),
        }

    return {
        "status": "success",
        "round_summary": {
            "new_investment_usd": new_investment_usd,
            "post_money_valuation_usd": post_money_valuation_usd,
            "implied_pre_money_valuation_usd": post_money_valuation_usd - new_investment_usd,
            "investor_equity_pct": round(investor_equity_pct, 2),
            "option_pool_pct": round(pool_pct, 2),
            "total_founder_retention_pct": round(remaining_founder_pool_pct, 2),
        },
        "founder_equity_breakdown": founder_breakdown,
        "recommendation": (
            "Ensure the option pool expansion is modeled pre-money or post-money in the term sheet, "
            "as pre-money option pool expansion dilutes founders solely before investor entry."
        ),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def tool_synthesize_technical_prd(
    product_title: str,
    target_users: str,
    core_value_prop: str,
    key_features: List[str],
    tech_stack: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Synthesize a production-grade Product Requirements Document (PRD) for technical founders.
    """
    stack = tech_stack or ["Python 3.12", "FastAPI", "SQLite WAL / PostgreSQL", "React / Tailwind", "Qualcomm NPU / DirectML"]
    
    prd_markdown = f"""# Product Requirements Document (PRD): {product_title}

## 1. Executive Summary & Value Proposition
- **Target Audience**: {target_users}
- **Core Value Proposition**: {core_value_prop}
- **Status**: Ready for Engineering Architecture

## 2. Technical Stack & Infrastructure
{chr(10).join(f"- {s}" for s in stack)}

## 3. Core Feature Specifications & Acceptance Criteria
"""
    for i, feat in enumerate(key_features, 1):
        prd_markdown += f"""
### 3.{i} Feature: {feat}
- **Description**: High-impact functional capability for {target_users}.
- **Acceptance Criteria**:
  - [ ] Zero-latency execution with AST-validated security bounds.
  - [ ] Full error boundary with deterministic exception logging.
  - [ ] 100% test coverage with automated behavioral verification.
"""

    prd_markdown += """
## 4. Non-Functional Requirements & Security
- **Latency**: P95 API response under 100ms.
- **Security**: Strict input sanitization, zero plain-text secret storage, OWASP Top 10 compliance.
- **Reliability**: Graceful offline degradation with local disk-backed WAL persistence.
"""

    return {
        "status": "success",
        "product_title": product_title,
        "prd_content": prd_markdown,
        "total_features": len(key_features),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def tool_synthesize_investor_memo_and_pitch(
    company_name: str,
    problem: str,
    solution: str,
    target_market: str,
    business_model: str,
    traction: str,
    ask_amount_usd: float,
) -> Dict[str, Any]:
    """
    Synthesize an institutional-grade investment thesis and pitch narrative.
    """
    memo_text = f"""# Investment Thesis & Executive Memo: {company_name}

## 1. The Core Insight & Opportunity
- **The Problem**: {problem}
- **The Solution**: {solution}
- **Target Market**: {target_market}

## 2. Business Model & Defensibility Moats
- **Monetization**: {business_model}
- **Moat Strategy**: Proprietary AI models, on-device sovereign computation, high switching costs, network effects.

## 3. Traction & Milestones
- **Current Progress**: {traction}

## 4. The Capital Ask & Use of Funds
- **Raising**: ${ask_amount_usd:,.2f}
- **Allocation**:
  - 60% Core Engineering & Deep Tech R&D
  - 25% Go-To-Market & Enterprise Distribution
  - 15% Operational Runway & Reserve
"""

    return {
        "status": "success",
        "company_name": company_name,
        "investment_memo": memo_text,
        "ask_usd": ask_amount_usd,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def tool_orchestrate_executive_sprint(
    goals: List[str],
    blockers: Optional[List[str]] = None,
    available_hours_per_week: float = 50.0,
) -> Dict[str, Any]:
    """
    Orchestrate an Eisenhower high-leverage sprint for technical founders.
    """
    blocker_list = blockers or []
    
    prioritized_sprint = []
    for i, g in enumerate(goals):
        priority = "P0 (Critical Path)" if i == 0 else ("P1 (High Leverage)" if i < 3 else "P2 (Strategic)")
        prioritized_sprint.append({
            "goal": g,
            "priority": priority,
            "allocated_hours": round(available_hours_per_week / max(1, len(goals)), 1),
        })

    return {
        "status": "success",
        "sprint_capacity_hours": available_hours_per_week,
        "prioritized_goals": prioritized_sprint,
        "blocker_mitigation_plan": [
            f"⚡ Direct resolution for blocker: '{b}' (automate, delegate, or refactor)"
            for b in blocker_list
        ],
        "focus_recommendation": "Protect 4-hour morning deep work blocks with zero notifications for P0 engineering.",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
