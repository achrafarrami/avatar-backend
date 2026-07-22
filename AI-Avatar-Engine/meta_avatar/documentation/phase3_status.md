# Phase 3 — End-to-End Meta Avatar Generation: Status Board

Orchestrator-maintained (Ruflo swarm `swarm-1784730488354-cljzrv`, hierarchical).
Goal: photos → AI params → Meta mapping → assembled avatar.glb → sandbox → QA.

## Ground rules (all agents)

- REUSE, don't rebuild: AI pipeline (`ai/photo_analyzer/`), morph layer,
  WardrobeManager + `assets/shared/catalog.json`, `export_avatar_glb.py`.
- NEVER modify: the realistic pipeline, `morph_definitions.json` (AI 20×20
  contract), AI models. Meta-only additions live under `meta_avatar/` or as
  additive sandbox/backend code.
- Blender headless: `"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" --background --python <script> -- <args>` (engine enum `BLENDER_EEVEE`).
- Verify visually (renders) before declaring done.

## Task board

| # | Owner | Task | Depends on | Status |
|---|-------|------|-----------|--------|
| T1 | ai-pipeline | Verify pipeline health; build SYNTHETIC photo sets (template renders, incl. haired); run per-set → `avatar_parameters.json`; check gender/confidence/faceMeta | — | **DONE** |
| T2 | blender-meta | Automated meta-template test script (bones/ARKit/morphs/followers/extremes) + smoke renders | — | **DONE — PASS/PASS** |
| T3 | hair-assets | Fit hair/beard/glasses/hats/accessories to META heads; per-item verify renders; `assets_metadata.json` | T2 | **DONE** — 8/22 items fitted (hair w01/w03/w07/w09 @1.5702, glasses_round + cap @1.447, watch, beard_short skinned/empirical); live-sandbox spot-verified; renders in `documentation/test_renders/wardrobe_fit/`; 14 honestly unfitted with notes |
| T4 | clothing | Skinned clothing on meta bodies (male: hoodie/shirt/pants/shoes; female: shirt/jacket/pants/shoes); clipping + export checks | T2 | **DONE + QA-verified** (before/after renders inspected; verify_glb independently re-run on dressed_test_male.glb) |
| T5 | backend | `backend/generate_avatar.py`: photos-dir → pipeline → meta mapping (exaggeration 1.3, gender→meta base) → assembly (morphs+assets) → `avatar.glb` | T1, T3, T4 | **DONE** — CLI + `--assets` forcing; 4 case GLBs built+verified (`backend/output/case{1..4}/`); hair auto-lights-up when T3 publishes; new `assemble_avatar.py` (thin, additive) |
| T6 | sandbox | Photos tab: Avatar Style radio (Realistic ○ / Meta ○); meta base on generate; compare photos-vs-avatar strip | T1 (params shape known) | **DONE + QA-verified live** (real Generate click incl. compare strip; exaggeration recomputed independently; D3 fix independently re-measured — clean 0.05m axis-aligned delta) |
| T7 | qa | 4 test cases end-to-end + `qa_report.md` | T5, T6 | **DONE** — verdict below; report at `documentation/qa_report.md` |

## Decisions (orchestrator)

- **D1-REVISED (2026-07-22)**: the `wardrobe.js` per-style override READER
  (setStyle/_resolved, glb/offset/scale + plain-field, applied in
  equip()/setColor()) was implemented and verified by **sandbox** and is now
  canonical. hair-assets delivers DATA only (item.json styles blocks +
  assets_metadata.json + renders). Sandbox also fixed a real radio-group bug
  (same-name radios form one document-wide group → split into
  avatar-style-hud/avatar-style-photos, class-synced).
- **D1 — Per-style asset override schema** (owner: hair-assets): optional
  `item.json` block `"styles": {"meta": {"offset":[x,y,z], "scale": s, "glb": "<path>"}}`
  read additively in `WardrobeManager.equip()`; `offset`/`scale` for
  bone-attached items, `"glb"` swap for skinned (clothing). `wardrobe.js` is
  owned by hair-assets; `src/main.js` is owned by sandbox (calls
  `wardrobe.setStyle('meta'|'realistic')`).
- **D2 — Comms routing**: agent names are not registered in this session; all
  inter-agent messages route through the orchestrator ('main'), which relays.

