from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from pathlib import Path
import asyncio
import json
import time
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone

import uvicorn

app = FastAPI(title="Bizixer Land API", version="2.0.0")

BASE_DIR   = Path(__file__).resolve().parent
INDEX_FILE = BASE_DIR / "index.html"
LAW_FILE   = BASE_DIR / "g.txt"

# همان a.json — لینک بعداً عوض می‌شود
CONTENT_URL = "https://raw.githubusercontent.com/null-flame/bizixer_land_site/refs/heads/main/data.json"
CACHE_TTL   = 180  # ثانیه

CONFIG = {
    "channel_id":  "@bizixer_LandBzx",
    "channel_url": "https://rubika.ir/bizixer_LandBzx",
    "join_url":    "https://rubika.ir/joing/+BBIDBECIE0PUMGWNRLTCQEMBNMMACHYH",
    "year":        2025,
    "creator":     "Hamid.vexor",
}

# کش فقط برای محتوای GitHub (بدون IP، بدون ویو، بدون ادمین)
_cache = {"data": None, "ts": 0}

# کامنت‌ها (درون‌حافظه)
_comments: dict = {}
_comment_id = 0


# ------------------------------------------------------------
#  Content fetch with 180s cache
# ------------------------------------------------------------
def _fetch_sync() -> dict:
    req = urllib.request.Request(
        CONTENT_URL,
        headers={
            "User-Agent": "BizixerLand/2.0",
            "Accept": "application/json",
            "Cache-Control": "no-cache",
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


async def fetch_content() -> dict:
    now = time.time()
    if _cache["data"] is not None and (now - _cache["ts"]) < CACHE_TTL:
        return _cache["data"]
    try:
        data = await asyncio.to_thread(_fetch_sync)
        _cache["data"] = data
        _cache["ts"] = now
        return data
    except urllib.error.HTTPError as e:
        if _cache["data"] is not None:
            return _cache["data"]
        raise HTTPException(502, f"GitHub HTTP {e.code}")
    except Exception as e:
        if _cache["data"] is not None:
            return _cache["data"]
        raise HTTPException(502, f"Fetch failed: {e}")


# ------------------------------------------------------------
#  SPA shell
# ------------------------------------------------------------
def _serve_spa() -> FileResponse:
    if not INDEX_FILE.exists():
        raise HTTPException(500, "index.html not found")
    return FileResponse(INDEX_FILE, media_type="text/html")


# ------------------------------------------------------------
#  API
# ------------------------------------------------------------
@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "bizixer-land"}


@app.get("/api/config")
async def get_config():
    return JSONResponse(CONFIG)


@app.get("/api/constitution")
async def get_constitution():
    if not LAW_FILE.exists():
        raise HTTPException(404, "فایل قانون اساسی (g.txt) یافت نشد.")
    try:
        content = LAW_FILE.read_text(encoding="utf-8")
    except Exception as e:
        raise HTTPException(500, f"خطا در خواندن فایل: {e}")
    return JSONResponse({"content": content, "length": len(content)})


@app.get("/api/posts")
async def get_posts():
    data = await fetch_content()
    return JSONResponse(data)


@app.get("/api/posts/{slug}")
async def get_post(slug: str):
    data = await fetch_content()
    for p in data.get("posts", []):
        if p.get("slug") == slug:
            return JSONResponse(p)
    raise HTTPException(404, "Post not found")


@app.get("/api/comments/{slug}")
async def get_comments(slug: str):
    return JSONResponse({"comments": _comments.get(slug, [])})


@app.post("/api/comment")
async def post_comment(payload: dict):
    global _comment_id
    slug      = (payload.get("slug") or "").strip()
    author    = (payload.get("author") or "").strip()
    text      = (payload.get("text") or "").strip()
    parent_id = payload.get("parent_id")

    if not slug or not author or not text:
        raise HTTPException(400, "فیلدهای ناقص")
    if len(author) > 24 or len(text) > 1000:
        raise HTTPException(400, "طول بیش از حد")

    pid = None
    if parent_id is not None:
        try:
            pid = int(parent_id)
            if not any(c["id"] == pid for c in _comments.get(slug, [])):
                pid = None
        except (TypeError, ValueError):
            pid = None

    _comment_id += 1
    c = {
        "id": _comment_id,
        "author": author,
        "text": text,
        "time": datetime.now(timezone.utc).strftime("%H:%M UTC"),
        "parent_id": pid,
    }
    _comments.setdefault(slug, []).append(c)
    return JSONResponse({"ok": True, "comment": c})


# ------------------------------------------------------------
#  Download proxy (media)
# ------------------------------------------------------------
_PRIVATE_PREFIXES = (
    "10.", "127.", "169.254.", "192.168.",
    "172.16.", "172.17.", "172.18.", "172.19.", "172.20.", "172.21.",
    "172.22.", "172.23.", "172.24.", "172.25.", "172.26.", "172.27.",
    "172.28.", "172.29.", "172.30.", "172.31.",
)


@app.get("/download")
async def download_proxy(url: str = "", name: str = ""):
    if not url:
        raise HTTPException(400, "Missing url")
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(400, "Invalid scheme")
    host = (parsed.hostname or "").lower()
    if (not host or host in ("localhost", "0.0.0.0", "::1")
            or host.startswith(_PRIVATE_PREFIXES)):
        raise HTTPException(403, "Forbidden host")

    if not name:
        name = url.split("/")[-1].split("?")[0] or "download"
    safe = "".join(c for c in name if c.isalnum() or c in "._-")[:120] or "download"
    if "." not in safe:
        safe += ".bin"

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "*/*",
        "Referer": f"{parsed.scheme}://{host}/",
    }

    def stream():
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=60) as resp:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        return
                    yield chunk
        except Exception as e:
            print(f"Download stream error: {e}")

    return StreamingResponse(
        stream(),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{safe}"',
            "Cache-Control": "public, max-age=3600",
            "X-Accel-Buffering": "no",
        },
    )


# ------------------------------------------------------------
#  SPA catch-all — همه مسیرها index.html
# ------------------------------------------------------------
@app.get("/{full_path:path}", include_in_schema=False)
async def spa_fallback(full_path: str):
    return _serve_spa()


if __name__ == "__main__":
    print("Bizixer Land v2.0  →  http://0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)