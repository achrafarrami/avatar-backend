"""
One-command avatar generation: a photos directory in, a complete rigged
avatar.glb out.

Steps (each degrades gracefully -- a missing wardrobe asset never aborts
the run, only a broken template/export does):
  1. AI analysis   -- ai/photo_analyzer/pipeline.py (analyze_photos), reusing
                       the front/left/right discovery convention from
                       ai/photo_analyzer/validate_real.py. --skip-analysis
                       bypasses this with an existing avatar_parameters.json
                       (deterministic QA runs).
  2. Meta mapping  -- camelCase "face" params -> engine snake_case (derived
                       from ai/photo_analyzer/pipeline.py's CAMEL table, the
                       same contract blender/scripts/render_avatar_params.py
                       inverts as CAMEL_TO_SNAKE), then exaggerated about the
                       0.5 neutral: p' = 0.5 + (p-0.5)*exaggeration, clamped
                       to [0,1]. exaggeration is read from
                       meta_avatar/renderer/meta.map.json (1.3) for
                       --style meta, fixed at 1.0 (no-op) for --style
                       realistic. Gender selects the template.
  3. Asset select  -- appearance labels (hair/beard/glasses) -> wardrobe
                       catalog ids via assets/shared/catalog.json, mirroring
                       frontend/threejs-viewer/src/main.js's APPEARANCE_MAP
                       (kept in sync by hand, same as the morph-math dup).
                       Default outfit: top/pants/shoes. For --style meta,
                       an item is only worn if it has a verified meta fit
                       (D1 schema: catalog item "styles"."meta" block, or an
                       equivalent entry in meta_avatar/assets/
                       assets_metadata.json) -- unfittable/undetected items
                       are skipped with a log line, never guessed.
                       --assets overrides/extends the auto-detected picks
                       per slot (deterministic QA path; see below).
  4. Assembly      -- meta_avatar/blender/scripts/assemble_avatar.py (new,
                       thin) attaches the selected assets onto the template;
                       blender/scripts/export_avatar_glb.py (unmodified)
                       bakes the exaggerated identity params into the mesh
                       basis and exports the final GLB.
  5. Verify        -- blender/scripts/verify_glb.py re-imports the GLB and
                       renders a preview PNG next to it.

Usage:
  ai/.venv/Scripts/python backend/generate_avatar.py <photos_dir> <out.glb> \
      [--style meta|realistic] [--skip-analysis <avatar_parameters.json>] \
      [--assets '<json>']

<photos_dir> layout (same loose convention as validate_real.py's "default"
set): front.(jpg|jpeg|png|webp|heic) required, left.* / right.* optional.

--assets '<json>' forces specific catalog ids per slot, overriding the
appearance-driven auto-detection -- the deterministic path for QA/tests,
since synthetic/geometry-focused analysis runs often don't detect any
wearable appearance (bald/no-beard/no-glasses). Auto-detection stays the
default when --assets is omitted or a slot is left out of it.
  {"hair": "<id>", "beard": "<id>", "glasses": "<id>", "hat": "<id>",
   "clothes": ["<id>", ...]}
- Any top-level key names a slot directly (hair/beard/glasses/hat/top/
  pants/shoes/wrist/ears/neck/back) except "clothes", which is a
  convenience list of ids auto-sorted into their own slot via the catalog
  (so {"clothes": ["hoodie", "jeans", "sneakers"]} equips all three).
- "none" (string) forces that slot explicitly EMPTY -- no auto-detect
  fallback, no item worn.
- A slot omitted entirely keeps the normal appearance-derived pick (or
  the default outfit for top/pants/shoes).
- An unknown catalog id, or an id given under the wrong slot key, is a
  fatal error (a QA typo should never silently no-op).
Example: --assets '{"hair":"hair_w03","beard":"none","glasses":"glasses_round"}'
"""
import argparse
import glob
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE_ROOT = os.path.dirname(HERE)                                  # AI-Avatar-Engine/
PHOTO_ANALYZER_DIR = os.path.join(ENGINE_ROOT, "ai", "photo_analyzer")
BLENDER_SCRIPTS = os.path.join(ENGINE_ROOT, "blender", "scripts")
REALISTIC_TEMPLATES = os.path.join(ENGINE_ROOT, "blender", "templates")
META_ROOT = os.path.join(ENGINE_ROOT, "meta_avatar")
META_SCRIPTS = os.path.join(META_ROOT, "blender", "scripts")
META_BASE = os.path.join(META_ROOT, "blender", "base")
META_ASSETS_DIR = os.path.join(META_ROOT, "assets")
META_ASSETS_METADATA = os.path.join(META_ASSETS_DIR, "assets_metadata.json")
SHARED_ASSETS_DIR = os.path.join(ENGINE_ROOT, "assets", "shared")
CATALOG_PATH = os.path.join(SHARED_ASSETS_DIR, "catalog.json")
META_MAP_PATH = os.path.join(META_ROOT, "renderer", "meta.map.json")
MORPH_DEFS_PATH = os.path.join(BLENDER_SCRIPTS, "morph_definitions.json")

