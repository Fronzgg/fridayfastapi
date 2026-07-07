import json
import os
import re
from datetime import datetime, timezone
from itertools import zip_longest
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel


APP_VERSION = os.environ.get("FRIDAY_VERSION", "3.1")
ADMIN_TOKEN = os.environ.get("FRIDAY_ADMIN_TOKEN", "")
INSTALLER_URL = os.environ.get("FRIDAY_INSTALLER_URL", "https://fridayfastapi.onrender.com/FridaySetup.exe")
ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
MANIFEST_FILE = DATA_DIR / "manifest.json"
NEWS_FILE = DATA_DIR / "news.json"
INSTALLER_CANDIDATES = [
    ROOT / "FridaySetup.exe",
    ROOT / "friday.exe",
    ROOT / "downloads" / "FridaySetup.exe",
    ROOT / "downloads" / "friday.exe",
    ROOT / "release" / "FridaySetup.exe",
    DATA_DIR / "FridaySetup.exe",
]

app = FastAPI(title="FRIDAY Cloud", version=APP_VERSION)


class JsonBody(BaseModel):
    raw: str


def _read_json(path: Path, fallback):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return fallback


def _write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _version_tuple(value):
    digits = [int(part) for part in re.findall(r"\d+", str(value or ""))]
    return tuple(digits or [0])


def _is_newer(candidate, current):
    left = _version_tuple(candidate)
    right = _version_tuple(current)
    for left_part, right_part in zip_longest(left, right, fillvalue=0):
        if left_part != right_part:
            return left_part > right_part
    return False


def default_manifest():
    return {
        "version": APP_VERSION,
        "latest_version": APP_VERSION,
        "title": "FRIDAY Desktop",
        "summary": "JSON-канал обновлений FRIDAY.",
        "force_update": False,
        "installer_url": INSTALLER_URL,
        "download_name": "FridaySetup.exe",
        "published_at": "",
        "notes": [
            "Новое облачное окно обновлений.",
            "Админка редактирует manifest и news JSON.",
        ],
    }


def default_news():
    return {
        "version": APP_VERSION,
        "items": [
            {
                "version": APP_VERSION,
                "title": "Добро пожаловать в FRIDAY",
                "date": "",
                "summary": "Лента новостей подключена.",
                "items": [
                    "Новый JSON-канал для release notes.",
                    "Пуши и хотфиксы можно обновлять вручную из админки.",
                ],
            }
        ],
    }


def ensure_files():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not MANIFEST_FILE.exists():
        _write_json(MANIFEST_FILE, default_manifest())
    if not NEWS_FILE.exists():
        _write_json(NEWS_FILE, default_news())


def load_manifest():
    return _read_json(MANIFEST_FILE, default_manifest())


def load_news():
    return _read_json(NEWS_FILE, default_news())


def payload():
    manifest = load_manifest()
    news = load_news()
    latest_version = str(manifest.get("latest_version") or manifest.get("version") or APP_VERSION)
    news_version = str(news.get("version") or "")
    return {
        "current_version": APP_VERSION,
        "latest_version": latest_version,
        "update_available": _is_newer(latest_version, APP_VERSION),
        "manifest": manifest,
        "news": news,
        "news_version": news_version,
        "release_visible": False,
        "news_visible": bool(news_version),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def require_admin(token: str):
    if ADMIN_TOKEN and token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Admin token required")


def save_json_body(path: Path, raw: str):
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise HTTPException(status_code=400, detail="JSON must be an object")
    _write_json(path, data)
    return data


ensure_files()


@app.get("/")
def root():
    return {"ok": True, "message": "FRIDAY Cloud is running", "state": payload()}


@app.get("/api/state")
def api_state():
    return {"ok": True, "state": payload(), "cloud": payload()}


@app.get("/api/cloud/state")
def cloud_state():
    return {"ok": True, "cloud": payload()}


@app.post("/api/admin/cloud")
def admin_manifest(body: JsonBody, token: str = ""):
    require_admin(token)
    data = save_json_body(MANIFEST_FILE, body.raw)
    return {"ok": True, "manifest": data, "cloud": payload()}


@app.post("/api/admin/cloud/news")
def admin_news(body: JsonBody, token: str = ""):
    require_admin(token)
    data = save_json_body(NEWS_FILE, body.raw)
    return {"ok": True, "news": data, "cloud": payload()}


@app.get("/FridaySetup.exe")
@app.get("/friday.exe")
@app.get("/download/FridaySetup.exe")
@app.get("/download/friday.exe")
def installer_download():
    for candidate in INSTALLER_CANDIDATES:
        if candidate.exists() and candidate.is_file():
            return FileResponse(str(candidate), filename=candidate.name)
    raise HTTPException(status_code=404, detail="Installer file is not uploaded yet")


@app.get("/admin", response_class=HTMLResponse)
def admin_page():
    manifest = json.dumps(load_manifest(), ensure_ascii=False, indent=2)
    news = json.dumps(load_news(), ensure_ascii=False, indent=2)
    return f"""
<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>FRIDAY Cloud Admin</title>
  <style>
    body {{ margin:0; background:#0a0b10; color:#eef3ff; font-family:Arial,sans-serif; }}
    .wrap {{ max-width:1200px; margin:0 auto; padding:32px; }}
    .grid {{ display:grid; grid-template-columns:1fr 1fr; gap:20px; }}
    textarea {{ width:100%; min-height:420px; background:#111521; color:#eef3ff; border:1px solid #283042; border-radius:14px; padding:16px; font-family:ui-monospace,Consolas,monospace; }}
    button {{ border:0; border-radius:999px; padding:12px 18px; background:linear-gradient(135deg,#8f6bff,#5f8cff); color:white; cursor:pointer; font-weight:700; }}
    .card {{ background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.08); border-radius:20px; padding:20px; }}
    .row {{ display:flex; gap:12px; align-items:center; flex-wrap:wrap; }}
    .muted {{ color:#9aa6bf; }}
  </style>
</head>
<body>
    <div class="wrap">
      <h1>FRIDAY Cloud Admin</h1>
      <p class="muted">Панель для JSON-обновлений и новостей. Для записи через API передай `token`.</p>
      <div class="card" style="margin-bottom:18px;">
        <div class="row">
          <label class="muted" for="token">Admin token</label>
          <input id="token" placeholder="optional" style="flex:1; min-width:260px; background:#111521; color:#eef3ff; border:1px solid rgba(255,255,255,0.08); border-radius:999px; padding:10px 14px;" />
        </div>
      </div>
      <div class="row">
        <button onclick="save('manifest')">Сохранить manifest</button>
        <button onclick="save('news')">Сохранить news</button>
      </div>
    <div class="grid" style="margin-top:20px;">
      <div class="card">
        <h3>manifest.json</h3>
        <textarea id="manifest">{manifest}</textarea>
      </div>
      <div class="card">
        <h3>news.json</h3>
        <textarea id="news">{news}</textarea>
      </div>
    </div>
  </div>
  <script>
    async function save(kind) {{
      const raw = document.getElementById(kind).value;
      const token = document.getElementById('token').value;
      const res = await fetch(`/api/admin/cloud${{kind === 'news' ? '/news' : ''}}?token=${{encodeURIComponent(token)}}`, {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{ raw }})
      }});
      alert(await res.text());
    }}
  </script>
</body>
</html>
"""
