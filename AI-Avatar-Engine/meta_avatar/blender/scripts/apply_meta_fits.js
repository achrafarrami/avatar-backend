// One-off: write the T3 Meta wardrobe-fit "styles.meta" overrides into the
// canonical item.json files (assets/shared) and their sandbox mirror
// (frontend/threejs-viewer/public/wardrobe), plus the matching entries
// embedded in both catalog.json copies (the actual runtime source read by
// WardrobeManager.init()). Values are in the three.js/glTF axis convention
// (X same, Y=Blender Z, Z=-Blender Y) and world meters, applied by
// WardrobeManager.equip() post-placement per the approved schema.
const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..", "..", "..");
const SHARED = path.join(ROOT, "assets", "shared");
const SANDBOX = path.join(ROOT, "frontend", "threejs-viewer", "public", "wardrobe");

const FITS = {
  hair_w01: { offset: [0, -0.041968, -0.003986], scale: 1.5702 },
  hair_w03: { offset: [0, -0.041968, -0.003986], scale: 1.5702 },
  hair_w07: { offset: [0, -0.041968, -0.003986], scale: 1.5702 },
  hair_w09: { offset: [0, -0.041968, -0.003986], scale: 1.5702 },
  glasses_round: { offset: [0, -0.011711, -0.002158], scale: 1.447 },
  // T10 (cap-fit-fix, 2026-07-22): re-derived empirically -- the old value
  // (offset [0,-0.033461,-0.006164], scale 1.447) reused compute_fits.py's
  // generic "head_compromise" crown-anchor formula, which assumes the cap's
  // own dome-apex landmark coincides with the HEAD mesh's own crown. It
  // doesn't: measured directly in Blender (attach_bone()'s exact transform,
  // vertex-baked scale then Translation(head_world+offset)), cap.glb's raw
  // local dome-apex vertex sits at local Z=0.254267, ~6cm above where the
  // head-crown-substitution assumed -- scaled 1.447x that pre-existing
  // mismatch amplifies into a ~10.2cm floating gap (reproduced identically
  // in T3's own "fitted" reference renders, so this was never actually a
  // transform-code bug -- see qa_report.md's T9 section). New value derived
  // from the cap's OWN measured local geometry (dome apex local Z=0.254267,
  // brim local Z=0.143267) solved jointly against both genders' measured
  // scalp-crown Z and CC_Base_Eye bone Z (brim-above-eyebrow target), scale
  // reduced from 1.447 to 1.371101 (the old width-ratio scale over-grows the
  // cap's own vertical brim-to-dome span past the available crown-to-brow
  // room on either template -- a single uniform scale can't satisfy both
  // head-width coverage and vertical clearance simultaneously, so this
  // trades a little width margin for a correct vertical fit). Verified via
  // render: dome touches scalp (gap 1.69cm male / 0.71cm female, both was
  // 9-10cm), brim clears eyebrows on both genders, no clipping. See
  // meta_avatar/documentation/wardrobe_fits.json's "cap_empirical" entry for
  // the full formula + measured inputs.
  cap: { offset: [0, -0.099505, 0.008696], scale: 1.371101 },
  watch: { offset: [0, -0.000279, -0.003716], scale: 1.0591 },
  beard_short: { offset: [0, -0.135, 0.05], scale: 1.0294 },
};

const ITEM_JSON_PATHS = {
  hair_w01: "hair/hair_w01/item.json",
  hair_w03: "hair/hair_w03/item.json",
  hair_w07: "hair/hair_w07/item.json",
  hair_w09: "hair/hair_w09/item.json",
  glasses_round: "glasses/glasses_round/item.json",
  cap: "hats/cap/item.json",
  watch: "accessories/watch/item.json",
  beard_short: "beards/beard_short/item.json",
};

function addStyles(obj, id) {
  const fit = FITS[id];
  if (!fit) return obj;
  return { ...obj, styles: { meta: { offset: fit.offset, scale: fit.scale } } };
}

let changed = [];

for (const [id, rel] of Object.entries(ITEM_JSON_PATHS)) {
  for (const base of [SHARED, SANDBOX]) {
    const p = path.join(base, rel);
    if (!fs.existsSync(p)) { console.warn(`MISSING ${p}`); continue; }
    const data = JSON.parse(fs.readFileSync(p, "utf8"));
    const updated = addStyles(data, id);
    fs.writeFileSync(p, JSON.stringify(updated, null, 2) + "\n");
    changed.push(p);
  }
}

for (const base of [SHARED, SANDBOX]) {
  const p = path.join(base, "catalog.json");
  const cat = JSON.parse(fs.readFileSync(p, "utf8"));
  let n = 0;
  cat.items = cat.items.map((item) => {
    if (FITS[item.id]) { n++; return addStyles(item, item.id); }
    return item;
  });
  fs.writeFileSync(p, JSON.stringify(cat, null, 2) + "\n");
  changed.push(p);
  console.log(`updated ${n} items in ${p}`);
}

console.log(`done, touched ${changed.length} files`);
