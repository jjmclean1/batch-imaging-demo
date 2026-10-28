"""Response shape for the batch endpoint (mirrored by the types in BatchPanel.tsx)."""

from pydantic import BaseModel

from models.card_model import CardIdentity


class DetectedCard(BaseModel):
    index: int
    box: list[float]  # [x1, y1, x2, y2] in pixels of the original photo
    fit: float        # 0-1, how rectangular the shape is
    card: CardIdentity


class BatchScanResultModel(BaseModel):
    image_width: int
    image_height: int
    detect_ms: float    # OpenCV time
    identify_ms: float  # Gemini time
    cards: list[DetectedCard]