/**
 * Avatar Sandbox — UI layer.
 * Owns the DOM panels; all 3D work lives in SandboxViewer (viewer.js).
 * The identity tab consumes morph_definitions.json — the same file the
 * Blender pipeline uses — so param semantics can never drift between tools.
 */
import { SandboxViewer } from "./viewer.js";

const $ = (sel) => document.querySelector(sel);

const viewer = new SandboxViewer($("#canvas3d"));
let morphDefs = null;          // morph_definitions.json
let identityParams = {};       // user params, 0..1
let assetManifest = null;
let description = null;        // current avatar description

// ---------------------------------------------------------------- tabs
document.querySelectorAll("#tabs button").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll("#tabs button").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
    btn.classList.add("active");
    $(`#tab-${btn.dataset.tab}`).classList.add("active");
  });
});

// ---------------------------------------------------------------- loading
async function loadAvatar(url) {
  const loading = $("#loading");
  loading.classList.remove("hidden");
  try {
    description = await viewer.loadAvatar(url, (ev) => {
      if (ev.total) {
        const pct = ((ev.loaded / ev.total) * 100).toFixed(0);
        $("#loading-text").textContent = `Loading avatar… ${pct}%`;
      }
    });
    buildInspector();
    buildMorphSliders();
    applyIdentity(); // re-apply current params to the fresh avatar
  } finally {
    loading.classList.add("hidden");
  }
}

$("#avatar-select").addEventListener("change", (e) => loadAvatar(e.target.value));
$("#btn-frame-face").addEventListener("click", () => viewer.frameFace());
$("#btn-frame-body").addEventListener("click", () => viewer.frameBody());

// ---------------------------------------------------------------- inspector
function buildInspector() {
  const el = $("#tab-inspector");
  const d = description;
  const meshRows = d.meshes.map((m) => `
    <div class="item">
      <span class="name">${m.name}${m.skinned ? '<span class="badge">skinned</span>' : ""}</span>
      <span class="meta">${m.vertices.toLocaleString()} verts · ${m.morphTargets} morphs<br>${m.materials.join(", ")}</span>
    </div>`).join("");

  const matRows = d.materials.map((m) => `
    <div class="item">
      <span class="name">${m.name}</span>
      <span class="meta">${m.type}${m.maps.length ? " · " + m.maps.join(", ") : ""}</span>
    </div>`).join("");

  el.innerHTML = `
    <h3 class="section">Meshes (${d.meshes.length})</h3>
    <div class="tree">${meshRows}</div>
    <h3 class="section">Materials (${d.materials.length})</h3>
    <div class="tree">${matRows}</div>
    <h3 class="section">Skeleton (${d.boneCount} bones)</h3>
    <details class="group"><summary>Bone hierarchy</summary>
      <div class="body bone-tree">${d.boneTree.join("\n")}</div>
    </details>
    <h3 class="section">Blendshapes</h3>
    <p class="hint">${d.morphNames.length} unique morph target names across all meshes.
    Same-named targets are driven together (engine sync contract).</p>`;
}

// ---------------------------------------------------------------- morphs
const CATEGORY_RULES = [
  ["Identity (custom)", (n) => morphDefs && isIdentityKey(n)],
  ["Visemes", (n) => n.startsWith("V_")],
  ["Brow", (n) => n.startsWith("Brow_")],
  ["Eye", (n) => n.startsWith("Eye_") || n.startsWith("Eyelash_")],
  ["Nose", (n) => n.startsWith("Nose_")],
  ["Cheek", (n) => n.startsWith("Cheek_")],
  ["Mouth", (n) => n.startsWith("Mouth_")],
  ["Jaw", (n) => n.startsWith("Jaw_")],
  ["Tongue", (n) => n.startsWith("Tongue_")],
  ["Head / Neck (corrective)", (n) => n.startsWith("Head_") || n.startsWith("Neck_")],
  ["Tearline / Occlusion fitting", (n) => n.startsWith("TL ") || n.startsWith("EO ")],
  ["Other", () => true],
];

function isIdentityKey(name) {
  for (const spec of Object.values(morphDefs.params))
    for (const t of spec.targets)
      if (t.shape_key === name) return true;
  return false;
}

