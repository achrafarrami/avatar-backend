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

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8100)
