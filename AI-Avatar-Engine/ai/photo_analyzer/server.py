"""
Local API for the Avatar Sandbox's "Generate From Photos" panel.

  ai/.venv/Scripts/python ai/photo_analyzer/server.py     # -> localhost:8100

Staged endpoints so the UI can show real progress:
  POST /analyze?appearance=false  (front [req], left, right)  -> geometry fast
  POST /appearance                (front [req])               -> VLM labels
  POST /analyze                   (front [req], left, right)  -> both in one
Every response carries `timings` (seconds per stage). All errors are returned
as JSON HTTPExceptions so CORS headers survive and the browser can display
them (an unhandled 500 loses CORS and the frontend sees only "failed to
fetch").

Everything runs locally; uploaded photos go to a temp dir and are deleted
after analysis. The MediaPipe model is loaded once and reused (saves ~2s per
request); requests are serialized with a lock (single-user dev tool).
"""
import base64
import os
import shutil
import sys
import tempfile
import threading
import time

from fastapi import FastAPI, File, HTTPException, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

sys.path.insert(0, os.path.dirname(__file__))
from pipeline import analyze_photos, FrontPhotoError
from processors.face_landmarks import FaceMeasurer
from processors.face_parsing import FaceParser
from processors.identity_embedding import IdentityEmbedder
from processors.face3d import Face3D
from processors.face3d_measure import Face3DMeasurer
from processors.appearance_analyzer import analyze_appearance

app = FastAPI(title="Avatar Photo Analyzer")
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- shared data + assets served to the web / mobile clients --------------
# Single source of truth: the web sandbox (and the future mobile app) fetch
# the morph definitions, style maps, the wardrobe catalog + GLBs, and the
# sandbox avatar bases from here over HTTP instead of each client keeping its
# own copy. Every path below points at the canonical file already in the repo.
_HERE = os.path.dirname(__file__)                       # ai/photo_analyzer
_ENGINE = os.path.abspath(os.path.join(_HERE, "..", ".."))  # AI-Avatar-Engine

_DATA_FILES = {
    "morph_definitions.json":
        os.path.join(_ENGINE, "blender", "scripts", "morph_definitions.json"),
    "meta.map.json":
        os.path.join(_ENGINE, "meta_avatar", "renderer", "meta.map.json"),
    "style.json":
        os.path.join(_ENGINE, "meta_avatar", "renderer", "style.json"),
}
_AVATAR_FILES = {
    "sandbox_male.glb":
        os.path.join(_ENGINE, "blender", "exports", "sandbox_male.glb"),
    "sandbox_female.glb":
        os.path.join(_ENGINE, "blender", "exports", "sandbox_female.glb"),
    "sandbox_meta_male.glb":
        os.path.join(_ENGINE, "meta_avatar", "blender", "exports",
                     "sandbox_meta_male.glb"),
    "sandbox_meta_female.glb":
        os.path.join(_ENGINE, "meta_avatar", "blender", "exports",
                     "sandbox_meta_female.glb"),
}
_WARDROBE_DIR = os.path.join(_ENGINE, "assets", "shared")


@app.get("/data/{name}")
def shared_data(name: str):
    """Morph definitions / style maps — the JSON both clients read live."""
    path = _DATA_FILES.get(name)
    if not path or not os.path.isfile(path):
        raise HTTPException(status_code=404, detail=f"no such data file: {name}")
    return FileResponse(path, media_type="application/json")


@app.get("/avatars/{name}")
def avatar_base(name: str):
    """Sandbox avatar base GLBs (dev builds kept with the identity keys live)."""
    path = _AVATAR_FILES.get(name)
    if not path or not os.path.isfile(path):
        raise HTTPException(status_code=404, detail=f"no such avatar: {name}")
    return FileResponse(path, media_type="model/gltf-binary")


# Wardrobe catalog + every item GLB/thumbnail, straight from the canonical
# assets/shared tree: GET /wardrobe/catalog.json, /wardrobe/<cat>/<id>/<file>.
app.mount("/wardrobe", StaticFiles(directory=_WARDROBE_DIR), name="wardrobe")

_measurer = None
_parser = None
_lock = threading.Lock()


def get_measurer():
    global _measurer
    if _measurer is None:
        _measurer = FaceMeasurer()
    return _measurer


def get_parser():
    global _parser
    if _parser is None:
        _parser = FaceParser()  # available=False if model missing — fine
    return _parser


_embedder = None
_face3d = None
_face3d_measurer = None


def get_embedder():
    global _embedder
    if _embedder is None:
        _embedder = IdentityEmbedder()
    return _embedder


def get_face3d():
    """MICA reconstructor + measurer (loaded once; ~0.25s/photo on CPU)."""
    global _face3d, _face3d_measurer
    if _face3d is None:
        _face3d = Face3D()
        _face3d_measurer = Face3DMeasurer()
    return _face3d, _face3d_measurer


def _has_key():
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    return bool(key) and not key.startswith("sk-...your")


@app.get("/health")
def health():
    return {"ok": True,
            "appearance": "enabled" if _has_key() else
            "disabled (no OPENAI_API_KEY — copy .env.example to .env)"}


def _save_uploads(tmp, uploads):
    paths = {}
    for tag, up in uploads:
        if up is None:
            paths[tag] = None
            continue
        ext = os.path.splitext(up.filename or "")[1] or ".jpg"
        p = os.path.join(tmp, tag + ext)
        with open(p, "wb") as f:
            f.write(up.file.read())
        paths[tag] = p
    return paths


# NOTE: sync `def` endpoints on purpose — FastAPI runs them in a threadpool,
# so the several-seconds analysis never blocks the event loop.
_DEBUG_MIME = {".png": "image/png", ".jpg": "image/jpeg",
               ".jpeg": "image/jpeg"}


