/**
 * SandboxViewer — Three.js scene, avatar loading, morph driving,
 * debug helpers (skeleton / wireframe / normals / UV), asset attachment,
 * and GLB export. UI-agnostic; main.js owns the DOM.
 */
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { GLTFExporter } from "three/addons/exporters/GLTFExporter.js";
import { VertexNormalsHelper } from "three/addons/helpers/VertexNormalsHelper.js";

export class SandboxViewer {
  constructor(canvas) {
    this.canvas = canvas;
    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;

    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x2a2d34);

    this.camera = new THREE.PerspectiveCamera(35, 1, 0.01, 100);
    this.camera.position.set(0, 1.65, 0.75);

    this.controls = new OrbitControls(this.camera, canvas);
    this.controls.target.set(0, 1.6, 0);
    this.controls.enableDamping = true;

    const hemi = new THREE.HemisphereLight(0xffffff, 0x445566, 1.1);
    this.scene.add(hemi);
    const key = new THREE.DirectionalLight(0xffffff, 2.2);
    key.position.set(0.5, 2.5, 2);
    this.scene.add(key);
    const rim = new THREE.DirectionalLight(0xbcd4ff, 0.8);
    rim.position.set(-1.5, 2, -2);
    this.scene.add(rim);

    this.grid = new THREE.GridHelper(4, 20, 0x555b66, 0x3a3f4a);
    this.scene.add(this.grid);

    this.loader = new GLTFLoader();

    this.avatarRoot = null;
    this.meshes = [];            // all skinned/morph meshes of the avatar
    this.headBone = null;
    this.morphIndex = new Map(); // key name -> [{mesh, index}]
    this.attachments = [];       // {id, name, root, boneName}
    this._attachId = 0;

    // debug state
    this.skeletonHelper = null;
    this.normalsHelpers = [];
    this._uvOriginalMaterials = new Map();
    this._uvTexture = null;

