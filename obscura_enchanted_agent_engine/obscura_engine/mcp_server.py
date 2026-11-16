"""Model Context Protocol (MCP) Server for the Obscura Enchanted Agent Engine.

Provides JSON-RPC stdio and SSE transport interfaces allowing any AI agent
(Claude Desktop, Cursor, Antigravity, CrewAI, AutoGen) to control the browser
with token-distilled snapshots, diff tracking, and deterministic action execution.
"""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Any, Dict, List, Optional

from .client import AsyncObscuraAgentEngine
from .types import ActionType, BrowserAction, FormFieldEntry


TOOL_DEFINITIONS = [
    {
        "name": "browser_navigate",
        "description": "Navigate to a URL and return a token-distilled semantic markdown snapshot with actionable [@ref:id] tags.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Target web URL (e.g. 'https://news.ycombinator.com')"}
            },
            "required": ["url"]
        }
    },
    {
        "name": "browser_distilled_snapshot",
        "description": "Extract a token-compressed semantic markdown snapshot of the current page with interactive [@ref:ID] tags. Saves 80-90% tokens compared to raw HTML.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "browser_diff_snapshot",
        "description": "Emit ONLY the DOM mutations and state differences since the previous agent turn. Saves up to 95% tokens in multi-step browser interactions.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "browser_act",
        "description": "Execute an atomic user action (click, type, select, hover, scroll) using an unambiguous [@ref:id] tag or CSS selector.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["click", "type", "select", "hover", "scroll", "press_key"],
                    "description": "The action to perform"
                },
                "ref": {"type": "string", "description": "Actionable ref identifier from snapshot (e.g. '3')"},
                "selector": {"type": "string", "description": "Fallback CSS selector if ref is unavailable"},
                "value": {"type": "string", "description": "Text to type or option value to select"},
                "key": {"type": "string", "description": "Keyboard key to press (e.g. 'Enter')"},
                "scroll_delta_y": {"type": "number", "description": "Pixels to scroll vertically"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "browser_fill_form_smart",
        "description": "Batch-fill an entire multi-field form in a single round-trip using a list of ref IDs and values.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "fields": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "ref_or_selector": {"type": "string"},
                            "value": {"type": "string"}
                        },
                        "required": ["ref_or_selector", "value"]
                    },
                    "description": "List of form fields to populate"
                }
            },
            "required": ["fields"]
        }
    },
    {
        "name": "browser_extract_structured_data",
        "description": "Extract repetitive DOM cards/rows into a structured list of JSON objects matching a field schema.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "container_selector": {"type": "string", "description": "CSS selector matching each repeating item (e.g. '.product-card', 'tr')"},
                "fields": {
                    "type": "object",
                    "description": "Mapping of field name to inner CSS selector (e.g. {'title': 'h3', 'price': '.price'})"
                }
            },
            "required": ["container_selector", "fields"]
        }
    },
    {
        "name": "browser_session_stats",
        "description": "Retrieve real-time memory usage, active tabs, and cumulative token savings metrics.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    }
]


class ObscuraMcpServer:
    """JSON-RPC Model Context Protocol server."""

    def __init__(self):
        self.engine = AsyncObscuraAgentEngine()

    async def handle_request(self, req: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatches JSON-RPC request to appropriate handler."""
        req_id = req.get("id")
        method = req.get("method", "")
        params = req.get("params", {})

        if method == "initialize":
            await self.engine.initialize()
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {
                        "name": "obscura-enchanted-agent-engine",
                        "version": "1.0.0"
                    },
                    "capabilities": {
                        "tools": {}
                    }
                }
            }

        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "tools": TOOL_DEFINITIONS
                }
            }

        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            result_content = await self._execute_tool(tool_name, arguments)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": result_content
                        }
                    ]
                }
            }

        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {
                "code": -32601,
                "message": f"Method '{method}' not found"
            }
        }

    async def _execute_tool(self, name: str, args: Dict[str, Any]) -> str:
        """Executes a specific browser tool."""
        try:
            if name == "browser_navigate":
                url = args["url"]
                snapshot = await self.engine.navigate(url)
                stats = (
                    f"*(Tokens: raw ~{snapshot.estimated_raw_tokens} ➔ "
                    f"distilled ~{snapshot.estimated_distilled_tokens}, "
                    f"Saved: {snapshot.token_savings_pct}%)*\n\n"
                )
                return stats + snapshot.markdown

            elif name == "browser_distilled_snapshot":
                snapshot = self.engine.snapshot()
                stats = (
                    f"*(Tokens: raw ~{snapshot.estimated_raw_tokens} ➔ "
                    f"distilled ~{snapshot.estimated_distilled_tokens}, "
                    f"Saved: {snapshot.token_savings_pct}%)*\n\n"
                )
                return stats + snapshot.markdown

            elif name == "browser_diff_snapshot":
                diff = self.engine.diff_snapshot()
                return f"**Summary:** {diff.summary}\n\n{diff.diff_markdown}"

            elif name == "browser_act":
                act = BrowserAction(
                    action=ActionType(args["action"]),
                    ref=args.get("ref"),
                    selector=args.get("selector"),
                    value=args.get("value"),
                    key=args.get("key"),
                    scroll_delta_y=args.get("scroll_delta_y")
                )
                res = await self.engine.act(act)
                return json.dumps(res, indent=2)

            elif name == "browser_fill_form_smart":
                entries = [FormFieldEntry(**f) for f in args.get("fields", [])]
                res = await self.engine.fill_form(entries)
                return json.dumps(res, indent=2)

            elif name == "browser_extract_structured_data":
                container = args["container_selector"]
                fields = args["fields"]
                data = self.engine.extract_structured_data(container, fields)
                return json.dumps(data, indent=2)

            elif name == "browser_session_stats":
                metrics = self.engine.session_pool.get_metrics()
                return json.dumps(metrics.model_dump(), indent=2)

            return f"Unknown tool: {name}"

        except Exception as e:
            return f"Error executing tool '{name}': {str(e)}"

    async def run_stdio(self) -> None:
        """Runs the MCP server over standard input/output."""
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        loop = asyncio.get_event_loop()
        await loop.connect_read_pipe(lambda: protocol, sys.stdin)

        while True:
            line = await reader.readline()
            if not line:
                break
            line_str = line.decode("utf-8").strip()
            if not line_str:
                continue

            try:
                req = json.loads(line_str)
                resp = await self.handle_request(req)
                resp_json = json.dumps(resp)
                sys.stdout.write(resp_json + "\n")
                sys.stdout.flush()
            except Exception as e:
                err_resp = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": f"Parse error: {str(e)}"}
                }
                sys.stdout.write(json.dumps(err_resp) + "\n")
                sys.stdout.flush()