def _collect_debug(debug_dir):
    """Debug images -> {filename: data URL} for the sandbox debug panel."""
    images = {}
    if debug_dir and os.path.isdir(debug_dir):
        for fn in sorted(os.listdir(debug_dir)):
            ext = os.path.splitext(fn)[1].lower()
            mime = _DEBUG_MIME.get(ext)
            if not mime:
                continue
            with open(os.path.join(debug_dir, fn), "rb") as f:
                images[fn] = (f"data:{mime};base64,"
                              + base64.b64encode(f.read()).decode())
    return images


@app.post("/analyze")
def analyze(front: UploadFile = File(...),
            left: UploadFile | None = File(None),
            right: UploadFile | None = File(None),
            appearance: bool = True,
            gender: str | None = None,
            beard: str | None = None,
            debug: bool = False):
    if gender not in (None, "male", "female"):
        raise HTTPException(status_code=422, detail="gender must be male|female")
    if beard not in (None, "none", "short", "goatee"):
        raise HTTPException(status_code=422,
                            detail="beard must be none|short|goatee")
    tmp = tempfile.mkdtemp(prefix="photo_analyzer_")
    try:
        paths = _save_uploads(tmp, [("front", front), ("left", left),
                                    ("right", right)])
        debug_dir = os.path.join(tmp, "debug") if debug else None
        timings = {}
        with _lock:
            t0 = time.perf_counter()
            try:
                result, raw, engine_params, warnings = analyze_photos(
                    paths["front"], paths["left"], paths["right"],
                    with_appearance=appearance, fm=get_measurer(),
                    fp=get_parser(), ie=get_embedder(),
                    f3d=get_face3d()[0], m3d=get_face3d()[1],
                    gender_hint=gender, beard_hint=beard,
                    debug_dir=debug_dir)
            except FrontPhotoError as e:
                raise HTTPException(status_code=422, detail=str(e))
            timings["total_s"] = round(time.perf_counter() - t0, 2)
        print(f"[server] /analyze appearance={appearance} debug={debug} "
              f"took {timings['total_s']}s ({len(warnings)} warnings)")
        out = {"parameters": result, "engine_params": engine_params,
               "warnings": warnings, "timings": timings}
        if debug:
            out["debug"] = {"images": _collect_debug(debug_dir),
                            "raw": raw}
        return out
    except HTTPException:
        raise
    except Exception as e:  # keep CORS headers on unexpected failures
        print(f"[server] /analyze ERROR: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500,
                            detail=f"{type(e).__name__}: {e}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


@app.post("/appearance")
def appearance_only(front: UploadFile = File(...)):
    if not _has_key():
        return {"appearance": None,
                "warning": "OPENAI_API_KEY not set — copy .env.example to .env",
                "timings": {"total_s": 0}}
    tmp = tempfile.mkdtemp(prefix="photo_analyzer_")
    try:
        paths = _save_uploads(tmp, [("front", front)])
        t0 = time.perf_counter()
        labels, warn = analyze_appearance(paths["front"])
        secs = round(time.perf_counter() - t0, 2)
        print(f"[server] /appearance took {secs}s"
              f"{' warn: ' + warn if warn else ''}")
        return {"appearance": labels, "warning": warn,
                "timings": {"total_s": secs}}
    except Exception as e:
        print(f"[server] /appearance ERROR: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500,
                            detail=f"{type(e).__name__}: {e}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---- voice conversation (OpenAI, key stays server-side) -------------------
# The mobile/web client never sees OPENAI_API_KEY: it POSTs text/audio here and
# gets back a reply + speech. Key is loaded from ai/photo_analyzer/.env (via the
# load_dotenv already run when appearance_analyzer imported above).
_AURA_SYSTEM = (
    "You are Aura, a warm, upbeat AI companion who lives as the user's animated "
    "avatar. Reply the way you'd speak out loud: natural, friendly, and short "
    "(1-3 sentences). Be expressive and encouraging; never mention being a "
    "language model.")


def _openai():
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key or key.startswith("sk-...your"):
        raise HTTPException(status_code=503,
                            detail="OPENAI_API_KEY not set on the backend")
    from openai import OpenAI
    return OpenAI(api_key=key, timeout=45.0, max_retries=1)


class ChatIn(BaseModel):
    message: str
    history: list[dict] | None = None  # prior [{role, content}] turns


@app.post("/chat")
def chat(body: ChatIn):
    client = _openai()
    msgs = [{"role": "system", "content": _AURA_SYSTEM}]
    if body.history:
        msgs += body.history[-8:]  # keep context bounded
    msgs.append({"role": "user", "content": body.message[:2000]})
    try:
        r = client.chat.completions.create(
            model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
            messages=msgs, max_tokens=220, temperature=0.8)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"openai chat: {e}")
    return {"reply": (r.choices[0].message.content or "").strip()}


class TTSIn(BaseModel):
    text: str
    voice: str | None = None  # alloy|echo|fable|onyx|nova|shimmer


@app.post("/tts")
def tts(body: TTSIn):
    client = _openai()
    try:
        r = client.audio.speech.create(
            model=os.environ.get("OPENAI_TTS_MODEL", "tts-1"),
            voice=(body.voice or "nova"), input=body.text[:900])
        audio = r.read()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"openai tts: {e}")
    return Response(content=audio, media_type="audio/mpeg")


@app.post("/stt")
def stt(audio: UploadFile = File(...)):
    client = _openai()
    try:
        r = client.audio.transcriptions.create(
            model=os.environ.get("OPENAI_STT_MODEL", "whisper-1"),
            file=(audio.filename or "clip.webm", audio.file.read()))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"openai stt: {e}")
    return {"text": (r.text or "").strip()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8100)
