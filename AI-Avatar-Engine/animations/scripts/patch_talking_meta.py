"""Stamp lipsync runtime metadata into the talking clips' preview meta.json.

QA dim8 requirement: talking clips bake their own blinks (self-sufficient
base clips), so the runtime blink scheduler must not fire procedural blinks
on top of them. render_previews.py owns meta.json generation (framework —
not modified); this post-process step injects:

  "baked_blinks":  [blink start frames]        (from clips/talking.py)
  "runtime_notes": blink-scheduler suppression note

Run AFTER render_previews.py, with any Python 3 (no bpy needed):
  python animations/scripts/patch_talking_meta.py
Idempotent — safe to re-run.
"""
import ast
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ANIM_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
TALKING_SOURCES = [os.path.join(SCRIPT_DIR, "clips", "talking.py"),
                   os.path.join(SCRIPT_DIR, "clips", "talking_tier2.py")]
PREVIEWS = os.path.join(ANIM_ROOT, "previews")

RUNTIME_NOTE = (
    "Blinks are BAKED into this clip at the baked_blinks start frames "
    "(self-sufficient talking clip). The runtime blink scheduler MUST "
    "suppress procedural blinks while this clip plays, or lids will "
    "double-blink (library_spec talking runtime note)."
)


def baked_blinks_from_source(path):
    """Read the BAKED_BLINKS dict literal out of clips/talking.py without
    importing it (the module needs bpy)."""
    with open(path, encoding="utf-8") as f:
        tree = ast.parse(f.read())
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name) and tgt.id == "BAKED_BLINKS":
                    return ast.literal_eval(node.value)
    raise SystemExit(f"BAKED_BLINKS dict not found in {path}")


def main():
    blinks = {}
    for src in TALKING_SOURCES:
        if os.path.isfile(src):
            blinks.update(baked_blinks_from_source(src))
    patched, missing = [], []
    for cid, frames in blinks.items():
        meta_path = os.path.join(PREVIEWS, cid, "meta.json")
        if not os.path.isfile(meta_path):
            missing.append(cid)
            continue
        with open(meta_path, encoding="utf-8") as f:
            meta = json.load(f)
        meta["baked_blinks"] = sorted(frames)
        meta["runtime_notes"] = RUNTIME_NOTE
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=1)
        patched.append(cid)
        print(f"patched {meta_path}: baked_blinks={sorted(frames)}")
    if missing:
        print(f"WARNING: no meta.json yet for {missing} — render previews "
              "first, then re-run this script.")
        sys.exit(1)
    print(f"OK: {len(patched)} meta.json files patched.")


if __name__ == "__main__":
    main()
