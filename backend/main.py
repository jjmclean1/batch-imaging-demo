from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import batch

app = FastAPI(title="Batch Card Scan Demo")

# The browser talks to us through Vite's proxy, so CORS is mostly a formality here.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


# Everything in api/batch.py is served under /api/batch
app.include_router(batch.router, prefix="/api/batch")