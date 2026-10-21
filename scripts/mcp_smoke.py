"""Raw Streamable HTTP check of the ChronoGrid MCP server, the way Alexa+ (or any MCP host) connects.

    python scripts/mcp_smoke.py [--url http://127.0.0.1:8787/mcp] [--version 2025-11-25]
"""

from __future__ import annotations

import argparse
import json

import httpx

HEADERS = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}


def parse(resp: httpx.Response) -> dict:
    if resp.headers.get("content-type", "").startswith("text/event-stream"):
        for line in resp.text.splitlines():
            if line.startswith("data:"):
                return json.loads(line[5:])
        raise ValueError("no data in SSE response")
    return resp.json()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--url", default="http://127.0.0.1:8787/mcp")
    p.add_argument("--version", default="2025-11-25", help="protocol version the client offers")
    args = p.parse_args()

    with httpx.Client(timeout=30) as http:
        init = http.post(args.url, headers=HEADERS, json={
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {
                "protocolVersion": args.version,
                "capabilities": {"extensions": {"io.modelcontextprotocol/ui": {"mimeTypes": ["text/html;profile=mcp-app"]}}},
                "clientInfo": {"name": "chronogrid-smoke", "version": "1.0"},
            },
        })
        init.raise_for_status()
        result = parse(init)["result"]
        session = init.headers.get("mcp-session-id")
        negotiated = result["protocolVersion"]
        print(f"transport        : Streamable HTTP ({args.url})")
        print(f"server           : {result['serverInfo']['name']} {result['serverInfo'].get('version', '')}")
        print(f"protocol offered : {args.version}")
        print(f"protocol agreed  : {negotiated}")
        print(f"session id       : {session}")
        print(f"capabilities     : {sorted(result['capabilities'])}")

        headers = {**HEADERS, "mcp-protocol-version": negotiated}
        if session:
            headers["mcp-session-id"] = session
        http.post(args.url, headers=headers, json={"jsonrpc": "2.0", "method": "notifications/initialized"})

        tools = parse(http.post(args.url, headers=headers, json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"}))
        print("\ntools:")
        for tool in tools["result"]["tools"]:
            ui = (tool.get("_meta") or {}).get("ui", {}).get("resourceUri")
            print(f"  - {tool['name']:<18} {'[MCP App ' + ui + ']' if ui else ''}")

        call = parse(http.post(args.url, headers=headers, json={
            "jsonrpc": "2.0", "id": 3, "method": "tools/call",
            "params": {"name": "where_is", "arguments": {"object": "multimeter"}},
        }))
        structured = call["result"].get("structuredContent") or {}
        print(f"\nwhere_is('multimeter') -> {structured.get('say')}")
        print(f"  clip: {structured.get('clip_url')}  bbox: {structured.get('bbox')}")


if __name__ == "__main__":
    main()
