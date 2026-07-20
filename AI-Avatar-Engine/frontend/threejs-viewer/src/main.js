/**
 * Avatar Sandbox — UI layer.
 * Owns the DOM panels; all 3D work lives in SandboxViewer (viewer.js).
 * The identity tab consumes morph_definitions.json — the same file the
 * Blender pipeline uses — so param semantics can never drift between tools.
 */
import { SandboxViewer } from "./viewer.js";
import { WardrobeManager } from "./wardrobe.js";

const $ = (sel) => document.querySelector(sel);

const viewer = new SandboxViewer($("#canvas3d"));
const wardrobe = new WardrobeManager(viewer);
let morphDefs = null;          // morph_definitions.json
let identityParams = {};       // user params, 0..1
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
    await wardrobe.reapply(); // re-equip outfit on the fresh avatar
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

// ---------------------------------------------------------------- photos
const ANALYZER_URL = "http://127.0.0.1:8100";

// semantic appearance labels (AI output) -> wardrobe catalog ids / palette hex
const APPEARANCE_MAP = {
  hairStyle: { pigtails: "hair_w01", high_ponytail: "hair_w02",
               long: "hair_w03", side_sweep: "hair_w04", updo: "hair_w05",
               low_bun: "hair_w06", spiky: "hair_w07", pixie: "hair_w08",
               bob: "hair_w09", side_ponytail: "hair_w10",
               bald: null, short: null, none: null },
  beardStyle: { short: "beard_short", goatee: "goatee", none: null },
  glasses: { round: "glasses_round", square: "glasses_square", none: null },
  hairColor: { black: "#0f0f12", dark_brown: "#3b2a1e", brown: "#6a4a2f",
               chestnut: "#55371f", auburn: "#7a3f24", light_brown: "#8c6239",
               dark_blonde: "#a67c48", blonde: "#c9a06a", platinum: "#e6d6b8",
               gray: "#9a9ea6", white: "#e8e6e2", red: "#a34a26" },
};

const AVATAR_URLS = { male: "avatars/sandbox_male.glb",
                      female: "avatars/sandbox_female.glb" };

/** Apply an /analyze response through the EXISTING engine paths:
 * gender -> avatar base, geometry -> identity params,
 * appearance -> wardrobe equips. */
async function applyPhotoResult(res) {
  // switch the avatar base if the detected gender doesn't match it
  const gender = res.parameters?.gender;
  const sel = $("#avatar-select");
  if (gender && AVATAR_URLS[gender] && sel.value !== AVATAR_URLS[gender]) {
    sel.value = AVATAR_URLS[gender];
    await loadAvatar(sel.value);
  }

  identityParams = { ...identityParams, ...res.engine_params };
  applyIdentity();
  syncIdentityUI();

  const app = res.parameters?.appearance || {};
  const hairId = APPEARANCE_MAP.hairStyle[app.hair?.style];
  if (app.hair?.style != null) await wardrobe.equip("hair", hairId ?? null);
  if (hairId && APPEARANCE_MAP.hairColor[app.hair?.color])
    wardrobe.setColor("hair", APPEARANCE_MAP.hairColor[app.hair.color]);
  const beardId = APPEARANCE_MAP.beardStyle[app.beard?.style];
  if (app.beard?.style != null) await wardrobe.equip("beard", beardId ?? null);
  if (beardId && APPEARANCE_MAP.hairColor[app.beard?.color])
    wardrobe.setColor("beard", APPEARANCE_MAP.hairColor[app.beard.color]);
  if (app.glasses != null)
    await wardrobe.equip("glasses", APPEARANCE_MAP.glasses[app.glasses] ?? null);
}

/** Photo Debug panel: what the analyzer actually saw — stage images
 * (aligned / landmarks / segmentation / hairline / beard), the raw
 * measurements with their confidences and down-weighting factors, and the
 * final parameters with provenance. Rendered only when the Debug checkbox
 * was on for the run. */
