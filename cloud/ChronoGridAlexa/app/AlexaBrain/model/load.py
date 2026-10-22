import os

from strands.models.bedrock import BedrockModel


def load_model() -> BedrockModel:
    """Amazon Nova 2 Lite by default: fast enough for voice, good at nested tool schemas."""
    return BedrockModel(
        model_id=os.getenv("CHRONOGRID_MODEL_ID", "us.amazon.nova-2-lite-v1:0"),
        temperature=0.2,
        max_tokens=600,
    )
