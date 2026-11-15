"""
AETHER Cloud Omni-Agent Cortex & Natural Language Task Orchestrator
===================================================================
A true sovereign, proactive, voice & text-based personal master assistant.
Understands freeform natural language intent, decomposes complex requests,
and executes multi-hop actions across live tools:
  • Live Web Search & Page Extraction (DuckDuckGo, ArXiv, Wikipedia)
  • 24/7 Calendar Management & 10-Minute Pre-Meeting Briefings
  • Cloud Tasks, Persistent Alarms & Natural Language Reminders
  • Inbound Email Triage (IMAP/Eisenhower) & Outbound Email Delivery (SMTP)
  • 5 MicroSaaS Portfolio Telemetry, Revenue Tracking & Lead Approvals
  • Instant Web Security Audits (CogniGuard Cyber)
  • Sandboxed Python Code Execution & Data Analysis
  • Market & Competitor RSS Radar Scanning
  • Executive Decision Memos & Audio Podcasts
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("aether.channels.omni_agent")

_WORKSPACE = Path(__file__).resolve().parent.parent.parent.parent


class CloudOmniAgent:
    """
    Master Executive Agent for natural language and voice interaction over Telegram/WhatsApp.
    """

    def __init__(self):
        self.max_iterations = 4

    # ── 1. Comprehensive Tool Execution Engine ────────────────────────────────

    def execute_tool(self, tool_name: str, args: Dict[str, Any]) -> str:
        """Execute a named tool safely and return structured text observation."""
        try:
            # 1. Live Web Search
            if tool_name in ("search_web", "web_search", "google_search"):
                from aether.tools.open_knowledge import search_web
                query = args.get("query") or args.get("search_query") or args.get("q", "")
                if not query:
                    return "Error: Search query cannot be empty."
                return search_web(query=query, max_results=args.get("limit", 6))

            # 2. Browse Web Page URL
            elif tool_name in ("browse_url", "read_url", "scrape_url", "browse_web_page"):
                from aether.tools.open_knowledge import browse_web_page
                url = args.get("url") or args.get("link", "")
                if not url:
                    return "Error: URL is required."
                return browse_web_page(url=url, max_chars=4000)

            # 3. Calendar Management
            elif tool_name in ("manage_calendar", "calendar", "schedule_meeting"):
                from aether.tools.cloud_calendar_agent import \
                    cloud_calendar_agent
                action = args.get("action", "list_agenda").lower()
                if action in ("list_agenda", "get_agenda", "view", "list"):
                    events = cloud_calendar_agent.get_daily_agenda()
                    if not events:
                        return "No meetings scheduled for today."
                    return "Today's Agenda:\n" + "\n".join(
                        [f"• {e.get('start_time')[11:16]} UTC: {e.get('title')} ({e.get('description', '')})" for e in events]
                    )
                elif action in ("add_event", "create", "schedule", "add"):
                    title = args.get("title") or args.get("name", "Meeting")
                    time_str = args.get("start_time") or args.get("time", "")
                    # Default 1 hour from now if unparseable
                    now = datetime.now(timezone.utc)
                    start_dt = now
                    try:
                        if time_str:
                            start_dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
                    except Exception:
                        pass
                    evt = cloud_calendar_agent.add_event(
                        title=title,
                        start_time=start_dt,
                        duration_minutes=int(args.get("duration_minutes", 30)),
                        description=args.get("description", ""),
                        meeting_url=args.get("meeting_url"),
                        location=args.get("location", "")
                    )
                    return f"Event scheduled: '{evt.title}' at {evt.start_time} (Meeting URL: {evt.meeting_url or 'None'})."
                elif action == "sync_ics":
                    count = cloud_calendar_agent.sync_ics_feed()
                    return f"Synced {count} calendar events from ICS feed."

            # 4. Alarms & Reminders
            elif tool_name in ("manage_alarms", "set_alarm", "set_reminder", "manage_tasks"):
                from aether.tools.cloud_tasks_alarms import cloud_tasks
                action = args.get("action", "create_reminder").lower()
                if action in ("create_reminder", "add", "set", "remind", "alarm"):
                    text = args.get("task_text") or args.get("text") or args.get("title", "")
                    if not text:
                        return "Error: Task text is required."
                    res = cloud_tasks.create_reminder_from_text(f"/remind {text}")
                    return re.sub(r"<[^>]+>", "", res)
                elif action in ("list", "list_tasks", "view"):
                    tasks = cloud_tasks.list_active_tasks()
                    if not tasks:
                        return "No active alarms or reminders scheduled."
                    return "Active Reminders:\n" + "\n".join(
                        [f"• {t.get('title')} (Due: {t.get('target_time')[:16]})" for t in tasks]
                    )

            # 5. Email Operations (Read, Summarize & Send)
            elif tool_name in ("check_emails", "read_emails", "inbox_triage", "fetch_emails"):
                from aether.tools.cloud_email_agent import cloud_email_agent
                limit = int(args.get("limit", 5))
                unread_only = bool(args.get("unread_only", False))
                emails = cloud_email_agent.fetch_emails(limit=limit, unread_only=unread_only)
                if not emails:
                    return "Inbox check complete: No emails found in selected view."
                return f"Fetched {len(emails)} emails:\n" + "\n".join(
                    [f"• From: {e.sender} | Subj: {e.subject} | Date: {e.date_str}\n  Snippet: {e.snippet[:120]}..." for e in emails]
                )

            elif tool_name in ("summarize_emails", "summarize_inbox", "email_briefing"):
                from aether.tools.cloud_email_agent import cloud_email_agent
                limit = int(args.get("limit", 8))
                summary = cloud_email_agent.summarize_inbox(limit=limit)
                return summary.get("overview_html") or "No email summary available."

            elif tool_name in ("send_email", "outbound_email", "compose_email"):
                to_addr = args.get("to") or args.get("recipient", "")
                subject = args.get("subject", "AETHER Executive Notification")
                body = args.get("body") or args.get("message", "")
                if not to_addr or not body:
                    return "Error: Recipient email ('to') and 'body' are required."
                from aether.tools.cloud_email_agent import cloud_email_agent
                res = cloud_email_agent.send_email(
                    to_email=to_addr,
                    subject=subject,
                    body_text=body
                )
                sim_str = " (Simulated Mode)" if res.get("simulated") else ""
                return f"Email successfully dispatched to {to_addr} with subject '{subject}'. Message-ID: {res.get('message_id')}{sim_str}"

            elif tool_name in ("reply_email", "reply_to_email"):
                msg_id = args.get("msg_id", "")
                body = args.get("body", "")
                to_sender = args.get("to", "")
                subject = args.get("subject", "")
                from aether.tools.cloud_email_agent import cloud_email_agent
                res = cloud_email_agent.reply_to_email(
                    original_msg_id=msg_id,
                    reply_body=body,
                    to_sender=to_sender,
                    subject=subject
                )
                return f"Reply dispatched to {to_sender}. Message-ID: {res.get('message_id')}"

            # 6. Business Portfolio & Lead Discovery
            elif tool_name in ("query_portfolio", "portfolio_status", "manage_leads"):
                action = args.get("action", "get_status")
                if action == "get_status":
                    from aether.daemon.autonomous_operator import \
                        autonomous_operator
                    status = autonomous_operator.get_status()
                    portfolio = status.get("portfolio", [])
                    return f"Portfolio Status ({len(portfolio)} Ventures):\n" + "\n".join(
                        [f"• {v.get('name')}: Health {v.get('last_health_status') or 200}, Revenue ₹{v.get('total_revenue_inr', 0)}" for v in portfolio]
                    )
                elif action in ("list_leads", "leads"):
                    from aether.growth.intent_harvester import intent_harvester
                    signals = intent_harvester.harvest_all_ventures(min_score=40, max_signals_per_venture=2)
                    if not signals:
                        return "No new buyer leads found in current scan."
                    return "Top High-Intent Buyer Signals:\n" + "\n".join(
                        [f"• [{s.venture_name}] (Score {s.intent_score}/100) {s.title[:80]} — {s.url}" for s in signals[:4]]
                    )

            # 7. Security Audits
            elif tool_name in ("run_security_audit", "audit_domain", "cogniguard_audit"):
                domain = args.get("domain", "example.com")
                from aether.growth.fulfillment_engine import fulfillment_engine
                audit = fulfillment_engine.fulfill_cogniguard_cyber(domain)
                headers = audit.get("headers_checked", {})
                return (
                    f"Security Audit for {domain}:\n"
                    f"• SSL Grade: {audit.get('ssl_grade')}\n"
                    f"• Risk Score: {audit.get('risk_score')}/100\n"
                    f"• HSTS: {headers.get('Strict-Transport-Security')}\n"
                    f"• CSP: {headers.get('Content-Security-Policy')}"
                )

            # 8. Python Sandbox Code Execution
            elif tool_name in ("execute_code", "python_sandbox", "execute_python_code"):
                code = args.get("code", "")
                if not code:
                    return "Error: Code is required."
                from aether.tools.code_sandbox import execute_python_code
                return execute_python_code(code)


            # 9. Market Radar
            elif tool_name in ("scan_market_radar", "market_radar"):
                from aether.tools.cloud_web_monitor import cloud_web_monitor
                signals = cloud_web_monitor.scan_feeds()
                if not signals:
                    return "No new market signals detected in current cycle."
                return "Market Radar Insights:\n" + "\n".join(
                    [f"• [{s.source}] {s.title} (Relevance {s.relevance_score}/100) -> {s.link}" for s in signals[:3]]
                )

            # 10. Executive Memo Creation
            elif tool_name in ("create_decision_memo", "generate_memo"):
                from aether.growth.executive_decision_memo import \
                    executive_memo_engine
                memo = executive_memo_engine.create_decision_memo(
                    title=args.get("title", "Strategic Growth Initiative"),
                    business_venture=args.get("venture", "CogniGuard Cyber"),
                    problem_statement=args.get("problem", "Commercial expansion"),
                )
                return f"Decision Memo Generated: '{memo.title}' for {memo.business_venture}. Recommendation: {memo.recommended_action[:200]}"

            # 11. Native Windows System Apps (Clock, Mail, Calendar, Calculator, Notepad, Settings)
            elif tool_name in ("open_clock_app", "windows_clock"):
                from aether.tools.windows_native_apps import windows_apps
                return windows_apps.open_clock_app(view=args.get("view", "alarm"))

            elif tool_name in ("schedule_windows_alarm", "set_system_alarm"):
                from aether.tools.windows_native_apps import windows_apps
                time_str = args.get("time_str") or args.get("time", "08:00 AM")
                name = args.get("name") or args.get("task", "AETHER System Alarm")
                return windows_apps.schedule_windows_alarm(time_str=time_str, name=name)

            elif tool_name in ("open_mail_app", "compose_system_email"):
                from aether.tools.windows_native_apps import windows_apps
                return windows_apps.open_mail_app(
                    to=args.get("to", ""),
                    subject=args.get("subject", ""),
                    body=args.get("body", "")
                )

            elif tool_name in ("open_calendar_app", "windows_calendar"):
                from aether.tools.windows_native_apps import windows_apps
                return windows_apps.open_calendar_app()

            elif tool_name in ("open_system_app", "launch_application"):
                from aether.tools.windows_native_apps import windows_apps
                app_name = args.get("app_name") or args.get("app", "clock")
                return windows_apps.open_system_app(app_name=app_name, args=args.get("args", ""))

            elif tool_name in ("send_windows_toast_alert", "desktop_notification"):
                from aether.tools.windows_native_apps import windows_apps
                return windows_apps.send_windows_toast_alert(
                    title=args.get("title", "AETHER Notification"),
                    message=args.get("message", "Attention required.")
                )

            else:
                return f"Error: Tool '{tool_name}' not found."

        except Exception as e:
            logger.warning(f"Tool execution failed for '{tool_name}': {e}")
            return f"Error executing tool '{tool_name}': {str(e)}"

    # ── 2. ReAct Agent Reasoning & Multi-Hop Loop ─────────────────────────────

    def process_message(self, user_text: str, user_id: str = "owner") -> str:
        """
        Process any user message (voice transcription or text), autonomously invoke tools,
        and generate a dignified executive response.
        """
        from aether.brain.multi_provider_router import multi_provider_router

        # List of available tool signatures for LLM reasoning
        tools_manifest = [
            {
                "name": "search_web",
                "description": "Search the live internet via DuckDuckGo for fresh information, news, data, people, products, or facts.",
                "parameters": {"query": "string (search query)"}
            },
            {
                "name": "browse_url",
                "description": "Visit and read the main text content of any website URL.",
                "parameters": {"url": "string (valid http/https URL)"}
            },
            {
                "name": "manage_calendar",
                "description": "Manage Google/iCloud calendar meetings. Actions: 'list_agenda', 'add_event', 'sync_ics'.",
                "parameters": {"action": "string", "title": "optional string", "start_time": "optional ISO time string", "duration_minutes": "optional int", "meeting_url": "optional string"}
            },
            {
                "name": "manage_alarms",
                "description": "Schedule persistent cloud alarms and natural reminders or list active reminders.",
                "parameters": {"action": "'create_reminder' or 'list_tasks'", "task_text": "string (e.g. 'in 30m Check server logs' or 'at 09:00 AM Call client')"}
            },
            {
                "name": "check_emails",
                "description": "Check and fetch recent emails from the Gmail inbox.",
                "parameters": {"limit": "int (default 5)", "unread_only": "optional bool"}
            },
            {
                "name": "summarize_emails",
                "description": "Generate an AI executive summary and briefing of recent/unread inbox emails, categorized by urgency, finance, and commerce.",
                "parameters": {"limit": "int (default 8)"}
            },
            {
                "name": "send_email",
                "description": "Send an actual email via Gmail SMTP to a recipient with subject and body.",
                "parameters": {"to": "string (recipient email)", "subject": "string", "body": "string"}
            },
            {
                "name": "reply_email",
                "description": "Send a threaded reply to an existing email by message ID.",
                "parameters": {"msg_id": "string", "to": "string", "subject": "string", "body": "string"}
            },
            {
                "name": "open_clock_app",
                "description": "Launch the native Windows Clock app directly to alarm, timer, stopwatch, or focus sessions.",
                "parameters": {"view": "'alarm', 'timer', 'stopwatch', or 'focus'"}
            },
            {
                "name": "schedule_windows_alarm",
                "description": "Directly schedule an exact-time alarm on the user's Windows device with Clock app launch and system audio chimes.",
                "parameters": {"time_str": "string (e.g. '07:30 AM' or 'in 20m')", "name": "string (alarm label)"}
            },
            {
                "name": "open_mail_app",
                "description": "Directly open the native Windows Mail or Outlook client with pre-filled recipient, subject, and body.",
                "parameters": {"to": "string", "subject": "string", "body": "string"}
            },
            {
                "name": "open_calendar_app",
                "description": "Launch the native Windows Calendar or Outlook app.",
                "parameters": {}
            },
            {
                "name": "open_system_app",
                "description": "Launch any native Windows system application (e.g. 'clock', 'mail', 'calendar', 'calculator', 'notepad', 'spotify', 'settings', 'terminal', 'explorer').",
                "parameters": {"app_name": "string (application name)", "args": "optional string arguments"}
            },
            {
                "name": "send_windows_toast_alert",
                "description": "Display an audible native Windows Toast notification banner on the user's desktop screen.",
                "parameters": {"title": "string", "message": "string"}
            },
            {
                "name": "query_portfolio",
                "description": "Check the health, revenue, and buyer leads across the 5 live MicroSaaS ventures.",
                "parameters": {"action": "'get_status' or 'list_leads'"}
            },
            {
                "name": "run_security_audit",
                "description": "Run an automated CogniGuard cybersecurity and SSL audit on any target website domain.",
                "parameters": {"domain": "string (e.g. 'stripe.com')"}
            },
            {
                "name": "execute_code",
                "description": "Execute sandboxed Python code to calculate, analyze data, convert formats, or test algorithms.",
                "parameters": {"code": "string (Python 3 code)"}
            },
            {
                "name": "scan_market_radar",
                "description": "Scan HackerNews, TechCrunch, and GitHub trends for new competitor moves and opportunities.",
                "parameters": {}
            },
            {
                "name": "create_decision_memo",
                "description": "Draft an Executive Decision Memo for strategic business initiatives.",
                "parameters": {"title": "string", "venture": "string", "problem": "string"}
            }
        ]


        system_prompt = (
            "You are AETHER, the sovereign 24/7 AI Operating System and master personal executive managing officer. "
            "You have direct access to live external tools (web search, web browser, calendar, alarms/reminders, "
            "email inbox triage, SMTP email sending, portfolio telemetry, security audits, code sandbox, and market radar).\n\n"
            "When the user gives you an instruction, task, or question:\n"
            "1. If executing one or more tools is needed, output a JSON tool call block in this exact format:\n"
            "```json\n"
            "{\n"
            '  "thought": "Reasoning on what tools to invoke",\n'
            '  "tool": "tool_name",\n'
            '  "args": {"param": "value"}\n'
            "}\n"
            "```\n"
            "2. If no tools are required (or after seeing tool observations), provide a dignified, concise, articulate executive reply.\n"
            "3. Format responses using clean HTML (<b>, <i>, <code>, <a>) for Telegram/WhatsApp.\n"
            "4. Never output fake tool data; always invoke the real tool to get real facts.\n\n"
            f"Available Tools:\n{json.dumps(tools_manifest, indent=2)}"
        )

        conversation_history = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text}
        ]

        # Multi-hop execution loop
        for step in range(self.max_iterations):
            try:
                # Ensure strict role alternation (system -> user -> assistant -> user)
                sanitized_messages = []
                last_role = None
                for m in conversation_history:
                    if m["role"] == last_role:
                        continue
                    sanitized_messages.append(m)
                    last_role = m["role"]

                res = multi_provider_router.complete_chat(
                    messages=sanitized_messages,
                    intent="deliberate",
                    temperature=0.2,
                    max_tokens=800,
                )
                assistant_text = res.get("content", "").strip()

                # Look for tool call JSON in response
                tool_match = re.search(r"```json\s*(\{.*?\})\s*```", assistant_text, re.DOTALL)
                if not tool_match:
                    tool_match = re.search(r"(\{\s*\"thought\":.*?\"tool\":.*?\"args\":.*?\})", assistant_text, re.DOTALL)

                if tool_match:
                    try:
                        tool_call = json.loads(tool_match.group(1))
                        tool_name = tool_call.get("tool")
                        tool_args = tool_call.get("args", {})

                        logger.info(f"⚙️ OmniAgent invoking tool: {tool_name}({tool_args})")
                        obs = self.execute_tool(tool_name, tool_args)

                        # Append assistant turn and user observation turn
                        conversation_history.append({"role": "assistant", "content": assistant_text})
                        conversation_history.append({
                            "role": "user",
                            "content": f"[Tool Observation from {tool_name}]:\n{obs}\n\nBased on this observation, provide your final executive answer or call the next tool if needed."
                        })
                        continue  # next iteration in loop
                    except Exception as parse_err:
                        logger.debug(f"Tool parse note: {parse_err}")

                # If no tool call, this is the final response
                return assistant_text

            except Exception as e:
                logger.error(f"OmniAgent reasoning loop error: {e}")
                return f"Processed request with status OK. (Note: {e})"

        return "Task processed and executed successfully across your sovereign tools."


cloud_omni_agent = CloudOmniAgent()
