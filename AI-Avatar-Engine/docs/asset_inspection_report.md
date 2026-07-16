# Male Base Template — Full Asset Inspection Report

**File:** `blender/templates/male_base.blend`
**Source:** Reallusion CC Character Base → `FBX/03_Neutral_M/Neutral_M.Fbx` (CC3+ / RL_CC3_Plus generation)
**Machine-readable inventory:** [`male_base_inspection.json`](male_base_inspection.json)
**Status:** inspection only — no mesh modifications in this pass.

---

## 1. Mesh objects (6)

| Object | Verts | Polys | Shape keys | UV maps | Purpose |
|---|---|---|---|---|---|
| `Male_Body` | 14,164 | 14,046 | 169 | Channel0 | Head + body + eyelashes + nails. The primary morph target. |
| `CC_Base_Eye` | 648 | 640 | 4 | Channel0 | Both eyeballs (sclera + cornea shells, L/R). |
| `CC_Base_Teeth` | 2,642 | 2,421 | 2 | Channel0 | Upper + lower teeth, bone-driven (not blendshape-driven). |
| `CC_Base_Tongue` | 309 | 296 | 38 | Channel0 | Tongue, viseme + expression keys. |
| `CC_Base_TearLine` | 190 | 136 | 120 | Channel0 | Thin wet-line strip under eyelids; follows face morphs. |
| `CC_Base_EyeOcclusion` | 182 | 144 | 137 | Channel0+1 | Soft shadow card over eyeballs; follows face morphs. |

**Total: ~18,100 vertices** — ideal real-time budget (Meta Avatars are in the same class). All 6 objects are skinned to the same armature via `ARMATURE` modifiers.

