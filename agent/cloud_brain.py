"""Alexa+ brain hosted on Amazon Bedrock AgentCore Runtime (see cloud/ChronoGridAlexa).

Same contract as AlexaBrain.ask, but the Strands agent runs in AWS, keeps household memory
in AgentCore Memory, and calls this server's MCP endpoint back through the public tunnel.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from datetime import datetime
from typing import Any, Callable

import boto3


log = logging.getLogger("chronogrid.cloud_brain")


class CloudBrain:
    def __init__(self, runtime_arn: str, region: str, public_url: Callable[[], str | None], mcp_token: str | None,
                 model_id: str, keep_warm_seconds: float = 240):
        self.runtime_arn = runtime_arn
        self.public_url = public_url
        self.mcp_token = mcp_token
        self.model_id = model_id
        self._client = boto3.client("bedrock-agentcore", region_name=region)
        self._lock = threading.Lock()
        self._stop = threading.Event()
        if keep_warm_seconds > 0:
            # an idle runtime session is recycled, and a fresh microVM can take ~45 s to answer
            threading.Thread(target=self._keep_warm, args=(keep_warm_seconds,), daemon=True).start()

    @staticmethod
    def _session_id() -> str:
        # AgentCore session ids must be at least 33 characters; one session per household per day
        return "chronogrid-household-" + datetime.now().strftime("%Y%m%d") + "-alexa-plus"

    def _invoke(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            resp = self._client.invoke_agent_runtime(
                agentRuntimeArn=self.runtime_arn,
                runtimeSessionId=self._session_id(),
                payload=json.dumps(payload).encode(),
            )
            return json.loads(resp["response"].read())

    def _keep_warm(self, interval: float) -> None:
        while not self._stop.is_set():
            t0 = time.perf_counter()
            try:
                self._invoke({"warmup": True})
                log.info("AgentCore runtime warm (%.1f s)", time.perf_counter() - t0)
            except Exception as exc:
                log.warning("AgentCore warm-up failed: %s", exc)
            self._stop.wait(interval)

    def ask(self, utterance: str) -> dict[str, Any]:
        base = self.public_url()
        if not base:
            raise RuntimeError("no public URL for the MCP server; start scripts/tunnel.ps1")
        payload = {
            "prompt": utterance,
            "mcp_url": f"{base}/mcp",
            "mcp_token": self.mcp_token,
            "now": datetime.now().strftime("%A %I:%M %p"),
            "household": "household",
        }
        t0 = time.perf_counter()
        body = self._invoke(payload)
        latency_ms = int((time.perf_counter() - t0) * 1000)
        if body.get("error"):
            raise RuntimeError(body["error"])
        return {
            "reply": body.get("reply", ""),
            "tools": body.get("tools", []),
            "latency_ms": latency_ms,
            "model": f"AgentCore Runtime · {self.model_id}",
        }

    def close(self) -> None:
        self._stop.set()