EXPORT_SCRIPT = os.path.join(BLENDER_SCRIPTS, "export_avatar_glb.py")
VERIFY_SCRIPT = os.path.join(BLENDER_SCRIPTS, "verify_glb.py")
ASSEMBLE_SCRIPT = os.path.join(META_SCRIPTS, "assemble_avatar.py")
BLENDER = r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"

sys.path.insert(0, PHOTO_ANALYZER_DIR)

DEFAULT_OUTFIT = {"top": "tshirt", "pants": "jeans", "shoes": "sneakers"}

# Semantic appearance labels -> wardrobe catalog ids / palette hex.
# Mirrors frontend/threejs-viewer/src/main.js's APPEARANCE_MAP exactly --
# these two must stay in sync by hand (same duplication contract already
# accepted for the morph-value formula between MorphController and
# computeKeyValues; see root CLAUDE.md).
APPEARANCE_MAP = {
    "hairStyle": {
        "pigtails": "hair_w01", "high_ponytail": "hair_w02",
        "long": "hair_w03", "side_sweep": "hair_w04", "updo": "hair_w05",
        "low_bun": "hair_w06", "spiky": "hair_w07", "pixie": "hair_w08",
        "bob": "hair_w09", "side_ponytail": "hair_w10",
        "bald": None, "short": None, "none": None,
    },
    "beardStyle": {"short": "beard_short", "goatee": "goatee", "none": None},
    "glasses": {"round": "glasses_round", "square": "glasses_square",
               "none": None},
    "hairColor": {
        "black": "#0f0f12", "dark_brown": "#3b2a1e", "brown": "#6a4a2f",
        "chestnut": "#55371f", "auburn": "#7a3f24", "light_brown": "#8c6239",
        "dark_blonde": "#a67c48", "blonde": "#c9a06a", "platinum": "#e6d6b8",
        "gray": "#9a9ea6", "white": "#e8e6e2", "red": "#a34a26",
    },
}


def log(msg):
    """Windows console is cp1252 -- never let a stray unicode char crash
    the run (same constraint validate_real.py documents)."""
    try:
        print(msg)
    except UnicodeEncodeError:
        print(str(msg).encode("ascii", "replace").decode("ascii"))


# --------------------------------------------------------------- step 1
def discover_photos(photos_dir):
    """Reuses validate_real.py's own front/left/right discovery helper
    (the 'default' loose-set convention: front.* required, left./right.*
    optional) instead of re-implementing the extension search."""
    from validate_real import _find_photo
    front = _find_photo(photos_dir, "front")
    if front is None:
        sys.exit(f"[fatal] no front.<ext> found in {photos_dir} "
                 "(expected front.jpg|jpeg|png|webp|heic)")
    return {"front": front, "left": _find_photo(photos_dir, "left"),
           "right": _find_photo(photos_dir, "right")}


