"""Stamp baked-blink runtime metadata into the facial Tier-2 preview meta.json.

QA dim8 requirement: these expression/listening clips bake their own blinks,
so the runtime blink scheduler must not fire procedural blinks on top of them
(mirrors patch_talking_meta.py). render_previews.py owns meta.json generation
(framework — not modified); this post-process injects, per clip:

  "baked_blinks":  [blink start frames]     (from the module's BLINK_META)
  "runtime_notes": suppression note + any per-clip cadence hint

Reads the BLINK_META dict literal out of clips/expressions_tier2.py and
clips/listening.py via ast (no bpy needed). Run AFTER render_previews.py with
any Python 3:
  python animations/scripts/patch_facial_tier2_meta.py
Idempotent — safe to re-run.
"""
import ast
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ANIM_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
SOURCES = [os.path.join(SCRIPT_DIR, "clips", "expressions_tier2.py"),
           os.path.join(SCRIPT_DIR, "clips", "listening.py")]
PREVIEWS = os.path.join(ANIM_ROOT, "previews")

SUPPRESS = ("Blinks are BAKED into this clip at the baked_blinks start frames. "
            "The runtime blink scheduler MUST suppress procedural blinks while "
            "this clip plays, or lids will double-blink. ")


def blink_meta_from_source(path):
    """Read the BLINK_META dict literal without importing (module needs bpy)."""
    with open(path, encoding="utf-8") as f:
        tree = ast.parse(f.read())
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name) and tgt.id == "BLINK_META":
                    return ast.literal_eval(node.value)
    raise SystemExit(f"BLINK_META dict not found in {path}")


def main():
    meta_all = {}
    for src in SOURCES:
        if os.path.isfile(src):
            meta_all.update(blink_meta_from_source(src))
    patched, missing = [], []
    for cid, info in meta_all.items():
        meta_path = os.path.join(PREVIEWS, cid, "meta.json")
        if not os.path.isfile(meta_path):
            missing.append(cid)
            continue
        with open(meta_path, encoding="utf-8") as f:
            meta = json.load(f)
        frames = sorted(info.get("blinks", []))
        meta["baked_blinks"] = frames
        note = info.get("note", "")
        meta["runtime_notes"] = (SUPPRESS + note) if frames else note
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=1)
        patched.append(cid)
        print(f"patched {meta_path}: baked_blinks={frames}")
    if missing:
        print(f"WARNING: no meta.json yet for {missing} — render previews "
              "first, then re-run this script.")
        sys.exit(1)
    print(f"OK: {len(patched)} meta.json files patched.")


if __name__ == "__main__":
    main()