    this._resize();
    window.addEventListener("resize", () => this._resize());
    this.renderer.setAnimationLoop(() => {
      this.controls.update();
      this.renderer.render(this.scene, this.camera);
    });
  }

  _resize() {
    const w = this.canvas.parentElement.clientWidth;
    const h = this.canvas.parentElement.clientHeight;
    this.renderer.setSize(w, h, false);
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
  }

  // ------------------------------------------------------------------
  async loadAvatar(url, onProgress) {
    this.clearAvatar();
    const gltf = await new Promise((resolve, reject) =>
      this.loader.load(url, resolve, onProgress, reject));

    this.avatarRoot = gltf.scene;
    this.scene.add(this.avatarRoot);

    this.meshes = [];
    this.morphIndex = new Map();
    this.headBone = null;

    this.avatarRoot.traverse((o) => {
      if (o.isMesh || o.isSkinnedMesh) {
        o.frustumCulled = false;
        this.meshes.push(o);
        if (o.morphTargetDictionary) {
          for (const [name, idx] of Object.entries(o.morphTargetDictionary)) {
            if (!this.morphIndex.has(name)) this.morphIndex.set(name, []);
            this.morphIndex.get(name).push({ mesh: o, index: idx });
          }
        }
      }
      if (o.isBone && o.name === "CC_Base_Head") this.headBone = o;
    });

    this.frameFace();
    return this.describe();
  }

  clearAvatar() {
    this.setSkeleton(false);
    this.setNormals(false);
    this.setUVDebug(false);
    this.setWireframe(false);
    for (const a of [...this.attachments]) this.removeAttachment(a.id);
    if (this.avatarRoot) {
      this.scene.remove(this.avatarRoot);
      this.avatarRoot.traverse((o) => {
        if (o.geometry) o.geometry.dispose();
        if (o.material) {
          const mats = Array.isArray(o.material) ? o.material : [o.material];
          mats.forEach((m) => m.dispose());
        }
      });
      this.avatarRoot = null;
    }
    this.meshes = [];
    this.morphIndex = new Map();
  }

  // ------------------------------------------------------------------
  /** Structured description of the loaded avatar for the Inspector tab. */
  describe() {
    const meshes = [];
    const materials = new Map();
    let bones = [];
    this.avatarRoot.traverse((o) => {
      if (o.isMesh || o.isSkinnedMesh) {
        const mats = Array.isArray(o.material) ? o.material : [o.material];
        mats.forEach((m) => materials.set(m.name || m.uuid, m));
        meshes.push({
          name: o.name,
          vertices: o.geometry.attributes.position.count,
          morphTargets: o.morphTargetInfluences ? o.morphTargetInfluences.length : 0,
          materials: mats.map((m) => m.name || "(unnamed)"),
          skinned: !!o.isSkinnedMesh,
        });
      }
      if (o.isSkinnedMesh && o.skeleton && o.skeleton.bones.length > bones.length) {
        bones = o.skeleton.bones;
      }
    });

    const boneTree = [];
    if (bones.length) {
      const boneSet = new Set(bones);
      const roots = bones.filter((b) => !boneSet.has(b.parent));
      const walk = (b, depth) => {
        boneTree.push("  ".repeat(depth) + b.name);
        b.children.filter((c) => c.isBone).forEach((c) => walk(c, depth + 1));
      };
      roots.forEach((r) => walk(r, 0));
    }

    return {
      meshes,
      materials: [...materials.entries()].map(([name, m]) => ({
        name,
        type: m.type,
        maps: ["map", "normalMap", "roughnessMap", "alphaMap", "aoMap"]
          .filter((k) => m[k]),
      })),
      boneCount: bones.length,
      boneTree,
      morphNames: [...this.morphIndex.keys()],
    };
  }

  // ------------------------------------------------------------------
  /** Set a morph value (may be negative) on every mesh carrying that key. */
  setMorph(name, value) {
    const entries = this.morphIndex.get(name);
    if (!entries) return false;
    for (const { mesh, index } of entries) mesh.morphTargetInfluences[index] = value;
    return true;
  }

  getMorph(name) {
    const entries = this.morphIndex.get(name);
    return entries ? entries[0].mesh.morphTargetInfluences[entries[0].index] : 0;
  }

  resetAllMorphs() {
    for (const entries of this.morphIndex.values())
      for (const { mesh, index } of entries) mesh.morphTargetInfluences[index] = 0;
  }

  // ------------------------------------------------------------------
  setSkeleton(on) {
    if (on && this.avatarRoot && !this.skeletonHelper) {
      this.skeletonHelper = new THREE.SkeletonHelper(this.avatarRoot);
      this.skeletonHelper.material.depthTest = false;
      this.scene.add(this.skeletonHelper);
    } else if (!on && this.skeletonHelper) {
      this.scene.remove(this.skeletonHelper);
      this.skeletonHelper.dispose();
      this.skeletonHelper = null;
    }
  }

  setWireframe(on) {
    for (const mesh of this.meshes) {
      const mats = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
      mats.forEach((m) => { if ("wireframe" in m) m.wireframe = on; });
    }
  }

  setNormals(on) {
    if (on && this.normalsHelpers.length === 0) {
      for (const mesh of this.meshes) {
        const h = new VertexNormalsHelper(mesh, 0.004, 0x38e079);
        this.normalsHelpers.push(h);
        this.scene.add(h);
      }
    } else if (!on) {
      for (const h of this.normalsHelpers) { this.scene.remove(h); h.dispose(); }
      this.normalsHelpers = [];
    }
  }

  _makeUVTexture() {
    if (this._uvTexture) return this._uvTexture;
    const size = 1024, cells = 16;
    const cv = document.createElement("canvas");
    cv.width = cv.height = size;
    const ctx = cv.getContext("2d");
    const cell = size / cells;
    for (let y = 0; y < cells; y++) {
      for (let x = 0; x < cells; x++) {
        const even = (x + y) % 2 === 0;
        ctx.fillStyle = even ? "#3a55d9" : "#e8ecf5";
        ctx.fillRect(x * cell, y * cell, cell, cell);
      }
    }
    ctx.strokeStyle = "#e5534b"; ctx.lineWidth = 4;
    ctx.strokeRect(0, 0, size, size);
    ctx.fillStyle = "#e5534b";
    ctx.font = "bold 44px monospace";
    ctx.fillText("0,0", 14, 52);
    ctx.fillText("1,1", size - 100, size - 20);
    const tex = new THREE.CanvasTexture(cv);
    tex.colorSpace = THREE.SRGBColorSpace;
    tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
    this._uvTexture = tex;
    return tex;
  }

  setUVDebug(on) {
    if (on && this._uvOriginalMaterials.size === 0) {
      const tex = this._makeUVTexture();
      for (const mesh of this.meshes) {
        this._uvOriginalMaterials.set(mesh, mesh.material);
        const mats = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
        const replaced = mats.map(() => new THREE.MeshBasicMaterial({ map: tex }));
        mesh.material = Array.isArray(mesh.material) ? replaced : replaced[0];
      }
    } else if (!on && this._uvOriginalMaterials.size > 0) {
      for (const [mesh, original] of this._uvOriginalMaterials) {
        const mats = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
        mats.forEach((m) => m.dispose());
        mesh.material = original;
      }
      this._uvOriginalMaterials.clear();
    }
  }

  // ------------------------------------------------------------------
  /**
   * @param {THREE.Vector3|[number,number,number]|null} offset  extra WORLD-space
   *   meters added to the bone position (e.g. a per-style Meta fit nudge).
   *   Must be folded in here, before parentInv is applied — mutating
   *   root.position after the fact would land in the bone's local frame
   *   (scaled by the armature's ~0.01 import scale and rotated by the bone's
   *   rest orientation), silently shrinking/mixing the intended world offset.
   * @param {number} scale  uniform WORLD scale for the asset (default 1,
   *   i.e. today's byte-identical behavior for callers that omit it).
   */
  async attachAsset(url, name, boneName, offset = null, scale = 1) {
    const gltf = await new Promise((resolve, reject) =>
      this.loader.load(url, resolve, undefined, reject));
    const root = gltf.scene;
    let parent = this.avatarRoot;
    if (boneName) {
      let bone = null;
      this.avatarRoot.traverse((o) => {
        if (o.isBone && o.name === boneName) bone = o;
      });
      if (bone) parent = bone;
      else console.warn(`Bone ${boneName} not found; attaching to root`);
    }
    parent.add(root);
    // Bones carry the armature's import scale (0.01) and their own rest
    // orientation. Assets are authored bone-relative in world meters, so bake
    // the inverse parent transform: the asset sits at the bone's world
    // position (+ optional world-meters offset) with identity rotation and a
    // uniform world scale (default 1), and still follows the bone.
    parent.updateWorldMatrix(true, false);
    const bonePos = new THREE.Vector3().setFromMatrixPosition(parent.matrixWorld);
    if (offset) bonePos.add(Array.isArray(offset)
      ? new THREE.Vector3(offset[0], offset[1], offset[2]) : offset);
    const desired = new THREE.Matrix4().compose(
      bonePos, new THREE.Quaternion(), new THREE.Vector3(scale, scale, scale));
    const parentInv = parent.matrixWorld.clone().invert();
    root.matrix.copy(parentInv.multiply(desired));
    root.matrix.decompose(root.position, root.quaternion, root.scale);
    const id = ++this._attachId;
    this.attachments.push({ id, name, root, boneName });
    return id;
  }

  /**
   * Attach a SKINNED asset (clothing, hair): re-binds every skinned mesh in
   * the asset GLB to the avatar's own bones, matched by bone name. The asset
   * then deforms with the avatar skeleton — its own armature copy is dropped.
   */
  async attachSkinned(url, name) {
    const gltf = await new Promise((resolve, reject) =>
      this.loader.load(url, resolve, undefined, reject));
    gltf.scene.updateMatrixWorld(true);

    const avatarBones = {};
    this.avatarRoot.traverse((o) => { if (o.isBone) avatarBones[o.name] = o; });

    const holder = new THREE.Group();
    holder.name = `attach_${name}`;
    const skinnedMeshes = [];
    gltf.scene.traverse((o) => { if (o.isSkinnedMesh) skinnedMeshes.push(o); });

    for (const sm of skinnedMeshes) {
      const mapped = sm.skeleton.bones.map((b) => avatarBones[b.name] || null);
      if (mapped.some((b) => !b)) {
        console.warn(`attachSkinned(${name}): unmatched bones`, sm.skeleton.bones
          .filter((b, i) => !mapped[i]).map((b) => b.name));
      }
      const world = sm.matrixWorld.clone();
      holder.add(sm);
      sm.matrix.copy(world);
      sm.matrix.decompose(sm.position, sm.quaternion, sm.scale);
      sm.bind(new THREE.Skeleton(mapped.map((b, i) => b || sm.skeleton.bones[i]),
        sm.skeleton.boneInverses), sm.bindMatrix);
      sm.frustumCulled = false;
    }

    this.avatarRoot.add(holder);
    const id = ++this._attachId;
    this.attachments.push({ id, name, root: holder, boneName: null });
    return id;
  }

  removeAttachment(id) {
    const i = this.attachments.findIndex((a) => a.id === id);
    if (i === -1) return;
    const a = this.attachments[i];
    a.root.removeFromParent();
    a.root.traverse((o) => {
      if (o.geometry) o.geometry.dispose();
      if (o.material) {
        const mats = Array.isArray(o.material) ? o.material : [o.material];
        mats.forEach((m) => m.dispose());
      }
    });
    this.attachments.splice(i, 1);
  }

  // ------------------------------------------------------------------
  frameFace() {
    let target = new THREE.Vector3(0, 1.63, 0);
    if (this.headBone) this.headBone.getWorldPosition(target);
    target.y += 0.02;
    this.controls.target.copy(target);
    this.camera.position.set(target.x, target.y + 0.01, target.z + 0.55);
  }

  frameBody() {
    if (!this.avatarRoot) return;
    const box = new THREE.Box3().setFromObject(this.avatarRoot);
    const center = box.getCenter(new THREE.Vector3());
    const height = box.getSize(new THREE.Vector3()).y;
    this.controls.target.copy(center);
    this.camera.position.set(center.x, center.y + 0.1, center.z + height * 1.35);
  }

  // ------------------------------------------------------------------
  async exportGLB() {
    const exporter = new GLTFExporter();
    const result = await exporter.parseAsync(this.avatarRoot, {
      binary: true,
      animations: [],
    });
    return result; // ArrayBuffer
  }
}