function renderPhotoDebug(res) {
  const el = $("#photo-debug");
  const dbg = res.debug;
  const raw = dbg.raw || {};
  const esc = (s) => String(s).replace(/[&<>]/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));

  const IMG_LABELS = {
    front_aligned: "front · aligned", front_normalized: "front · color-normalized",
    front_landmarks: "front · landmarks", front_parsing: "front · segmentation + hairline + beard",
    left_aligned: "left · aligned", left_landmarks: "left · landmarks",
    left_normalized: "left · color-normalized",
    left_profile: "left · silhouette contour",
    right_aligned: "right · aligned", right_landmarks: "right · landmarks",
    right_normalized: "right · color-normalized",
    right_profile: "right · silhouette contour",
    front_face3d: "front · MICA 3D landmarks (front / side)",
  };
  const imgs = Object.entries(dbg.images || {}).map(([fn, url]) => {
    const key = fn.replace(/\.(png|jpe?g)$/, "");
    return `<figure class="dbg-fig"><img src="${url}" loading="lazy">
      <figcaption>${esc(IMG_LABELS[key] || key)}</figcaption></figure>`;
  }).join("");

  const feats = raw.features || {};
  const featRows = Object.entries(feats)
    .sort((a, b) => a[1].confidence - b[1].confidence)
    .map(([name, f]) => {
      const factors = Object.entries(f.factors || {})
        .filter(([, v]) => v < 0.999)
        .map(([k, v]) => `${k}×${v}`).join(" ");
      return `<tr class="${f.confidence < 0.5 ? "low" : ""}">
        <td>${esc(name)}</td><td>${f.value}</td>
        <td>${f.confidence}</td><td>${esc(f.source)}</td>
        <td class="factors">${esc(factors)}</td></tr>`;
    }).join("");

  const meta = res.parameters?.faceMeta || {};
  const paramRows = Object.entries(meta).map(([name, m]) =>
    `<tr class="${m.confidence < 0.4 ? "low" : ""}">
      <td>${esc(name)}</td><td>${m.value}</td>
      <td>${m.confidence}</td><td>${esc(m.source)}</td></tr>`).join("");

  const parsing = raw.parsing || {};
  const ident = raw.identity || {};
  const f3d = raw.face3d || {};
  const idBits = ["left", "right"]
    .filter((t) => ident[`similarity_${t}`] !== undefined)
    .map((t) => `${t}: ${ident[`similarity_${t}`]}`).join(", ");
  const summary = [
    `beard coverage (parser): ${parsing.beard_coverage ?? "n/a"}`,
    `beard (VLM): ${raw.beard_style_used ?? raw.appearance?.beard?.style ?? "n/a"}`,
    `hairline: ${parsing.hairline_y != null
      ? "detected (fh=" + (parsing.forehead_hairline ?? "?") + ")" : "not found"}`,
    `identity similarity — ${idBits || "n/a"}`,
    `3D reconstruction (MICA): ${f3d.available
      ? "on — " + Object.keys(f3d.measurements || {}).length + " beard-robust 3D measurements"
      : "off (" + (f3d.why || "unavailable") + ")"}`,
    `solver: ${(raw.calibration_notes || []).join("; ")}`,
  ].map((s) => `<li>${esc(s)}</li>`).join("");

  el.innerHTML = `
    <h3>Photo Debug</h3>
    <ul class="hint dbg-summary">${summary}</ul>
    <div class="dbg-grid">${imgs}</div>
    <details open><summary>Measurements (${Object.keys(feats).length})</summary>
      <table class="dbg-table"><thead><tr>
        <th>measurement</th><th>value</th><th>conf</th><th>source</th><th>down-weights</th>
      </tr></thead><tbody>${featRows}</tbody></table></details>
    <details><summary>Final parameters</summary>
      <table class="dbg-table"><thead><tr>
        <th>parameter</th><th>value</th><th>conf</th><th>main source</th>
      </tr></thead><tbody>${paramRows}</tbody></table></details>`;
  el.querySelectorAll(".dbg-fig img").forEach((img) =>
    img.addEventListener("click", () =>
      img.closest(".dbg-fig").classList.toggle("wide")));
}