function buildMorphSliders() {
  const el = $("#tab-morphs");
  el.innerHTML = `
    <input type="text" id="morph-search" placeholder="Filter blendshapes…">
    <div class="row"><button class="btn" id="btn-reset-morphs">Reset all to 0</button></div>
    <div id="morph-groups"></div>`;

  const groups = new Map();
  for (const name of description.morphNames) {
    const cat = CATEGORY_RULES.find(([, test]) => test(name))[0];
    if (!groups.has(cat)) groups.set(cat, []);
    groups.get(cat).push(name);
  }

  const container = $("#morph-groups");
  for (const [cat, names] of groups) {
    const details = document.createElement("details");
    details.className = "group";
    details.innerHTML = `<summary>${cat}<span class="badge">${names.length}</span></summary>`;
    const body = document.createElement("div");
    body.className = "body";
    const isIdentity = cat.startsWith("Identity");
    for (const name of names.sort()) {
      const row = document.createElement("div");
      row.className = "slider-row";
      row.dataset.morph = name.toLowerCase();
      const min = isIdentity ? -1 : 0;
      row.innerHTML = `
        <label title="${name}">${name}</label>
        <input type="range" min="${min}" max="1" step="0.01" value="0">
        <span class="val">0.00</span>`;
      const slider = row.querySelector("input");
      const val = row.querySelector(".val");
      slider.addEventListener("input", () => {
        const v = parseFloat(slider.value);
        viewer.setMorph(name, v);
        val.textContent = v.toFixed(2);
      });
      body.appendChild(row);
    }
    details.appendChild(body);
    container.appendChild(details);
  }

  $("#btn-reset-morphs").addEventListener("click", () => {
    viewer.resetAllMorphs();
    container.querySelectorAll("input[type=range]").forEach((s) => {
      s.value = 0;
      s.closest(".slider-row").querySelector(".val").textContent = "0.00";
    });
  });

  $("#morph-search").addEventListener("input", (e) => {
    const q = e.target.value.trim().toLowerCase();
    container.querySelectorAll(".slider-row").forEach((row) => {
      row.style.display = !q || row.dataset.morph.includes(q) ? "" : "none";
    });
    container.querySelectorAll("details.group").forEach((g) => {
      const any = [...g.querySelectorAll(".slider-row")].some((r) => r.style.display !== "none");
      g.style.display = any ? "" : "none";
      if (q) g.open = true;
    });
  });
}

// ---------------------------------------------------------------- identity
function computeKeyValues(params) {
  const neutral = morphDefs.param_space.neutral;
  const out = {};
  for (const [name, value] of Object.entries(params)) {
    const spec = morphDefs.params[name];
    if (!spec) continue;
    const centered = (Math.min(1, Math.max(0, value)) - neutral) * 2;
    for (const t of spec.targets)
      out[t.shape_key] = (out[t.shape_key] || 0) + centered * t.weight;
  }
  return out;
}

function applyIdentity() {
  if (!morphDefs) return;
  // zero identity keys first, then apply combined values
  for (const spec of Object.values(morphDefs.params))
    for (const t of spec.targets) viewer.setMorph(t.shape_key, 0);
  const keyValues = computeKeyValues(identityParams);
  for (const [key, v] of Object.entries(keyValues))
    viewer.setMorph(key, Math.min(1, Math.max(-1, v)));
}

function syncIdentityUI({ skipJson = false, skipSliders = false } = {}) {
  if (!skipJson) {
    $("#identity-json").value = JSON.stringify(identityParams, null, 2);
    $("#identity-json").classList.remove("invalid");
  }
  if (!skipSliders) {
    document.querySelectorAll("#identity-sliders .slider-row").forEach((row) => {
      const p = row.dataset.param;
      const v = identityParams[p] ?? 0.5;
      row.querySelector("input").value = v;
      row.querySelector(".val").textContent = Number(v).toFixed(2);
    });
  }
}