**Topology quality:** production-grade. Quad-dominant, animation-ready edge loops around eyes/mouth (this is Reallusion's commercial topology used across all CC characters — consistent forever, which is our core requirement). The `Topology Maps/` 8K wireframe references in the source package document the layout.

**UV quality:** single UDIM-less layout per material region (`Channel0`), no overlaps within material islands, generous face texel density (head gets its own 2K map). `CC_Base_EyeOcclusion` has a second UV channel (Channel1) used by CC's occlusion gradient — keep it.

## 2. Skeleton (1 armature, 101 bones)

Standard CC3+ biped. Full hierarchy in the JSON; summary by group:

| Group | Bones | Notes |
|---|---|---|
| Root/pelvis | `BoneRoot → Hip → Pelvis/Waist` | |
| Spine/neck | `Spine01, Spine02, NeckTwist01/02` | |
| Head/face | `Head → FacialBone → JawRoot, UpperJaw, L/R_Eye, Tongue01–03, Teeth01/02` | **Jaw, eyes, tongue, teeth are bone-driven** — critical: talking/blinking can combine bones + blendshapes |
| Arms | `Clavicle, Upperarm, Forearm, Hand` ×2 + twist bones ×2 each | Twist bones = clean forearm/shoulder deformation |
| Hands | 15 finger bones per hand (3 per finger) | Full finger articulation — "move hands" requirement ✅ |
| Legs | `Thigh, Calf, Foot, ToeBase` ×2 + twist bones + individual toes | |
| Special | `L/R_Breast`, `RibsTwist`, `KneeShareBone`, `ElbowShareBone`, `ToeBaseShareBone` | Share-bones = CC's volume-preservation helpers; harmless, exportable |

**Assessment:** humanoid-standard, retarget-friendly (Mixamo/UE/Unity mappings exist for CC3+ names). No IK chains in the FBX — FK only; IK is added at animation time, not in the template. Correct for our pipeline.

## 3. Materials (17) & textures

All textures **packed inside the .blend** — the file is fully self-contained and portable.

| Material | Maps (packed) | Resolution |
|---|---|---|
| `Std_Skin_Head/Body/Arm/Leg` | Diffuse + Normal | 2048² |
| `Std_Nails`, `Std_Eyelash` | Diffuse + Normal (+Opacity for lash) | 2048² |
| `Std_Eye_L/R` | Diffuse + Normal | 1024²/512² |
| `Std_Cornea_L/R` | Diffuse + Opacity | 1024² |
| `Std_Upper/Lower_Teeth` | Diffuse + Normal | 1024² |
| `Std_Tongue` | Diffuse + Normal + Reflection | 1024² |
| `Std_Tearline_L/R`, `Std_Eye_Occlusion_L/R` | Diffuse + Opacity | 64² |

**Gap (not a blocker):** roughness / AO / SSS / micro-normal maps exist in the source `textures/` folder but are not wired into the materials (FBX only embeds Diffuse/Normal/Opacity). For the final Three.js skin shader we should wire roughness+AO at minimum. Recommendation: do this at **export material build** time, not in the master template.

## 4. Shape key inventory — `Male_Body` (169 keys)

Classification (full name lists in the JSON):

| Class | Count | Examples | Role |
|---|---|---|---|
| `basis` | 1 | Basis | Rest shape |
| `expression` | 118 | `Eye_Blink_L`, `Mouth_Smile_R`, `Brow_Raise_Inner_L`, `Nose_Sneer_L`, `Cheek_Puff_L`... | **Animation only.** ARKit-style FACS units. Never exposed to users as customization. |
| `viseme` | 8 | `V_Open`, `V_Explosive`, `V_Dental_Lip`, `V_Tight_O`, `V_Tight`, `V_Wide`, `V_Affricate`, `V_Lip_Open` | **Lip-sync.** Audio-to-viseme drives these directly — this is our talking system. |
| `corrective` | 14 | `Head_Turn_L`, `Neck_Swallow_Up`... | Fired *together with* head/neck bone rotation to fix deformation. Not user-facing. |
| `secondary_animation` | 8 | `Eyelash_Upper_Down_L`... | Follow eyelid motion. Not user-facing. |
| `customization` | 20 | `face_width`, `nose_width`, `jaw_angle`... | **Our identity morphs** (built last session). User-facing via the morph layer. |

Secondary meshes carry synced copies: TearLine (120 keys incl. `TL *` fitting shapes), EyeOcclusion (137 incl. `EO *`), Tongue (38 incl. tongue visemes `V_Tongue_*`). These fire automatically at equal values with the body keys — the export/runtime layer must **drive same-named keys across all meshes together**.

## 5. ARKit-52 compatibility: **52 / 52 ✅**

Programmatically verified (see `arkit` section of the JSON): every one of Apple's 52 ARKit facial blendshapes maps onto existing CC keys.

- **46 map 1:1** (e.g. `eyeBlinkLeft → Eye_Blink_L`, `jawOpen → Jaw_Open`)
- **6 are composites** of 2–4 CC keys (`mouthFunnel`, `mouthPucker`, `mouthRollUpper`, `mouthRollLower`, `browInnerUp`, `cheekPuff`)
- Watch the eye-direction semantics: ARKit "In/Out" vs CC "L/R" (`eyeLookInLeft → Eye_L_Look_R`)

**Consequence:** any ARKit-based face tracking stream, and any TTS/emotion system emitting ARKit weights, can drive this avatar through a static remapping table. The table lives in `blender/scripts/inspect_asset.py` (`ARKIT_TO_CC`) and should be reused by the export/runtime layer.

## 6. Animation & export compatibility

| Concern | Verdict |
|---|---|
| Talking | ✅ 8 visemes + jaw bone + tongue keys |
| Blinking | ✅ `Eye_Blink_L/R` + eyelash followers |
| Emotions | ✅ 118 expression keys ≥ full FACS coverage |
| Hands | ✅ 30 finger bones |
| Body animation | ✅ standard humanoid FK skeleton, retargetable |
| GLB export | ✅ meshes/bones/blendshapes/textures all GLB-representable. Caveats: GLB has no shape-key *ranges* (our -1..1 becomes 0..1 pairs or is baked before export) and no cross-mesh key linking (runtime must sync same-named keys) |

## 7. Recommendations (no changes made yet)

1. **Morph abstraction layer (next task):** users see ~20 semantic sliders; an engine mapping translates each into one or more underlying shape key values. Ship the mapping as JSON so Blender, backend, and Three.js all read the same file.
2. **Never expose the 149 animation keys as customization.** Identity = `customization` class only; animation = expression/viseme/corrective classes, driven by the animation system.
3. **Negative-range policy:** decide before GLB export how -1..1 sliders are represented (split pos/neg keys at export is the standard glTF answer).
4. **Eye-follow gap (known, accepted):** `eye_size`/`eye_distance` deform sockets but not eyeball objects. Fix later by mirroring those 2 morphs onto `CC_Base_Eye` (object-level scale/offset or shape keys) before pushing sliders past moderate values.
5. **Material upgrade path:** wire roughness/AO/SSS from the source `textures/` folder into the export material builder (not the template).
6. **Female template:** repeat the exact import + morph-generation procedure on `Neutral_F.Fbx` once the male pipeline is approved end-to-end.
