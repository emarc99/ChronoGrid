"""Amazon Polly text-to-speech for the simulated Alexa+ speaker."""

from __future__ import annotations

from functools import lru_cache

import boto3


class Voice:
    def __init__(self, region: str, voice_id: str = "Joanna"):
        self._polly = boto3.client("polly", region_name=region)
        self.voice_id = voice_id

    @lru_cache(maxsize=128)
    def speak(self, text: str) -> bytes:
        for engine in ("generative", "neural"):
            try:
                response = self._polly.synthesize_speech(
                    Text=text[:2900], OutputFormat="mp3", VoiceId=self.voice_id, Engine=engine
                )
                return response["AudioStream"].read()
            except self._polly.exceptions.EngineNotSupportedException:
                continue
            except Exception as exc:
                if "engine" not in str(exc).lower():
                    raise
        raise RuntimeError(f"Polly voice {self.voice_id} supports neither generative nor neural engines")
