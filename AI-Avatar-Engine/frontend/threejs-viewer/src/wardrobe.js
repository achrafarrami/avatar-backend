/**
 * WardrobeManager — the single, generic asset-equipment engine.
 *
 * There are no per-category "hair manager / beard manager / ..." classes:
 * every category (slot) is data in wardrobe/catalog.json, and the two attach
 * behaviors are selected by item metadata:
 *   - attach_type "bone"    → rigid parent to a bone (glasses, hats, watch…)
 *   - attach_type "skinned" → re-bound to the avatar skeleton by bone name
 *                             (hair, beard, clothes… deform with the body)
 *
 * One item per slot; equipping replaces, equip(slot, null) removes.
 * Colors apply to the materials listed in item.colorable_materials.
 *
 * Per-style fit (added for Meta-avatar support): an item.json may carry a
 *   "styles": { "meta": { "glb": "...", "offset": [x,y,z], "scale": s,
 *                          "attach_to": "...", "colorable_materials": [...] } }
 * block. setStyle() selects which one applies; equip() reads it:
 *   - "glb"      → load this file instead of the item's default `file`
 *                  (a properly-fitted mesh, e.g. a re-scaled clothing item —
 *                  used when a runtime offset/scale isn't enough)
 *   - "offset"/"scale" → a lightweight per-style nudge (e.g. hair/hats/
 *                  glasses sized for the realistic head, nudged to sit on a
 *                  bigger Meta head) WITHOUT duplicating a GLB. offset is
 *                  real-world METERS in bone-world space. For attach_type
 *                  "bone" items this is passed straight into
 *                  viewer.attachAsset(url, name, boneName, offset, scale) so
 *                  it can be folded into the bone's inverse-rest-transform
 *                  matrix construction — mutating the attachment root
 *                  AFTER that placement would land in the bone's local
 *                  frame (scaled ~100x by the armature's 0.01 import scale
 *                  and rotated by the bone's rest orientation), not world
 *                  meters. attach_type "skinned" holders parent directly to
 *                  the (identity-transform) avatar root, so a post-hoc
 *                  nudge on the attachment root IS already world-meters —
 *                  see _applyFitPostHoc().
 *   - any other key (attach_to, colorable_materials, gender, ...) →
 *                  plain metadata override for that style
 * Items with no "styles" block (everything as of this patch, until
 * hair-assets/clothing publish real fits) are completely unaffected — this
 * stays true to "only the catalog changes, never this code": callers that
 * omit offset/scale get exactly today's attachAsset()/attachSkinned() output.
 */
export class WardrobeManager {
  constructor(viewer) {
    this.viewer = viewer;
    this.catalog = null;
    this.equipped = {};   // slot -> {itemId, attachmentId, color}
    this.style = "realistic"; // "realistic" | "meta" — set via setStyle();
                               // only changes equip() resolution, see _resolved()
  }

  async init(catalogUrl = "wardrobe/catalog.json") {
    this.catalog = await fetch(catalogUrl).then((r) => r.json());
    return this.catalog;
  }

  /** Switch the active avatar style. Additive/forward-looking only — items
   * without a "styles" override (every item today) are completely unaffected.
   * Call reapply() (or let loadAvatar() do it via main.js) afterwards to
   * re-resolve anything currently equipped against the new style. */
  setStyle(style) {
    this.style = style;
  }

  itemsForSlot(slot) {
    return this.catalog.items.filter((i) => i.slot === slot);
  }

  item(itemId) {
    return this.catalog.items.find((i) => i.id === itemId) || null;
  }

  /** Merge an item's base fields with its optional per-style override:
   *   item.styles = { meta: { glb, offset, scale, attach_to,
   *                            colorable_materials, ... } }
   * "glb" replaces the loaded file (mapped onto `file` below — the item's
   * own field is still called `file`, "glb" is just the override's spelling
   * per the schema doc above). "offset"/"scale" are pulled out separately
   * since they're not item metadata fields — they're applied to the
   * attachment root post-placement in equip(). Any other key (attach_to,
   * colorable_materials, gender, ...) is a plain metadata override.
   * Defensive by construction: no "styles" block (the case for every item as
   * of this patch) means this returns the item unchanged plus null fit. */
  _resolved(meta) {
    const override = meta.styles?.[this.style];
    if (!override) return { meta, fit: null };
    const { glb, offset, scale, ...rest } = override;
    return {
      meta: { ...meta, ...rest, file: glb ?? meta.file },
      fit: (offset || scale != null) ? { offset: offset || null, scale: scale ?? null } : null,
    };
  }

