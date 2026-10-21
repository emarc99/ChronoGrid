"""ChronoGrid HTTP entry point: MCP (/mcp), REST (/api), screen push (/ws), clips and the web UI."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from typing import Any

from fastapi import FastAPI, File, HTTPException, Query, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from .config import ROOT, load_settings
from .hub import Hub
from .ledger import EVENT_KINDS, Ledger
from .linter import Linter
from .mcp_server import build_mcp
from .storage import ClipStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("chronogrid.api")

settings = load_settings()
ledger = Ledger(settings.db_path)
hub = Hub()
clips = ClipStore(settings.clips_dir, settings.base_url, settings.s3_bucket, settings.region)
linter = Linter(ledger, hub, settings.lint_interval)
csp = [settings.base_url] + ([f"https://{settings.s3_bucket}.s3.amazonaws.com"] if settings.s3_bucket else [])
mcp = build_mcp(ledger, hub, clips, csp_domains=csp)
mcp_app = mcp.streamable_http_app(streamable_http_path="/mcp", host=settings.host)

_brain = None
_voice = None


def brain():
    global _brain
    if _brain is None:
        from agent.alexa_agent import AlexaBrain

        _brain = AlexaBrain(settings.mcp_url, settings.model_id, settings.region, settings.s3_bucket)
    return _brain


def voice():
    global _voice
    if _voice is None:
        from agent.voice import Voice

        _voice = Voice(settings.region, settings.polly_voice)
    return _voice


@contextlib.asynccontextmanager
async def lifespan(_: FastAPI):
    hub.bind(asyncio.get_running_loop())
    lint_task = asyncio.create_task(linter.run())
    async with mcp.session_manager.run():
        log.info("ChronoGrid up: MCP at %s, UI at %s", settings.mcp_url, settings.base_url)
        yield
    lint_task.cancel()
    if _brain is not None:
        await run_in_threadpool(_brain.close)


app = FastAPI(title="ChronoGrid", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.router.routes.extend(mcp_app.routes)


# ---- edge ingest -----------------------------------------------------------


class EventIn(BaseModel):
    kind: str
    label: str | None = None
    zone_id: str | None = None
    bbox: list[float] | None = Field(None, description="Normalized [x1, y1, x2, y2]")
    confidence: float | None = None
    clip: str | None = None
    ts: float | None = None
    meta: dict[str, Any] | None = None


@app.post("/api/events")
def ingest_event(event: EventIn) -> dict[str, Any]:
    if event.kind not in EVENT_KINDS:
        raise HTTPException(400, f"kind must be one of {sorted(EVENT_KINDS)}")
    zone_id = event.zone_id
    if zone_id is None and event.bbox:
        x1, y1, x2, y2 = event.bbox
        zone_id = ledger.zone_for_point((x1 + x2) / 2, (y1 + y2) / 2)
    saved = ledger.record_event(
        event.kind, event.label, zone_id, ts=event.ts, bbox=event.bbox, clip=event.clip,
        confidence=event.confidence, meta=event.meta,
    )
    payload = saved.to_dict()
    payload["zone_name"] = ledger.zone_name(saved.zone_id)
    payload["clip_url"] = clips.url(saved.clip)
    if saved.kind != "seen":
        hub.publish({"type": "event", "event": payload})
    return payload


@app.post("/api/clips")
async def upload_clip(file: UploadFile = File(...)) -> dict[str, str]:
    data = await file.read()
    key = await run_in_threadpool(clips.save, file.filename or f"clip-{int(time.time())}.mp4", data,
                                  file.content_type or "video/mp4")
    return {"clip": key, "url": clips.url(key)}


class ApplianceIn(BaseModel):
    label: str
    on: bool
    zone_id: str | None = None


@app.post("/api/appliance")
def set_appliance(body: ApplianceIn) -> dict[str, Any]:
    """Smart-plug style signal (or edge glow detection) for appliances."""
    ledger.record_event("appliance_on" if body.on else "appliance_off", body.label, body.zone_id)
    state = ledger.appliance(body.label)
    hub.publish({"type": "appliance", "appliance": state})
    return state


# ---- screen reads ------------------------------------------------------------


@app.get("/api/state")
def state() -> dict[str, Any]:
    zones = ledger.zones()
    for z in zones:
        z["objects"] = [o["label"] for o in ledger.objects(z["id"])]
        z["presence"] = ledger.presence(z["id"])
        z["last_commit"] = ledger.last_commit(z["id"])
    return {
        "zones": zones,
        "appliances": ledger.appliances(),
        "alerts": [a for a in ledger.alerts() if a["status"] in ("open", "snoozed")],
        "rules": ledger.rules(),
        "recent": [_event_out(e) for e in ledger.events(limit=12, kinds=["placed", "moved", "removed"])],
        "now": time.time(),
    }


@app.get("/api/grid")
def grid(hours: int = Query(12, ge=1, le=48)) -> dict[str, Any]:
    return ledger.activity_grid(hours=hours)


@app.get("/api/events")
def list_events(zone_id: str | None = None, since: float | None = None, until: float | None = None,
                label: str | None = None, limit: int = Query(50, le=500)) -> list[dict[str, Any]]:
    return [_event_out(e) for e in ledger.events(zone_id=zone_id, since=since, until=until, label=label,
                                                 kinds=["placed", "moved", "removed"], limit=limit)]


def _event_out(e) -> dict[str, Any]:
    out = e.to_dict()
    out["zone_name"] = ledger.zone_name(e.zone_id)
    out["clip_url"] = clips.url(e.clip)
    return out


# ---- actions from the screen (D-pad / click) ---------------------------------


@app.post("/api/rules/{rule_id}/{action}")
def rule_action(rule_id: int, action: str) -> dict[str, Any]:
    status = {"approve": "active", "reject": "rejected", "disable": "disabled"}.get(action)
    if status is None:
        raise HTTPException(400, "action must be approve, reject or disable")
    row = ledger.set_rule_status(rule_id, status)
    if row is None:
        raise HTTPException(404, "rule not found")
    hub.publish({"type": "rule_updated", "rule": row})
    return row


@app.post("/api/alerts/{alert_id}/snooze")
def snooze(alert_id: int, minutes: float = 10) -> dict[str, Any]:
    alert = ledger.snooze_alert(alert_id, minutes)
    if alert is None:
        raise HTTPException(404, "alert not found")
    hub.publish({"type": "alert_snoozed", "alert": alert})
    return alert


# ---- simulated Alexa+ voice ----------------------------------------------------


class AskIn(BaseModel):
    text: str = Field(min_length=1, max_length=500)


@app.post("/api/ask")
async def ask(body: AskIn) -> dict[str, Any]:
    hub.publish({"type": "utterance", "text": body.text})
    try:
        result = await run_in_threadpool(brain().ask, body.text)
    except Exception as exc:
        log.exception("agent failed")
        result = {"reply": "Sorry, I couldn't reach ChronoGrid just now.", "tools": [], "error": str(exc)}
    hub.publish({"type": "assistant", "text": body.text, **result})
    return result


@app.get("/api/tts")
async def tts(text: str = Query(min_length=1, max_length=1000)) -> Response:
    audio = await run_in_threadpool(voice().speak, text)
    return Response(audio, media_type="audio/mpeg", headers={"Cache-Control": "max-age=3600"})


@app.websocket("/ws")
async def screen_socket(ws: WebSocket) -> None:
    await ws.accept()
    queue = hub.subscribe()
    try:
        await ws.send_json({"type": "hello", "at": time.time()})
        while True:
            await ws.send_json(await queue.get())
    except WebSocketDisconnect:
        pass
    finally:
        hub.unsubscribe(queue)


app.mount("/clips", StaticFiles(directory=settings.clips_dir), name="clips")
app.mount("/apps", StaticFiles(directory=ROOT / "server" / "apps"), name="apps")
_web = ROOT / "web" / "dist"
if _web.exists():
    app.mount("/", StaticFiles(directory=_web, html=True), name="web")


def main() -> None:
    import uvicorn

    uvicorn.run(app, host=settings.host, port=settings.port, log_level="info")


if __name__ == "__main__":
    main()