def run_analysis(photos_dir, out_dir):
    from pipeline import analyze_photos, FrontPhotoError
    photos = discover_photos(photos_dir)
    log(f"[analysis] front={photos['front']}"
        + (f" left={photos['left']}" if photos["left"] else "")
        + (f" right={photos['right']}" if photos["right"] else ""))
    analysis_dir = os.path.join(out_dir, "analysis")
    os.makedirs(analysis_dir, exist_ok=True)
    try:
        result, raw, engine_params, warnings = analyze_photos(
            photos["front"], photos["left"], photos["right"],
            debug_dir=os.path.join(analysis_dir, "debug"))
    except FrontPhotoError as e:
        sys.exit(f"[fatal] analysis failed: {e}")
    for w in warnings:
        log(f"[analysis][warn] {w}")
    # same output contract as pipeline.py main()
    with open(os.path.join(analysis_dir, "raw_analysis.json"), "w") as f:
        json.dump(raw, f, indent=2)
    with open(os.path.join(analysis_dir, "avatar_parameters.json"), "w") as f:
        json.dump(result, f, indent=2)
    with open(os.path.join(analysis_dir, "identity_paste.json"), "w") as f:
        json.dump(engine_params, f, indent=2)
    log(f"[analysis] gender={result.get('gender')} -> {analysis_dir}")
    return result


def load_skip_analysis(path):
    with open(path, encoding="utf-8-sig") as f:
        result = json.load(f)
    if "face" not in result:
        sys.exit(f"[fatal] {path} is not a valid avatar_parameters.json "
                 "(missing 'face')")
    return result


# --------------------------------------------------------------- step 2
def camel_to_snake_face(face_camel):
    """engine snake_case <- avatar_parameters.json camelCase 'face' block.
    Derived from pipeline.py's own CAMEL table (already imported for
    analyze_photos) rather than retyping render_avatar_params.py's
    CAMEL_TO_SNAKE -- the two are the same table, inverted; that file can't
    be imported directly here since it opens with `import bpy` and this
    script must run under the plain ai/.venv (no Blender) python."""
    from pipeline import CAMEL
    inv = {v: k for k, v in CAMEL.items()}
    dropped = [k for k in face_camel if k not in inv]
    if dropped:
        log(f"[mapping][warn] ignoring unknown face params: {dropped}")
    return {inv[k]: v for k, v in face_camel.items() if k in inv}


def load_exaggeration(style):
    if style == "realistic":
        return 1.0
    with open(META_MAP_PATH, encoding="utf-8-sig") as f:
        m = json.load(f)
    return float(m.get("exaggeration", 1.3))


def apply_exaggeration(snake_params, exaggeration):
    """p' = 0.5 + (p-0.5)*exaggeration, clamped to [0,1]; only the 20
    known morph_definitions.json params are kept (plain-data validation,
    no bpy/Blender needed to check membership)."""
    with open(MORPH_DEFS_PATH, encoding="utf-8-sig") as f:
        defs = json.load(f)
    valid = set(defs["params"].keys())
    out = {}
    for k, v in snake_params.items():
        if k not in valid:
            continue
        p = 0.5 + (float(v) - 0.5) * exaggeration
        out[k] = max(0.0, min(1.0, p))
    return out


def select_template(style, gender):
    gender = (gender or "male").lower()
    if gender not in ("male", "female"):
        log(f"[mapping][warn] unrecognized gender '{gender}', defaulting male")
        gender = "male"
    if style == "meta":
        path = os.path.join(META_BASE, f"meta_{gender}.blend")
    else:
        path = os.path.join(REALISTIC_TEMPLATES, f"{gender}_base.blend")
    return path, gender


# --------------------------------------------------------------- step 3
def load_catalog():
    with open(CATALOG_PATH, encoding="utf-8-sig") as f:
        return json.load(f)