  async equip(slot, itemId) {
    const prev = this.equipped[slot];
    if (prev) {
      this.viewer.removeAttachment(prev.attachmentId);
      delete this.equipped[slot];
    }
    if (!itemId) return null;               // "None" → slot stays empty

    const rawMeta = this.item(itemId);
    if (!rawMeta || rawMeta.slot !== slot) throw new Error(`Unknown item ${itemId} for slot ${slot}`);
    const { meta, fit } = this._resolved(rawMeta);

    const url = `wardrobe/${meta.file}`;
    let attachmentId;
    if (meta.attach_type === "skinned") {
      // holder parents directly to the (identity-transform) avatar root, not
      // to a bone — no rest-transform to cancel, so a post-hoc nudge is
      // already in world-meters space. Verified fine as-is.
      attachmentId = await this.viewer.attachSkinned(url, meta.id);
      if (fit) this._applyFitPostHoc(attachmentId, fit);
    } else {
      // bone-attached items: attachAsset() bakes the bone's INVERSE rest
      // transform (cancels the armature's ~0.01 import scale + rest
      // rotation) into root's local matrix. A post-hoc root.position/scale
      // mutation here would land in that same rest-transform-warped local
      // frame instead of world meters — offset/scale MUST be passed in so
      // attachAsset can fold them into its own matrix construction, before
      // the inverse is applied. (This was the bug hair-assets caught: a
      // 0.05m post-hoc offset only moved ~0.0005m in world space, ~100x
      // undershoot from the bone's 0.01 scale, and slightly axis-mixed by
      // its rest rotation.)
      attachmentId = await this.viewer.attachAsset(
        url, meta.id, meta.attach_to, fit?.offset ?? null, fit?.scale ?? 1);
    }

    this.equipped[slot] = { itemId, attachmentId, color: prev?.color || null };
    if (prev?.color) this.setColor(slot, prev.color);   // keep color across swaps
    return attachmentId;
  }

  /** Post-placement offset/scale nudge for attachments whose root already
   * lives in world-meters space (skinned holders only — see equip()). */
  _applyFitPostHoc(attachmentId, fit) {
    const attachment = this.viewer.attachments.find((a) => a.id === attachmentId);
    if (!attachment) return;
    if (fit.offset) {
      const [dx, dy, dz] = fit.offset;
      attachment.root.position.x += dx;
      attachment.root.position.y += dy;
      attachment.root.position.z += dz;
    }
    if (fit.scale != null) attachment.root.scale.multiplyScalar(fit.scale);
  }

  setColor(slot, hex) {
    const entry = this.equipped[slot];
    if (!entry) return;
    const { meta } = this._resolved(this.item(entry.itemId));
    if (!meta.colorable_materials.length) return;
    const attachment = this.viewer.attachments.find((a) => a.id === entry.attachmentId);
    if (!attachment) return;
    attachment.root.traverse((o) => {
      if (!o.isMesh && !o.isSkinnedMesh) return;
      const mats = Array.isArray(o.material) ? o.material : [o.material];
      for (const m of mats) {
        if (meta.colorable_materials.includes(m.name)) m.color.set(hex);
      }
    });
    entry.color = hex;
  }

  /** Re-equip the whole outfit (after the avatar GLB was swapped/reloaded). */
  async reapply() {
    const outfit = Object.entries(this.equipped)
      .map(([slot, e]) => ({ slot, itemId: e.itemId, color: e.color }));
    this.equipped = {};
    for (const { slot, itemId, color } of outfit) {
      await this.equip(slot, itemId);
      if (color) this.setColor(slot, color);
    }
  }

  /** Serializable outfit state, e.g. for export or future avatar params. */
  state() {
    return Object.fromEntries(Object.entries(this.equipped)
      .map(([slot, e]) => [slot, { item: e.itemId, color: e.color }]));
  }
}
