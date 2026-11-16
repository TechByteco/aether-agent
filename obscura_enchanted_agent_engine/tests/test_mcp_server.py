import json
from obscura_engine.mcp_server import ObscuraMcpServer


async def test_mcp_initialize():
    server = ObscuraMcpServer()
    req = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {}
    }
    resp = await server.handle_request(req)
    assert resp["id"] == 1
    assert resp["result"]["serverInfo"]["name"] == "obscura-enchanted-agent-engine"


async def test_mcp_tools_list():
    server = ObscuraMcpServer()
    req = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {}
    }
    resp = await server.handle_request(req)
    tool_names = [t["name"] for t in resp["result"]["tools"]]
    assert "browser_navigate" in tool_names
    assert "browser_distilled_snapshot" in tool_names
    assert "browser_diff_snapshot" in tool_names
    assert "browser_act" in tool_names
    assert "browser_fill_form_smart" in tool_names
    assert "browser_session_stats" in tool_names


async def test_mcp_tools_call_stats():
    server = ObscuraMcpServer()
    await server.engine.initialize()
    req = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "browser_session_stats",
            "arguments": {}
        }
    }
    resp = await server.handle_request(req)
    content = resp["result"]["content"][0]["text"]
    data = json.loads(content)
    assert "active_tabs" in data
    assert "memory_usage_mb" in data