def parse_forced_assets(json_str, by_id):
    """--assets '{"hair":"hair_w03","beard":"none",...,"clothes":["hoodie",
    "jeans"]}' -> {slot: item_id_or_None} forced overrides (see the module
    docstring for the full contract). Returns {} when json_str is falsy.
    Fatal (clear error, not a silent skip) on an unknown id or a slot/id
    mismatch -- this is the deterministic QA path, it must not typo-silently
    no-op."""
    if not json_str:
        return {}
    try:
        raw = json.loads(json_str)
    except json.JSONDecodeError as e:
        sys.exit(f"[fatal] --assets is not valid JSON: {e}")
    if not isinstance(raw, dict):
        sys.exit("[fatal] --assets must be a JSON object")

    forced = {}
    for key, val in raw.items():
        if key == "clothes":
            if not isinstance(val, list):
                sys.exit("[fatal] --assets: 'clothes' must be a list of "
                         "catalog ids")
            for item_id in val:
                item = by_id.get(item_id)
                if item is None:
                    sys.exit(f"[fatal] --assets: unknown catalog id "
                             f"'{item_id}' in 'clothes'")
                forced[item["slot"]] = item_id
            continue
        if isinstance(val, str) and val.lower() == "none":
            forced[key] = None
            continue
        item = by_id.get(val)
        if item is None:
            sys.exit(f"[fatal] --assets: unknown catalog id '{val}' for "
                     f"slot '{key}'")
        if item["slot"] != key:
            sys.exit(f"[fatal] --assets: '{val}' belongs to slot "
                     f"'{item['slot']}', not '{key}'")
        forced[key] = val
    return forced


def _load_meta_overrides():
    """{"catalog_id": {"offset":[x,y,z]?, "scale": s?, "glb": "path"?}, ...}
    merged from two possible sources of the D1 override schema (per-item
    catalog "styles"."meta" block is read separately per item below; this
    is just the optional standalone assets_metadata.json some assets may
    ship instead/also). Missing file -> {} (meta wardrobe stays bare until
    hair-assets/clothing publish it), never fatal."""
    if not os.path.isfile(META_ASSETS_METADATA):
        log(f"[assets] no {META_ASSETS_METADATA} yet -- meta-only overrides "
            "unavailable this run")
        return {}
    with open(META_ASSETS_METADATA, encoding="utf-8-sig") as f:
        data = json.load(f)
    # tolerate either {"overrides": {...}} or a flat {id: {...}} map
    return data.get("overrides", data)


def _resolve_meta_override(item_id, base_item, standalone_overrides):
    """D1 schema: catalog item's own "styles"."meta" block wins; the
    standalone assets_metadata.json is a fallback/alternate source for the
    same shape. Returns None if this item has no verified meta fit yet."""
    styles = (base_item.get("styles") or {}).get("meta")
    if styles is not None:
        return styles
    return standalone_overrides.get(item_id)


def _resolve_meta_glb(candidate):
    """A "styles"."meta"."glb" path is relative, but its exact root/category
    directory naming isn't guaranteed (observed: catalog.json's stored path
    said "clothes/tshirt/tshirt_meta.glb" while T4 actually shipped the file
    under meta_avatar/assets/clothes_meta/tshirt/tshirt_meta.glb -- a
    "_meta" suffixed sibling directory). Try, in order: the literal path
    under meta_avatar/assets/ or assets/shared/; the same path with its
    first segment suffixed "_meta" (clothes -> clothes_meta, shoes ->
    shoes_meta, matching the convention above); finally a basename search
    anywhere under meta_avatar/assets/. Returns None if truly not found."""
    if os.path.isabs(candidate) and os.path.isfile(candidate):
        return candidate
    for root in (META_ASSETS_DIR, SHARED_ASSETS_DIR):
        p = os.path.join(root, candidate)
        if os.path.isfile(p):
            return p
    parts = candidate.replace("\\", "/").split("/")
    if len(parts) > 1 and not parts[0].endswith("_meta"):
        alt = "/".join([parts[0] + "_meta"] + parts[1:])
        p = os.path.join(META_ASSETS_DIR, alt)
        if os.path.isfile(p):
            return p
    matches = glob.glob(os.path.join(META_ASSETS_DIR, "**",
                                     os.path.basename(candidate)),
                        recursive=True)
    return matches[0] if matches else None