- **D3 — Bone-attach offset defect (2026-07-22, found by hair-assets):**
  post-hoc `root.position` offsets on bone-attached items are pre-multiplied
  by the bone's inverse-rest transform baked into root (0.01 import scale +
  rest rotation) → ~100× undershoot + axis mixing; `scale` overrides work.
  **RESOLVED by sandbox (2026-07-22):** attachAsset(url, name, boneName,
  offset, scale) now bakes offset (world meters) into bonePos before the
  parentInv bake (Matrix4.compose, identity-equivalent when offset=null/
  scale=1); wardrobe.equip() passes fits for bone items, keeps post-hoc
  mutation only for skinned (identity parent — correct). Verified live:
  0.05m test offset → (−2e-22, 2e-16, 0.05) world delta; scale 1.5 exact;
  realistic placement unchanged; state reset. Item.json data stays
  true-meters (no per-bone fudge).

- **D4 — Rigid bone-parenting breaks in glTF export (2026-07-22, found by
  backend):** parent_type='BONE' props land ~3.5m off with 100× scale in the
  exported GLB (skinned/Armature-modifier path is fine). Backend worked
  around with static world placement → props correct at rest pose but do NOT
  follow head animation in exported avatars. **RESOLVED by backend
  (2026-07-22):** attach_bone() now single-bone rigid-skins each prop
  (_make_single_bone_skin: vertex group named for the attach bone @1.0 on
  all verts + Armature modifier; no bone parenting). Verified: exported
  avatar with forced glasses_round, re-imported, rest pose correct, then
  CC_Base_Head rotated 35° in Pose Mode → glasses follow rigidly, still
  seated. QA's case1–4 builds unaffected (contained no bone-type items).
  Sandbox RUNTIME attachment was never affected (Three.js parents live).
- Icosphere-in-every-export re-confirmed by backend on bare realistic
  templates (pre-existing exporter artifact; chip already filed Phase 1).
- **F5 — Skinned-item retarget mismatch (2026-07-22, found by hair-assets):**
  retargeting a skinned item's Armature modifier to the meta rig does NOT
  preserve position per simple bone-anchor formulas — bone REST ORIENTATIONS
  differ slightly between realistic/meta rigs, not just positions.
  beard_short fitted empirically (5 render iterations); eyebrows items
  flagged unfitted/at-risk in assets_metadata.json.
- Comms note: the backend agent's transcript expired after T5+D4 completion —
  further backend work (if any) is handled directly by the orchestrator.

## Blockers

- **B1 — No real photo sets** (`ai/photo_analyzer/input/` is empty; personal
  photos are gitignored). QA cases 1–4 (beard/hat/long-hair/curly+glasses)
  need real photos for full validation. Interim: T1 builds synthetic sets from
  template renders (same trick as the calibration loop). **ACTION (user):**
  drop photo sets into `ai/photo_analyzer/input/<set>/{front,left,right}.jpg`.

## Test results

- **T2 meta-template regression (2026-07-22): PASS both genders.** 101
  CC_Base_* bones; 20 identity + head_size + body_weight keys (−1..1);
  ARKit 52/52; follower contract verified (head_size on every mesh,
  eye keys ×3 meshes, 10/11 eyebrow followers, 11 teeth+tongue followers);
  extremes ±1 no NaN, displacement < ceiling; render smoke clean (mouths
  closed, head_size=1 intact). Script:
  `meta_avatar/blender/scripts/test_meta_templates.py`; reports:
  `documentation/test_meta_{male,female}.json`; renders:
  `documentation/test_renders/`. Templates untouched (read-only test).
  → GO relayed to T3 + T4.
- **T1 AI pipeline verification (2026-07-22): PASS, all 4 synthetic cases.**
  Full stack live (MediaPipe, BiSeNet, ArcFace, MICA, OpenAI VLM — key
  configured). Gender == template on 4/4; params in [0,1], non-neutral;
  faceMeta complete; appearance labels sane. Sets:
  `ai/photo_analyzer/input/synth_case{1..4}_*/`; outputs:
  `ai/photo_analyzer/output/phase3/case{1..4}_avatar_parameters.json`.
  New tooling (additive): `blender/scripts/render_synthetic_photoset.py`.
  Findings (no code changed): (F1) right-profile fails when long hair covers
  the far ear — graceful degradation, real-photo failure mode too; (F2) VLM
  misread scaled female bun on male head — male hair fits are a risk area;
  (F3) fusion ridge solve mutes simultaneous extremes toward 0.5 (measured
  .83 → fused .50) — calibration-tuning nuance for calibration.json owners;
  generated avatars will read softer than ground truth.
  → Relayed to T5 + T7.