function buildPhotosTab() {
  const el = $("#tab-photos");
  el.innerHTML = `
    <p class="hint">Drop 3 photos and generate the avatar's identity parameters.
    Everything runs locally (<code>ai/photo_analyzer/server.py</code>).</p>
    <div id="photo-drops"></div>
    <div class="row">
      <button class="btn primary" id="btn-generate-avatar" disabled>Generate Avatar</button>
      <button class="btn" id="btn-photos-clear">Clear</button>
      <label class="hint chk"><input type="checkbox" id="chk-photo-debug"> Debug</label>
    </div>
    <div id="photo-status" class="hint"></div>
    <div id="photo-debug"></div>`;

  const slots = [
    ["front", "Front", "face the camera straight on"],
    ["left", "Left ~45–60°", "optional"],
    ["right", "Right ~45–60°", "optional"],
  ];
  const files = { front: null, left: null, right: null };
  const dropsEl = $("#photo-drops");
  const status = $("#photo-status");
  const genBtn = $("#btn-generate-avatar");

  const refresh = () => { genBtn.disabled = !files.front; };

  for (const [key, label, hint] of slots) {
    const zone = document.createElement("div");
    zone.className = "drop-zone";
    zone.innerHTML = `
      <input type="file" accept="image/*" hidden>
      <div class="drop-inner">
        <span class="drop-label">${label}</span>
        <span class="drop-hint">${hint}</span>
      </div>`;
    const input = zone.querySelector("input");
    const inner = zone.querySelector(".drop-inner");

    const setFile = (f) => {
      if (!f || !f.type.startsWith("image/")) return;
      files[key] = f;
      inner.innerHTML = `<img class="drop-preview" src="${URL.createObjectURL(f)}">
        <span class="drop-label">${label}</span>`;
      zone.classList.add("filled");
      refresh();
    };
    zone.addEventListener("click", () => input.click());
    input.addEventListener("change", () => setFile(input.files[0]));
    zone.addEventListener("dragover", (e) => { e.preventDefault(); zone.classList.add("dragging"); });
    zone.addEventListener("dragleave", () => zone.classList.remove("dragging"));
    zone.addEventListener("drop", (e) => {
      e.preventDefault();
      zone.classList.remove("dragging");
      setFile(e.dataTransfer.files[0]);
    });
    dropsEl.appendChild(zone);
    zone.dataset.slot = key;
  }

  $("#btn-photos-clear").addEventListener("click", () => buildPhotosTab());

  // fetch with a hard timeout — a hung request must never freeze the panel
  const fetchT = async (url, opts = {}, ms = 90000) => {
    const ctl = new AbortController();
    const timer = setTimeout(() => ctl.abort(), ms);
    try {
      return await fetch(url, { ...opts, signal: ctl.signal });
    } finally { clearTimeout(timer); }
  };
  const errDetail = async (r) =>
    (await r.json().catch(() => null))?.detail || `HTTP ${r.status}`;

  genBtn.addEventListener("click", async () => {
    genBtn.disabled = true;
    const t0 = performance.now();
    const STEPS = [
      "Detecting gender & appearance — hair / beard / glasses (OpenAI)",
      "Selecting avatar base & equipping wardrobe",
      "Measuring face geometry — MediaPipe, runs locally",
      "Applying identity parameters to the avatar",
    ];
    status.innerHTML = `
      <div class="progress"><div class="progress-fill" id="pa-fill"></div></div>
      <div class="steps" id="pa-steps">${STEPS.map((s, i) =>
        `<div class="step" data-step="${i}"><span class="step-ico">·</span> ${s}
         <span class="step-note"></span></div>`).join("")}</div>
      <div id="pa-elapsed" class="hint"></div>`;
    const fill = $("#pa-fill");
    const setProgress = (pct) => { fill.style.width = pct + "%"; };
    const ICONS = { run: "⏳", done: "✅", warn: "⚠️", skip: "—" };
    const step = (i, state, note = "") => {
      const el = status.querySelector(`.step[data-step="${i}"]`);
      el.querySelector(".step-ico").textContent = ICONS[state];
      el.querySelector(".step-note").textContent = note;
      el.className = `step ${state}`;
    };
    const tick = setInterval(() => {
      $("#pa-elapsed").textContent =
        `elapsed ${((performance.now() - t0) / 1000).toFixed(1)}s`;
    }, 200);

    try {
      // ---- stage 1: gender + appearance (OpenAI, optional) ----------------
      // runs FIRST so the detected gender picks the avatar base AND the
      // matching calibration anchors for the geometry stage
      step(0, "run"); setProgress(10);
      let detectedGender = null;
      let detectedBeard = null;
      const health = await (await fetchT(`${ANALYZER_URL}/health`, {}, 5000)).json();
      if (!health.appearance?.startsWith("enabled")) {
        step(0, "skip", "no API key — geometry only");
        step(1, "skip");
      } else {
        const f1 = new FormData();
        f1.append("front", files.front);
        const r1 = await fetchT(`${ANALYZER_URL}/appearance`,
          { method: "POST", body: f1 }, 60000);
        if (!r1.ok) throw new Error(await errDetail(r1));
        const res1 = await r1.json();
        if (!res1.appearance) {
          step(0, "warn", res1.warning || "no result");
          step(1, "skip");
        } else {
          const a = res1.appearance;
          detectedGender = a.gender;
          detectedBeard = a.beard?.style || null;
          step(0, "done", `${res1.timings?.total_s ?? "?"}s — ${a.gender ?? "?"}` +
            `, hair: ${a.hair?.style ?? "?"}` +
            `${a.beard?.style && a.beard.style !== "none" ? ", beard: " + a.beard.style : ""}` +
            `${a.glasses && a.glasses !== "none" ? ", glasses: " + a.glasses : ""}`);
          step(1, "run"); setProgress(35);
          await applyPhotoResult({ engine_params: {},
            parameters: { gender: a.gender, appearance: a } });
          step(1, "done", detectedGender ? `${detectedGender} base` : "");
        }
      }

      // ---- stage 2: geometry (fast, local) --------------------------------
      // no detection? use whichever base is selected as the gender hint
      const hint = detectedGender ||
        ($("#avatar-select").value.includes("female") ? "female" : "male");
      step(2, "run"); setProgress(55);
      const form = new FormData();
      form.append("front", files.front);
      if (files.left) form.append("left", files.left);
      if (files.right) form.append("right", files.right);
      const wantDebug = $("#chk-photo-debug").checked;
      // beard hint: the VLM ran as a separate request above; without
      // forwarding its beard label, the geometry stage can't down-weight
      // the beard-corrupted lower-face measurements
      const r = await fetchT(
        `${ANALYZER_URL}/analyze?appearance=false&gender=${hint}` +
        (detectedBeard ? `&beard=${detectedBeard}` : "") +
        (wantDebug ? "&debug=true" : ""),
        { method: "POST", body: form }, 120000);
      if (!r.ok) throw new Error(await errDetail(r));
      const res = await r.json();
      if (res.debug) renderPhotoDebug(res);
      const gWarn = res.warnings?.length ? res.warnings.join("; ") : "";
      step(2, gWarn ? "warn" : "done",
        `${res.timings?.total_s ?? "?"}s${gWarn ? " — " + gWarn : ""}`);

      step(3, "run"); setProgress(85);
      await applyPhotoResult(res);
      step(3, "done");
      setProgress(100);
      $("#pa-elapsed").textContent =
        `✅ Done in ${((performance.now() - t0) / 1000).toFixed(1)}s — fine-tune in the Identity tab.`;
    } catch (err) {
      const offline = err.name === "AbortError" || err.message?.includes("fetch");
      $("#pa-elapsed").innerHTML = offline
        ? `❌ Analyzer server not responding. Start it with:<br>
           <code>ai\\.venv\\Scripts\\python ai\\photo_analyzer\\server.py</code>`
        : `❌ ${err.message}`;
      fill.classList.add("error");
    } finally {
      clearInterval(tick);
      genBtn.disabled = !files.front;
    }
  });
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

// ---------------------------------------------------------------- wardrobe
/** Build one slot section: item grid ("None" + thumbnails) + color swatches. */
function buildSlotSection(slot, slotDef) {
  const details = document.createElement("details");
  details.className = "group";
  details.open = true;
  const items = wardrobe.itemsForSlot(slot);
  details.innerHTML = `<summary>${slotDef.label}<span class="badge">${items.length}</span></summary>`;
  const body = document.createElement("div");
  body.className = "body";

  const grid = document.createElement("div");
  grid.className = "item-grid";

  const select = async (itemId, btn) => {
    grid.querySelectorAll(".item-btn").forEach((b) => b.classList.remove("selected"));
    btn.classList.add("selected");
    await wardrobe.equip(slot, itemId);
  };

  const noneBtn = document.createElement("button");
  noneBtn.className = "item-btn selected";
  noneBtn.innerHTML = `<span class="none-x">✕</span><span class="item-label">None</span>`;
  noneBtn.addEventListener("click", () => select(null, noneBtn));
  grid.appendChild(noneBtn);

  for (const item of items) {
    const btn = document.createElement("button");
    btn.className = "item-btn";
    btn.title = item.label;
    btn.innerHTML = `<img src="wardrobe/${item.thumb}" alt="${item.label}">
      <span class="item-label">${item.label}</span>`;
    btn.addEventListener("click", () => select(item.id, btn));
    grid.appendChild(btn);
  }
  body.appendChild(grid);

  if (slotDef.palette) {
    const palette = wardrobe.catalog.palettes[slotDef.palette];
    const swatches = document.createElement("div");
    swatches.className = "swatch-row";
    for (const hex of palette) {
      const sw = document.createElement("button");
      sw.className = "swatch";
      sw.style.background = hex;
      sw.title = hex;
      sw.addEventListener("click", () => {
        swatches.querySelectorAll(".swatch").forEach((s) => s.classList.remove("selected"));
        sw.classList.add("selected");
        wardrobe.setColor(slot, hex);
      });
      swatches.appendChild(sw);
    }
    body.appendChild(swatches);
  }

  details.appendChild(body);
  return details;
}

function buildWardrobeTabs() {
  for (const tab of ["appearance", "clothing", "accessories"]) {
    const el = $(`#tab-${tab}`);
    el.innerHTML = "";
    for (const [slot, slotDef] of Object.entries(wardrobe.catalog.slots)) {
      if (slotDef.tab === tab) el.appendChild(buildSlotSection(slot, slotDef));
    }
    const hint = document.createElement("p");
    hint.className = "hint";
    hint.innerHTML = `Assets live in <code>assets/shared/</code> — regenerate the demo
      library with <code>blender/scripts/build_demo_assets.py</code>.`;
    el.appendChild(hint);
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
  wardrobe,
  applyPhotoResult,
  get params() { return identityParams; },
  get defs() { return morphDefs; },
};

(async function boot() {
  [morphDefs] = await Promise.all([
    fetch("morph_definitions.json").then((r) => r.json()),
    wardrobe.init(),
  ]);
  buildIdentityTab();
  buildPhotosTab();
  buildDisplayTab();
  buildWardrobeTabs();
  buildExportTab();
  await loadAvatar($("#avatar-select").value);
})();
