from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from pathlib import Path
import uvicorn

app = FastAPI(
    title="Bizixer Land API",
    version="1.0.0",
    description="REST API + SPA host for Bizixer Land",
)

BASE_DIR = Path(__file__).resolve().parent
INDEX_FILE = BASE_DIR / "index.html"
LAW_FILE = BASE_DIR / "g.txt"

CONFIG = {
    "channel_id":  "@bizixer_LandBzx",
    "channel_url": "https://rubika.ir/bizixer_LandBzx",
    "join_url":    "https://rubika.ir/joing/+BBIDBECIE0PUMGWNRLTCQEMBNMMACHYH",
    "year":        2025,
    "creator":     "Hamid.vexor",
}


# ---------- SPA shell ----------
def _serve_spa() -> FileResponse:
    if not INDEX_FILE.exists():
        raise HTTPException(status_code=500, detail="فایل index.html یافت نشد.")
    return FileResponse(INDEX_FILE, media_type="text/html")


@app.get("/", include_in_schema=False)
async def serve_root():
    return _serve_spa()


@app.get("/constitution", include_in_schema=False)
async def serve_constitution_route():
    return _serve_spa()


# ---------- REST API ----------
@app.get("/api/health", tags=["system"])
async def health():
    return {"status": "ok", "service": "bizixer-land"}


@app.get("/api/config", tags=["config"])
async def get_config():
    return JSONResponse(content=CONFIG)


@app.get("/api/constitution", tags=["constitution"])
async def get_constitution():
    if not LAW_FILE.exists():
        raise HTTPException(status_code=404, detail="فایل قانون اساسی (g.txt) یافت نشد.")
    try:
        content = LAW_FILE.read_text(encoding="utf-8")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطا در خواندن فایل: {e}")
    return JSONResponse(content={"content": content, "length": len(content)})


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)