def resolve_assets(style, appearance, catalog, forced=None):
    """-> list of manifest entries ready for assemble_avatar.py.
    `forced` (from --assets, see parse_forced_assets) overrides/extends the
    appearance-derived pick per slot: a slot key mapped to None means
    explicitly worn empty (no auto-detect fallback); a slot absent from
    `forced` keeps the normal appearance-derived / default-outfit pick."""
    forced = forced or {}
    by_id = {it["id"]: it for it in catalog["items"]}

    hair = appearance.get("hair") or {}
    beard = appearance.get("beard") or {}
    wants = {
        "hair": APPEARANCE_MAP["hairStyle"].get(hair.get("style")),
        "beard": APPEARANCE_MAP["beardStyle"].get(beard.get("style")),
        "glasses": APPEARANCE_MAP["glasses"].get(appearance.get("glasses")),
    }
    wants.update(DEFAULT_OUTFIT)
    forced_slots = set(forced)
    wants.update(forced)   # None entries force an explicit empty slot
    colors = {
        "hair": APPEARANCE_MAP["hairColor"].get(hair.get("color")),
        "beard": APPEARANCE_MAP["hairColor"].get(beard.get("color")),
    }

    standalone_overrides = _load_meta_overrides() if style == "meta" else {}

    manifest = []
    for slot, item_id in wants.items():
        if not item_id:
            reason = "forced 'none' (--assets)" if slot in forced_slots \
                else "no matching item for detected appearance"
            log(f"[assets] slot '{slot}': {reason} -- skip")
            continue
        base_item = by_id.get(item_id)
        if base_item is None:
            log(f"[assets] slot '{slot}': catalog id '{item_id}' not found "
                "-- skip")
            continue

        abs_file = os.path.join(SHARED_ASSETS_DIR, base_item["file"])
        entry = {
            "slot": slot, "id": item_id, "file": abs_file,
            "attach_type": base_item.get("attach_type"),
            "attach_to": base_item.get("attach_to"),
            "colorable_materials": base_item.get("colorable_materials", []),
            "color_hex": colors.get(slot),
        }

        if style == "meta":
            override = _resolve_meta_override(item_id, base_item,
                                              standalone_overrides)
            if override is None:
                log(f"[assets] slot '{slot}': '{item_id}' has no verified "
                    "meta fit yet -- skip (waiting on hair-assets/clothing)")
                continue
            if override.get("glb"):
                resolved = _resolve_meta_glb(override["glb"])
                entry["file"] = resolved if resolved else override["glb"]
                # (falls through to the missing-file check below if still
                # unresolved, which reports and skips this item cleanly)
            if override.get("offset"):
                entry["offset"] = override["offset"]
            if override.get("scale"):
                entry["scale"] = override["scale"]

        if not os.path.isfile(entry["file"]):
            log(f"[assets] slot '{slot}': file missing {entry['file']} "
                "-- skip")
            continue
        manifest.append(entry)
        tag = " (forced via --assets)" if slot in forced_slots else ""
        log(f"[assets] slot '{slot}': {item_id} -> {entry['file']}{tag}")
    return manifest


