from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


@dataclass(frozen=True)
class Settings:
    region: str
    model_id: str
    s3_bucket: str | None
    polly_voice: str
    host: str
    port: int
    db_path: Path
    clips_dir: Path
    lint_interval: float

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    @property
    def mcp_url(self) -> str:
        return f"{self.base_url}/mcp"


def load_settings() -> Settings:
    _load_dotenv(ROOT / ".env")
    db = Path(os.environ.get("CHRONOGRID_DB", "data/chronogrid.db"))
    if not db.is_absolute():
        db = ROOT / db
    return Settings(
        region=os.environ.get("AWS_REGION", "us-east-1"),
        model_id=os.environ.get("CHRONOGRID_MODEL_ID", "us.amazon.nova-2-lite-v1:0"),
        s3_bucket=os.environ.get("CHRONOGRID_S3_BUCKET") or None,
        polly_voice=os.environ.get("CHRONOGRID_POLLY_VOICE", "Joanna"),
        host=os.environ.get("CHRONOGRID_HOST", "127.0.0.1"),
        port=int(os.environ.get("CHRONOGRID_PORT", "8787")),
        db_path=db,
        clips_dir=db.parent / "clips",
        lint_interval=float(os.environ.get("CHRONOGRID_LINT_INTERVAL", "5")),
    )