function buildIdentityTab() {
  const el = $("#tab-identity");
  el.innerHTML = `
    <p class="hint">Semantic identity parameters (0–1, <b>0.5 = neutral</b>).
    Translated through <code>morph_definitions.json</code> — identical math to
    the Blender exporter. Users never see raw blendshapes.</p>
    <div class="row">
      <button class="btn" id="btn-identity-reset">Reset (all 0.5)</button>
      <button class="btn" id="btn-identity-random">Randomize</button>
    </div>
    <div id="identity-sliders"></div>
    <h3 class="section">Live JSON editor</h3>
    <p class="hint">Edit and the avatar updates as soon as the JSON parses.</p>
    <textarea id="identity-json" rows="12" spellcheck="false"></textarea>`;

  const slidersEl = $("#identity-sliders");
  const categories = new Map();
  for (const [pname, spec] of Object.entries(morphDefs.params)) {
    if (!categories.has(spec.category)) categories.set(spec.category, []);
    categories.get(spec.category).push([pname, spec]);
  }

  for (const [cat, entries] of categories) {
    const details = document.createElement("details");
    details.className = "group";
    details.open = true;
    details.innerHTML = `<summary>${cat}<span class="badge">${entries.length}</span></summary>`;
    const body = document.createElement("div");
    body.className = "body";
    for (const [pname, spec] of entries) {
      const row = document.createElement("div");
      row.className = "slider-row";
      row.dataset.param = pname;
      row.innerHTML = `
        <label title="${spec.description}">${spec.label}</label>
        <input type="range" min="0" max="1" step="0.01" value="0.5">
        <span class="val">0.50</span>`;
      const slider = row.querySelector("input");
      slider.addEventListener("input", () => {
        identityParams[pname] = parseFloat(slider.value);
        row.querySelector(".val").textContent = slider.value;
        applyIdentity();
        syncIdentityUI({ skipSliders: true });
      });
      body.appendChild(row);
    }
    details.appendChild(body);
    slidersEl.appendChild(details);
  }

  $("#identity-json").addEventListener("input", (e) => {
    try {
      const parsed = JSON.parse(e.target.value);
      identityParams = parsed;
      e.target.classList.remove("invalid");
      applyIdentity();
      syncIdentityUI({ skipJson: true });
    } catch {
      e.target.classList.add("invalid");
    }
  });

  $("#btn-identity-reset").addEventListener("click", () => {
    identityParams = Object.fromEntries(Object.keys(morphDefs.params).map((k) => [k, 0.5]));
    applyIdentity();
    syncIdentityUI();
  });

  $("#btn-identity-random").addEventListener("click", () => {
    identityParams = Object.fromEntries(Object.keys(morphDefs.params)
      .map((k) => [k, Math.round((0.5 + (Math.random() - 0.5) * 0.7) * 100) / 100]));
    applyIdentity();
    syncIdentityUI();
  });

  identityParams = Object.fromEntries(Object.keys(morphDefs.params).map((k) => [k, 0.5]));
  syncIdentityUI();
}

// ---------------------------------------------------------------- display
function buildDisplayTab() {
  const el = $("#tab-display");
  const toggles = [
    ["skeleton", "Skeleton overlay", (v) => viewer.setSkeleton(v)],
    ["wireframe", "Wireframe", (v) => viewer.setWireframe(v)],
    ["normals", "Vertex normals", (v) => viewer.setNormals(v)],
    ["uv", "UV debug (checker)", (v) => viewer.setUVDebug(v)],
    ["grid", "Ground grid", (v) => (viewer.grid.visible = v)],
  ];
  el.innerHTML = `<h3 class="section">Debug overlays</h3>
    <div id="display-toggles"></div>
    <p class="hint">Vertex normals draw one line per vertex (~19k lines) — expect a
    small FPS dip while enabled.</p>`;
  const wrap = $("#display-toggles");
  for (const [id, label, fn] of toggles) {
    const row = document.createElement("div");
    row.className = "toggle-row";
    row.innerHTML = `
      <label for="tg-${id}">${label}</label>
      <span class="switch">
        <input type="checkbox" id="tg-${id}" ${id === "grid" ? "checked" : ""}>
        <span class="track"></span>
      </span>`;
    row.querySelector(".track").addEventListener("click", () => {
      const cb = row.querySelector("input");
      cb.checked = !cb.checked;
      fn(cb.checked);
    });
    wrap.appendChild(row);
  }
}

