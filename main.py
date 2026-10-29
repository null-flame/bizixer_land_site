from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import uvicorn

app = FastAPI(title="Bizixer Land")
templates = Jinja2Templates(directory="templates")

BASE_DIR = Path(__file__).resolve().parent

CONFIG = {
    "channel_id":  "@bizixer_LandBzx",
    "channel_url": "https://rubika.ir/bizixer_LandBzx",
    "join_url":    "https://rubika.ir/joing/+BBIDBECIE0PUMGWNRLTCQEMBNMMACHYH",
    "year":        2025,
}

@app.get("/")
async def serve_index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html", context=CONFIG)

@app.get("/constitution")
async def serve_constitution(request: Request):
    return templates.TemplateResponse(request=request, name="constitution.html", context=CONFIG)

@app.get("/api/constitution")
async def get_constitution():
    file_path = BASE_DIR / "g.txt"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="فایل قانون اساسی (g.txt) یافت نشد.")
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطا در خواندن فایل: {e}")
    return JSONResponse(content={"content": content})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)