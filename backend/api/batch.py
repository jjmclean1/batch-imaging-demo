"""HTTP endpoint: photo in, list of identified cards (with box coordinates) out."""

import time

from fastapi import APIRouter, File, HTTPException, UploadFile

from models.batch_model import BatchScanResultModel, DetectedCard
from services.batch_service import identify_batch
from services.detect_service import detect_cards

router = APIRouter(tags=["Batch"])


@router.post("", response_model=BatchScanResultModel)
async def scan_batch(image: UploadFile = File(...)):
    image_bytes = await image.read()

    # STEP 1: split the photo into individual cards (OpenCV, runs on CPU)
    t0 = time.perf_counter()
    try:
        img_w, img_h, found = detect_cards(image_bytes)
    except ValueError:
        raise HTTPException(status_code=400, detail="Could not read that image.")
    detect_ms = (time.perf_counter() - t0) * 1000

    if not found:
        raise HTTPException(status_code=422, detail="No cards detected. Try a darker background.")

    # STEP 2: send every cropped card to Gemini in ONE request (the "batch")
    t1 = time.perf_counter()
    cards = await identify_batch([crop for _, _, crop in found])
    identify_ms = (time.perf_counter() - t1) * 1000

    # STEP 3: pair each card's box with the identity Gemini returned for it
    return BatchScanResultModel(
        image_width=img_w,
        image_height=img_h,
        detect_ms=round(detect_ms, 1),
        identify_ms=round(identify_ms, 1),
        cards=[
            DetectedCard(index=i, box=[round(v, 1) for v in box], fit=round(fit, 3), card=card)
            for i, ((box, fit, _), card) in enumerate(zip(found, cards))
        ],
    )