"""Sends all cropped cards to Gemini in a single request."""

import asyncio
import json
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

from models.card_model import CardIdentity


def _identify_sync(crops: list[bytes]) -> list[CardIdentity]:
    load_dotenv()
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    # One image part per card, followed by ONE prompt that applies to all of them.
    # This is the batching idea: same instructions, many items, a single request.
    parts = [types.Part.from_bytes(data=c, mime_type="image/jpeg") for c in crops]
    prompt = (
        f"These are {len(crops)} separate Pokemon card images, in order. "
        "Return a JSON array with exactly one object per image, in the same order, "
        "with: name (translated to English), card_number, and language spelled out."
    )

    response = client.models.generate_content(
        model="gemini-3.1-flash-lite-preview",
        contents=[*parts, prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",  # force JSON output
            response_schema=list[CardIdentity],     # ...shaped like our model
            temperature=0.0,                        # deterministic answers
        ),
    )

    cards = [CardIdentity(**item) for item in json.loads(response.text)][: len(crops)]
    # If Gemini returned fewer items than crops, pad so boxes and results still line up
    while len(cards) < len(crops):
        cards.append(CardIdentity(name="Unknown"))
    return cards


async def identify_batch(crops: list[bytes]) -> list[CardIdentity]:
    # The Gemini SDK call is blocking, so run it in a thread to keep the server responsive
    return await asyncio.to_thread(_identify_sync, crops)