# --------------------------------------------------------------- step 4/5
def run_blender(script, script_args, timeout, log_tail=25):
    cmd = [BLENDER, "--background", "--python", script, "--"] + script_args
    try:
        p = subprocess.run(cmd, capture_output=True, text=True,
                          timeout=timeout, encoding="utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        log(f"[blender] TIMEOUT running {os.path.basename(script)}")
        return False
    except OSError as e:
        log(f"[blender] could not launch Blender: {e}")
        return False
    tail = "\n".join((p.stdout or "").strip().splitlines()[-log_tail:])
    if tail:
        log(tail)
    if p.returncode != 0:
        err_tail = "\n".join((p.stderr or "").strip().splitlines()[-log_tail:])
        log(f"[blender] {os.path.basename(script)} exited {p.returncode}")
        if err_tail:
            log(err_tail)
        return False
    return True


def assemble(template, manifest, out_blend):
    manifest_path = out_blend + ".manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    ok = run_blender(ASSEMBLE_SCRIPT, [template, manifest_path, out_blend],
                     timeout=600)
    return ok and os.path.isfile(out_blend)


def export(source_blend, out_glb, params):
    params_path = out_glb + ".params.json"
    with open(params_path, "w") as f:
        json.dump(params, f, indent=2)
    ok = run_blender(EXPORT_SCRIPT,
                     [source_blend, out_glb, "--params", params_path],
                     timeout=600)
    return ok and os.path.isfile(out_glb)


def verify(out_glb, preview_png):
    return run_blender(VERIFY_SCRIPT, [out_glb, preview_png], timeout=300)


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("photos_dir")
    ap.add_argument("out_glb")
    ap.add_argument("--style", choices=["meta", "realistic"], default="meta")
    ap.add_argument("--skip-analysis", metavar="PARAMS_JSON", default=None)
    ap.add_argument("--assets", metavar="JSON", default=None,
                   help="force specific catalog ids per slot, overriding "
                        "appearance auto-detection (see module docstring)")
    args = ap.parse_args()

    if not os.path.isfile(BLENDER):
        sys.exit(f"[fatal] Blender not found at {BLENDER}")

    out_glb = os.path.abspath(args.out_glb)
    out_dir = os.path.dirname(out_glb)
    os.makedirs(out_dir, exist_ok=True)

    if args.skip_analysis:
        result = load_skip_analysis(args.skip_analysis)
        log(f"[analysis] skipped -- using {args.skip_analysis}")
    else:
        result = run_analysis(args.photos_dir, out_dir)

    gender_in = result.get("gender")
    appearance = result.get("appearance") or {}
    face_camel = result.get("face") or {}

    snake = camel_to_snake_face(face_camel)
    exaggeration = load_exaggeration(args.style)
    exag_params = apply_exaggeration(snake, exaggeration)
    log(f"[mapping] style={args.style} exaggeration={exaggeration} "
        f"params={len(exag_params)}")

    template, gender = select_template(args.style, gender_in)
    if not os.path.isfile(template):
        sys.exit(f"[fatal] template not found: {template}")
    log(f"[mapping] gender={gender} template={template}")

    catalog = load_catalog()
    by_id = {it["id"]: it for it in catalog["items"]}
    forced = parse_forced_assets(args.assets, by_id)
    manifest = resolve_assets(args.style, appearance, catalog, forced)

    source_for_export = template
    if manifest:
        assembled = os.path.join(out_dir, "_assembled.blend")
        if assemble(template, manifest, assembled):
            source_for_export = assembled
            log(f"[assemble] {len(manifest)} item(s) attached -> {assembled}")
        else:
            log("[assemble] assembly failed -- exporting bare template "
                "(no wardrobe) instead")
    else:
        log("[assemble] no wardrobe items resolved -- exporting bare template")

    if not export(source_for_export, out_glb, exag_params):
        sys.exit("[fatal] GLB export failed")
    log(f"[export] {out_glb} ({os.path.getsize(out_glb) / 1e6:.1f} MB)")

    preview_png = os.path.splitext(out_glb)[0] + "_preview.png"
    if verify(out_glb, preview_png):
        log(f"[verify] preview -> {preview_png}")
    else:
        log("[verify] verification failed (avatar.glb was still produced)")

    log(f"[done] {out_glb}")


if __name__ == "__main__":
    main()
