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
 * The same manager will serve stylized avatars later — only the catalog
 * (and per-style asset variants) changes, never this code.
 */
export class WardrobeManager {
  constructor(viewer) {
    this.viewer = viewer;
    this.catalog = null;
    this.equipped = {};   // slot -> {itemId, attachmentId, color}
  }

  async init(catalogUrl = "wardrobe/catalog.json") {
    this.catalog = await fetch(catalogUrl).then((r) => r.json());
    return this.catalog;
  }

  itemsForSlot(slot) {
    return this.catalog.items.filter((i) => i.slot === slot);
  }

  item(itemId) {
    return this.catalog.items.find((i) => i.id === itemId) || null;
  }

  async equip(slot, itemId) {
    const prev = this.equipped[slot];
    if (prev) {
      this.viewer.removeAttachment(prev.attachmentId);
      delete this.equipped[slot];
    }
    if (!itemId) return null;               // "None" → slot stays empty

    const meta = this.item(itemId);
    if (!meta || meta.slot !== slot) throw new Error(`Unknown item ${itemId} for slot ${slot}`);

    const url = `wardrobe/${meta.file}`;
    const attachmentId = meta.attach_type === "skinned"
      ? await this.viewer.attachSkinned(url, meta.id)
      : await this.viewer.attachAsset(url, meta.id, meta.attach_to);

    this.equipped[slot] = { itemId, attachmentId, color: prev?.color || null };
    if (prev?.color) this.setColor(slot, prev.color);   // keep color across swaps
    return attachmentId;
  }

  setColor(slot, hex) {
    const entry = this.equipped[slot];
    if (!entry) return;
    const meta = this.item(entry.itemId);
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
