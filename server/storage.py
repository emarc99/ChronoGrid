"""Clip storage: local disk always, mirrored to S3 (served via presigned URLs) when configured."""

from __future__ import annotations

import logging
import re
import threading
from pathlib import Path

log = logging.getLogger("chronogrid.storage")

_SAFE = re.compile(r"[^A-Za-z0-9._-]")


class ClipStore:
    def __init__(self, clips_dir: Path, base_url: str, bucket: str | None = None, region: str = "us-east-1"):
        self.clips_dir = clips_dir
        self.clips_dir.mkdir(parents=True, exist_ok=True)
        self.base_url = base_url.rstrip("/")
        self.bucket = bucket
        self._s3 = None
        self._local_only: set[str] = set()
        if bucket:
            import boto3

            self._s3 = boto3.client("s3", region_name=region)

    def save(self, name: str, data: bytes, content_type: str = "video/mp4") -> str:
        key = _SAFE.sub("_", Path(name).name)
        (self.clips_dir / key).write_bytes(data)
        if self._s3:
            # the edge box is busy running detection; never make it wait on S3
            self._local_only.add(key)
            threading.Thread(target=self._mirror, args=(key, data, content_type), daemon=True).start()
        return key

    def _mirror(self, key: str, data: bytes, content_type: str) -> None:
        try:
            self._s3.put_object(Bucket=self.bucket, Key=f"clips/{key}", Body=data, ContentType=content_type)
            self._local_only.discard(key)
        except Exception:
            log.exception("S3 upload failed for %s; serving locally", key)

    def url(self, key: str | None, expires: int = 3600) -> str | None:
        if not key:
            return None
        if key.startswith("http"):
            return key
        if self._s3 and key not in self._local_only:
            return self._s3.generate_presigned_url(
                "get_object", Params={"Bucket": self.bucket, "Key": f"clips/{key}"}, ExpiresIn=expires
            )
        return f"{self.base_url}/clips/{key}"
