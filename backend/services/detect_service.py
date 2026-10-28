"""Step 1 of the pipeline: find every card in a photo using classic OpenCV.

Idea: a trading card is a rectangle with a known shape (63mm x 88mm). So we
find edges, turn them into closed shapes, and keep only the card-shaped ones.
Each one is then flattened into an upright crop for Gemini.
"""

import cv2
import numpy as np

# ---- Tuning knobs ----
CARD_RATIO = 63 / 88      # real card width / height
RATIO_TOLERANCE = 0.12    # how far from that ratio a shape may be and still count
MIN_AREA_FRAC = 0.01      # a card must cover at least 1% of the photo...
MAX_AREA_FRAC = 0.50      # ...and at most 50% (bigger = probably the table)
MIN_FILL = 0.80           # shape must fill 80% of its bounding rectangle (rejects blobs)
MAX_SIDE = 1000           # shrink big photos to this many pixels so detection is fast
OUT_W, OUT_H = 630, 880   # size of each flattened crop sent to Gemini


def _order_points(pts: np.ndarray) -> np.ndarray:
    """Sort 4 corners into top-left, top-right, bottom-right, bottom-left.
    Top-left has the smallest x+y; bottom-right the largest. Top-right has the
    smallest y-x difference; bottom-left the largest."""
    s = pts.sum(axis=1)
    d = np.diff(pts, axis=1).ravel()
    return np.array([pts[np.argmin(s)], pts[np.argmin(d)],
                     pts[np.argmax(s)], pts[np.argmax(d)]], dtype="float32")


def _flatten(img: np.ndarray, pts: np.ndarray) -> bytes:
    """Perspective-warp a (possibly tilted) card into an upright rectangle, return as JPEG."""
    tl, tr, br, bl = _order_points(pts)
    ordered = np.array([tl, tr, br, bl], dtype="float32")

    # If the card was laid sideways, rotate the corner order so the crop is portrait
    if np.linalg.norm(tr - tl) > np.linalg.norm(br - tr):
        ordered = np.roll(ordered, -1, axis=0)

    # Map the 4 corners onto a clean OUT_W x OUT_H rectangle
    dst = np.array([[0, 0], [OUT_W - 1, 0], [OUT_W - 1, OUT_H - 1], [0, OUT_H - 1]],
                   dtype="float32")
    matrix = cv2.getPerspectiveTransform(ordered, dst)
    warped = cv2.warpPerspective(img, matrix, (OUT_W, OUT_H))

    _, buf = cv2.imencode(".jpg", warped, [cv2.IMWRITE_JPEG_QUALITY, 90])
    return buf.tobytes()


def detect_cards(image_bytes: bytes):
    """Returns (width, height, [(box, fit, crop_jpeg), ...]) in reading order."""
    img = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image")
    h, w = img.shape[:2]

    # Work on a smaller copy for speed; we scale results back up at the end
    scale = min(1.0, MAX_SIDE / max(h, w))
    small = cv2.resize(img, None, fx=scale, fy=scale) if scale < 1 else img

    # 1. EDGES: grayscale, blur away noise, then Canny marks sharp brightness changes
    gray = cv2.GaussianBlur(cv2.cvtColor(small, cv2.COLOR_BGR2GRAY), (5, 5), 0)
    edges = cv2.Canny(gray, 50, 150)

    # 2. CLOSE GAPS: thicken the edges so each card outline becomes one connected shape
    edges = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=1)
    edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8), iterations=2)

    # 3. SHAPES: trace the outline of every connected edge region
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    total = small.shape[0] * small.shape[1]
    found = []
    for c in contours:
        # 4. FILTER: keep only shapes that look like a card
        area = cv2.contourArea(c)
        if not (MIN_AREA_FRAC * total <= area <= MAX_AREA_FRAC * total):
            continue  # too small (noise) or too big (the table)

        rect = cv2.minAreaRect(c)  # smallest rotated rectangle around the shape
        (_, _), (rw, rh), _ = rect
        if min(rw, rh) == 0:
            continue
        if abs(min(rw, rh) / max(rw, rh) - CARD_RATIO) > RATIO_TOLERANCE:
            continue  # wrong proportions for a card

        fit = area / (rw * rh)  # 1.0 = perfect rectangle
        if fit < MIN_FILL:
            continue  # blobby shape, not a rectangle

        # Convert corners back to the ORIGINAL photo's coordinates
        pts = cv2.boxPoints(rect) / scale
        x, y, bw, bh = cv2.boundingRect(pts.astype(np.int32))
        box = [float(max(x, 0)), float(max(y, 0)),
               float(min(x + bw, w)), float(min(y + bh, h))]

        found.append((box, float(fit), _flatten(img, pts)))

    # Sort into reading order: group into rows (15% of photo height), then left to right.
    # This makes "card 1, 2, 3..." match what a human would expect.
    row_h = h * 0.15
    found.sort(key=lambda f: (round(((f[0][1] + f[0][3]) / 2) / row_h), f[0][0]))
    return w, h, found