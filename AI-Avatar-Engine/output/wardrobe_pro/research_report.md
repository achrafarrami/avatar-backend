# Pro Wardrobe — Phase 1 Research Report (Meta reference analysis)

Reference: 7-avatar Meta Avatars lineup (provided image). Target: match this
look with the project's meta (toon) bases.

## Silhouette
- Bodies ~5.5–6 heads tall, soft rounded volumes, no hard muscle definition.
- Garments read as **clean closed volumes** with gentle looseness: cloth
  stands off the body 1–3 cm at the torso, tapers to near-contact at
  shoulders, cuffs, waistbands.
- Hems flare slightly outward (hoodie-dress, skirt, abaya) — silhouette
  widens toward the bottom; nothing hugs the legs under a skirt.
- Layering is real geometry: scarf over top, jacket over tee, hijab over
  shoulders — each layer has its own visible edge.

## Topology density (inferred from curvature)
- Smooth continuous curvature with zero visible faceting at ~600 px avatar
  height → ≈ 2–5k triangles per garment equivalent. Even density; loops
  follow openings (neck, cuff, hem) and limb axes.

## Cloth thickness
- Thickness is **only shown at openings**: rolled collar rims, folded cuffs,
  visible hem lips (~1 cm at this stylization). Interiors are never seen.
  Jacket lapels and hood rolls are the thickest reads (~2–3 cm).

## Wrinkle style
- Almost none. A few **broad, soft folds**: one elbow crease per sleeve,
  2–3 vertical pleats on skirts, soft bunching where the hijab meets the
  shoulder. No micro-wrinkles, no noise. Shading (AO in folds) does the work.

## Edge flow & seams
- Seams appear as **subtle grooves + color breaks**, not geometry noise:
  button plackets, jeans waistband, hoodie kangaroo pocket outline,
  lace-up detail on the hoodie-dress. Support loops at every opening.

## Bevels
- Every visible edge is rounded — cuff lips, sole edges, brims, lapel edges
  (~0.5–1 cm radius). Nothing is knife-sharp.

## Proportions (garment-specific)
- Tops end at high hip; the hoodie-dress at mid-thigh; abaya at ankle.
- Sleeves have volume: blouse sleeves puff slightly then gather at cuffs.
- Pants: straight, slightly tapered, break at the ankle; jeans show cuffs.
- Shoes are simplified: one-piece uppers, thick soles, no individual laces
  (lace area is a smooth panel; sometimes painted detail).

## Color palette (sampled)
- Dusty rose `#c98d80`, terracotta `#b0563b`, deep plaid red `#8f3a34`,
  navy suit `#3a4a68`, denim `#4a5a78`, charcoal `#2e2f35`, cream `#e5ded2`,
  slate abaya `#5c6274`, blush hijab `#e8b4ac`, leather black `#26262a`,
  forest, mustard accents. Muted, mid-saturation, warm-leaning.

## Material style
- **Matte fabric**: roughness 0.75–0.92, no metallic, very soft speculars.
- Subtle roughness variation (woven feel), gentle sheen on knits.
- Leather jacket: roughness ~0.45 with soft highlights. Shoes: semi-matte.
- Ambient occlusion in folds and where layers meet — soft, never black.
- Prints exist (plaid, floral) as albedo only; geometry stays clean.

## Build implications (what the factory must do)
1. Relax body-derived shells hard (kill anatomy detail), then inflate with a
   per-garment drape profile; loft skirts/dresses as ring surfaces instead
   of inflating legs.
2. Construct rolled trim geometry at every opening (collar/cuff/hem/brim).
3. Add the 3–4 signature details per garment (pocket, placket+buttons,
   waistband, lapels, sole, hood roll) — nothing more.
4. Crease/groove seams; bevel all visible edges; weighted normals.
5. Matte PBR with slight roughness noise + sheen; baked vertex-color AO;
   reference palette above.
6. 1.5–5k tris per garment; quad-dominant; subdivision-safe.