// ---------------------------------------------------------------- assets
function buildAssetsTab() {
  const el = $("#tab-assets");
  el.innerHTML = `<div id="asset-cats"></div>
    <h3 class="section">Attached</h3>
    <div id="attached-list"><p class="hint">Nothing attached.</p></div>
    <p class="hint">To add assets: drop .glb files into
    <code>public/assets/&lt;category&gt;/</code> and register them in
    <code>public/assets_manifest.json</code>.</p>`;

  const cats = $("#asset-cats");
  for (const [key, cat] of Object.entries(assetManifest.categories)) {
    const details = document.createElement("details");
    details.className = "group";
    details.open = cat.items.length > 0;
    details.innerHTML = `<summary>${cat.label}<span class="badge">${cat.items.length}</span></summary>`;
    const body = document.createElement("div");
    body.className = "body";
    if (cat.items.length === 0) {
      body.innerHTML = `<p class="hint">No ${cat.label.toLowerCase()} yet.</p>`;
    }
    for (const item of cat.items) {
      const row = document.createElement("div");
      row.className = "asset-item";
      row.innerHTML = `<span class="name">${item.name}</span>`;
      const btn = document.createElement("button");
      btn.className = "btn";
      btn.textContent = "Attach";
      btn.addEventListener("click", async () => {
        btn.disabled = true;
        try {
          await viewer.attachAsset(item.file, item.name, cat.attach_to);
          renderAttached();
        } finally {
          btn.disabled = false;
        }
      });
      row.appendChild(btn);
      body.appendChild(row);
    }
    details.appendChild(body);
    cats.appendChild(details);
  }
}

function renderAttached() {
  const list = $("#attached-list");
  if (viewer.attachments.length === 0) {
    list.innerHTML = `<p class="hint">Nothing attached.</p>`;
    return;
  }
  list.innerHTML = "";
  for (const a of viewer.attachments) {
    const row = document.createElement("div");
    row.className = "asset-item";
    row.innerHTML = `<span class="name">${a.name} <span class="badge">${a.boneName || "root"}</span></span>`;
    const btn = document.createElement("button");
    btn.className = "btn danger";
    btn.textContent = "Remove";
    btn.addEventListener("click", () => { viewer.removeAttachment(a.id); renderAttached(); });
    row.appendChild(btn);
    list.appendChild(row);
  }
}

// ---------------------------------------------------------------- export
function download(blob, filename) {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 5000);
}

function buildExportTab() {
  const el = $("#tab-export");
  el.innerHTML = `
    <h3 class="section">Export current state</h3>
    <div class="row">
      <button class="btn primary" id="btn-export-glb">Download GLB</button>
      <button class="btn" id="btn-export-json">Download identity JSON</button>
    </div>
    <p class="hint">GLB = the scene as currently posed/morphed (incl. attachments),
    re-exported by Three.js. For production avatars use the Blender exporter
    (<code>export_avatar_glb.py</code>) which bakes identity properly.</p>
    <p class="hint">Identity JSON matches the format the AI will output and
    <code>export_avatar_glb.py --params</code> accepts.</p>
    <h3 class="section">Resolved blendshape values</h3>
    <textarea id="resolved-keys" rows="10" readonly spellcheck="false"></textarea>`;

  $("#btn-export-glb").addEventListener("click", async () => {
    const buf = await viewer.exportGLB();
    download(new Blob([buf], { type: "model/gltf-binary" }), "avatar_sandbox_export.glb");
  });
  $("#btn-export-json").addEventListener("click", () => {
    download(new Blob([JSON.stringify(identityParams, null, 2)], { type: "application/json" }),
      "avatar_params.json");
  });

  setInterval(() => {
    const ta = $("#resolved-keys");
    if (ta && $("#tab-export").classList.contains("active"))
      ta.value = JSON.stringify(computeKeyValues(identityParams), null, 2);
  }, 500);
}

// ---------------------------------------------------------------- boot
// Console access for debugging: window.sandbox.viewer, .params, .defs
window.sandbox = {
  viewer,
  get params() { return identityParams; },
  get defs() { return morphDefs; },
};

(async function boot() {
  [morphDefs, assetManifest] = await Promise.all([
    fetch("morph_definitions.json").then((r) => r.json()),
    fetch("assets_manifest.json").then((r) => r.json()),
  ]);
  buildIdentityTab();
  buildDisplayTab();
  buildAssetsTab();
  buildExportTab();
  await loadAvatar($("#avatar-select").value);
})();
