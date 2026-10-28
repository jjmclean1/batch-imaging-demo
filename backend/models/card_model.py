"""What Gemini tells us about one card."""

from typing import Optional

from pydantic import BaseModel


class CardIdentity(BaseModel):
    name: str
    card_number: Optional[str] = None
    language: Optional[str] = None