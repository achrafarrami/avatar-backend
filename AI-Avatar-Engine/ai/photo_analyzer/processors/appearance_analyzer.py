"""
Vision-language appearance analysis: photo → semantic appearance labels.

The VLM is prompted with a CLOSED vocabulary — exactly the labels that
appearance_map / the sandbox's APPEARANCE_MAP can turn into wardrobe equips —
so it can only answer things the engine can actually render. It produces
LABELS ONLY; it never touches geometry parameters.

Backend: OpenAI vision (key from ai/photo_analyzer/.env). The public
interface is a single `analyze_appearance(front, extra=[])` function so the
backend can be swapped (local VLM, Claude, ...) without callers changing.
No key configured → returns (None, warning) and the pipeline continues
geometry-only.
"""
import base64
import io
import json
import os

from dotenv import load_dotenv
from PIL import Image, ImageOps

try:  # iPhone HEIC support (optional)
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:
    pass

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

VOCAB = {
    "gender": ["male", "female"],
    "skinTone": ["light", "medium_light", "medium", "medium_dark", "dark"],
    "hairStyle": ["bald", "short", "pigtails", "high_ponytail", "long",
                  "side_sweep", "updo", "low_bun", "spiky", "pixie", "bob",
                  "side_ponytail"],
    "hairColor": ["black", "dark_brown", "brown", "chestnut", "auburn",
                  "light_brown", "dark_blonde", "blonde", "platinum",
                  "gray", "white", "red"],
    "beardStyle": ["none", "short", "goatee"],
    "glasses": ["none", "round", "square"],
    "bodyType": ["slim", "average", "athletic", "heavy"],
}

_PROMPT = f"""You are an avatar-creation assistant. Look at the photo(s) of a person and describe their appearance using ONLY the allowed values below. Always pick the CLOSEST available option, even if imperfect (this maps onto a fixed 3D wardrobe).

Allowed values:
- gender: {VOCAB['gender']} — judge carefully from facial features, this selects the avatar body
- skinTone: {VOCAB['skinTone']}
- hair.style: {VOCAB['hairStyle']}
    bald = shaved or no hair on top (side stubble still counts as bald)
    short = short men's crop (any short masculine cut)
    pigtails = two bunches left+right
    high_ponytail = hair tied up high at the back
    long = long loose hair past the shoulders
    side_sweep = long hair swept across to one side of the face
    updo = gathered up with loose face-framing strands
    low_bun = pulled back into a bun at the nape
    spiky = choppy spiky fringe over one eye
    pixie = very short feminine crop
    bob = chin/jaw-length cut
    side_ponytail = ponytail over one shoulder with bangs
- hair.color: {VOCAB['hairColor']} (null if hair.style is "bald"; chestnut = warm mid-brown, auburn = red-brown, platinum = near-white blonde)
- beard.style: {VOCAB['beardStyle']} (goatee = chin/mustache only; short = full short beard/stubble)
- beard.color: same values as hair.color (null if beard.style is "none")
- glasses: {VOCAB['glasses']}
- bodyType: {VOCAB['bodyType']} (guess "average" if only the face is visible)

Reply with ONLY this JSON object, no other text:
{{"gender": "...", "skinTone": "...",
  "hair": {{"style": "...", "color": "..."}},
  "beard": {{"style": "...", "color": "..."}},
  "glasses": "...", "bodyType": "...",
  "confidence": 0.0}}
confidence = your overall confidence, 0..1."""


def _encode(path, max_side=768):
    """Downscale + JPEG-encode to keep vision tokens/cost low."""
    img = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    img.thumbnail((max_side, max_side))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=88)
    return base64.b64encode(buf.getvalue()).decode()


def _validate(res):
    """Force every field into the closed vocabulary (None if it drifted)."""
    def pick(value, vocab):
        return value if value in vocab else None
    hair = res.get("hair") or {}
    beard = res.get("beard") or {}
    out = {
        "gender": pick(res.get("gender"), VOCAB["gender"]),
        "skinTone": pick(res.get("skinTone"), VOCAB["skinTone"]),
        "hair": {"style": pick(hair.get("style"), VOCAB["hairStyle"]),
                 "color": pick(hair.get("color"), VOCAB["hairColor"])},
        "beard": {"style": pick(beard.get("style"), VOCAB["beardStyle"]),
                  "color": pick(beard.get("color"), VOCAB["hairColor"])},
        "glasses": pick(res.get("glasses"), VOCAB["glasses"]),
        "bodyType": pick(res.get("bodyType"), VOCAB["bodyType"]),
        "confidence": res.get("confidence")
        if isinstance(res.get("confidence"), (int, float)) else None,
    }
    if out["hair"]["style"] == "bald":
        out["hair"]["color"] = None
    if out["beard"]["style"] == "none":
        out["beard"]["color"] = None
    return out


def analyze_appearance(front, extra=()):
    """Returns (labels_dict|None, warning|None)."""
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key or key.startswith("sk-...your"):
        return None, ("OPENAI_API_KEY not set — appearance analysis skipped "
                      "(copy ai/photo_analyzer/.env.example to .env)")
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini").strip()

    try:
        from openai import OpenAI
        # hard timeout: a hung API call must never freeze the whole pipeline
        client = OpenAI(api_key=key, timeout=45.0, max_retries=1)
        content = [{"type": "text", "text": _PROMPT}]
        for path in (front, *[p for p in extra if p]):
            content.append({"type": "image_url", "image_url": {
                "url": f"data:image/jpeg;base64,{_encode(path)}"}})
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": content}],
            response_format={"type": "json_object"},
            max_tokens=300,
            temperature=0,
        )
        return _validate(json.loads(resp.choices[0].message.content)), None
    except Exception as e:  # network/key/quota errors must not kill geometry
        return None, f"appearance analysis failed ({type(e).__name__}: {e})"