- **T7 cross-check of T1 (2026-07-22):** all three findings confirmed in the
  raw data. NEW finding (F4, qa): `cheekboneHeight` and `earSize` are EXACTLY
  0.5 in all 4 cases (zero signal, not muting) and `jawAngle` collapses to
  ~neutral even at extreme targets — filed as a background investigation task
  (out of Phase-3 scope; calibration/measurement diagnosis). REQUIREMENT
  relayed to T5: CLI must support explicit `--assets` forcing (synthetic
  appearance blocks can't drive asset selection; auto-detect stays default).

## Fix round (approved by user 2026-07-22)

| # | Owner | Task | Status |
|---|-------|------|--------|
| T8 | backend-fix | Fix D5/D6/D7 in `assemble_avatar.py` | **DONE** — root cause: AXIS-FRAME mismatch (catalog stores three.js-frame offsets; assembly consumed them unconverted; fix `_meta_offset_to_blender` x,y,z→(x,−z,y)) + attach_skinned() ignored fits (now applies to rest geometry pre-retarget). No fit values changed; only assemble_avatar.py touched. case{1,2,3,4}_fix regenerated, render+numeric verified (beard bbox eye-height→jaw 1.48–1.56m; cap contacts scalp; glasses on bridge both genders; case3 regression clean) |
| T9 | qa-reverify | Re-verify CASE1/2/4 + confirm CASE3 unchanged; amend qa_report.md verdict | **DONE** — D6 RESOLVED (own bbox: beard Z 1.4828–1.5586m = jaw), D7 RESOLVED (both genders), CASE3 clean, D4 preserved (0.1585m vertex displacement @45° head rotation). **D5 NOT resolved**: cap still floats 10.24cm — AND T3's own reference renders show the identical gap → fit-VALUE miscalibration (cap offset/scale), not assembly code. Re-scoped to data fix. |
| T10 | cap-fit-fix | Re-derive cap's meta fit values | **DONE** — root cause: generic head_compromise formula assumed cap's dome landmark == head crown (off ~6cm in cap local coords, ×1.447 → 10cm float; reproduced analytically first). New values scale 1.371101 / offset_blender [0,−0.008696,−0.099505], landmark-solved per gender + averaged; gap 10.22/9.25cm → 1.70/0.71cm (m/f); v2 renders both genders; case2_fix2 regenerated + round-trip re-measured (1.702cm). Old values retained as _v1_MISCALIBRATED; data files only |
| T11 | qa-reverify | Final CASE2 re-check + close qa_report.md | **DONE — REPORT CLOSED. ALL 4 CASES PASS** (raycast-grid gap 1.61–2.29cm, 0/25 interpenetrations; other 7 items' values diff-confirmed unchanged; gap asymmetry ruled acceptable; back-hem closest-point reading ruled pre-existing/cosmetic after dedicated back-of-head render). Shipping builds: case1_fix, case2_fix2, case3_fix, case4_fix |

## FINAL VERDICT (T7, 2026-07-22)

**Core pipeline: SOLID, independently verified end-to-end on all 4 cases**
(photos → params → meta mapping → skeleton/ARKit/skinned clothing → sandbox).
CASE3 (female + hair_w03) is a clean full pass. **3 of 4 cases fail on
accessory fit in the GENERATION path** — all in `assemble_avatar.py`'s
consumption of T3's fit data (the sandbox runtime path applies fits
correctly; the Blender assembly path does not):

- **D5 [HIGH]** cap floats above scalp in generated GLB. attach_bone()
  applies offset/scale correctly per QA's vertex-level check → fit-value vs
  transform-semantics mismatch (pivot/order of scale+offset likely differs
  from T3's fitting scripts). Same suspect shared scale (1.447) as D7.
- **D6 [HIGH]** beard_short invisible (bbox at eye height): attach_skinned()
  takes NO offset/scale at all — skinned fits silently unused; rest-orientation
  mismatch (F5) makes pure bone-rebinding insufficient. NOT a contradiction
  with T3's sandbox verification — different consumer.
- **D7 [MED-HIGH]** glasses_round oversized + brow-height on both genders —
  systemic, shares the 1.447 ratio with cap.
- **[LOW]** no male-native hair fits (all 4 fitted styles are women's-pack);
  CASE1 "short hair" only approximable.
- **Coverage gap:** appearance-driven auto-detect asset path never exercised
  (synthetic photos detect bald/none) — first exercised when real photos
  arrive (B1).

Fix owner: orchestrator directly (backend agent expired). Fix plan: align
assemble_avatar.py's bone-item transform semantics with
`meta_avatar/blender/scripts/compute_fits.py`'s definition (scale about the
bone anchor, then world-meter offset), implement skinned-fit application for
attach_skinned() (or bake T3's empirical beard offset), re-run CASE1/2/4,
have QA re-verify.

## Completed

- Phase 1 (meta bases) + Phase 2 (stylized morph library) — merged to main.
