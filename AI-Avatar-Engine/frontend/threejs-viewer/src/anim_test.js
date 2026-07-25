// Minimal runtime playback test for the exported animation library GLB.
// Loads the 103-clip GLB, drives it with an AnimationMixer, and exposes a
// small HUD + window.__animTest so the clip set can be verified in-browser.
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";

const GLB = "/avatars/animated_meta_male.glb";
const params = new URLSearchParams(location.search);
const START_CLIP = params.get("clip") || "wave";
// Seek to a fraction of the clip so a still screenshot lands on a clear pose.
const SEEK = params.has("seek") ? parseFloat(params.get("seek")) : 0.5;

const $ = (id) => document.getElementById(id);

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x202428);
const camera = new THREE.PerspectiveCamera(35, innerWidth / innerHeight, 0.01, 100);
camera.position.set(0, 1.2, 3.2);
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(devicePixelRatio);
renderer.setSize(innerWidth, innerHeight);
document.body.appendChild(renderer.domElement);
addEventListener("resize", () => {
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
});

scene.add(new THREE.HemisphereLight(0xffffff, 0x333340, 2.2));
const key = new THREE.DirectionalLight(0xffffff, 2.0);
key.position.set(2, 4, 3);
scene.add(key);
const grid = new THREE.GridHelper(4, 8, 0x444, 0x333);
scene.add(grid);

const controls = new OrbitControls(camera, renderer.domElement);
controls.target.set(0, 1.0, 0);
controls.update();

let mixer = null;
let clipsByName = new Map();
let current = null;

function play(name) {
  if (!mixer || !clipsByName.has(name)) return false;
  mixer.stopAllAction();
  const clip = clipsByName.get(name);
  const action = mixer.clipAction(clip);
  action.reset();
  action.play();
  // deterministic pose for stills
  mixer.setTime(clip.duration * SEEK);
  current = name;
  $("playing").textContent = `${name} (${clip.duration.toFixed(2)}s)`;
  return true;
}

const loader = new GLTFLoader();
$("status").textContent = "loading GLB…";
loader.load(
  GLB,
  (gltf) => {
    scene.add(gltf.scene);
    // frame the avatar
    const box = new THREE.Box3().setFromObject(gltf.scene);
    const c = box.getCenter(new THREE.Vector3());
    const h = box.getSize(new THREE.Vector3()).y || 1.7;
    controls.target.set(c.x, c.y, c.z);
    camera.position.set(c.x, c.y + h * 0.1, c.z + h * 1.4);
    controls.update();

    mixer = new THREE.AnimationMixer(gltf.scene);
    for (const clip of gltf.animations) clipsByName.set(clip.name, clip);

    const names = [...clipsByName.keys()].sort();
    $("count").textContent = String(gltf.animations.length);
    const sel = $("clip");
    for (const n of names) {
      const o = document.createElement("option");
      o.value = o.textContent = n;
      sel.appendChild(o);
    }
    sel.addEventListener("change", () => play(sel.value));

    const first = clipsByName.has(START_CLIP) ? START_CLIP : names[0];
    sel.value = first;
    play(first);
    $("status").textContent = "LOADED · PLAYING";

    // collect skeleton bones for motion probing
    const bones = new Map();
    gltf.scene.traverse((o) => { if (o.isBone) bones.set(o.name, o); });

    // Prove a clip actually DEFORMS the rig: sample selected bone world
    // positions across the clip timeline; return the max travel per bone.
    function motionProof(name, samples = 12) {
      if (!clipsByName.has(name)) return { error: "no clip " + name };
      const clip = clipsByName.get(name);
      mixer.stopAllAction();
      const action = mixer.clipAction(clip);
      action.reset(); action.play();
      const probe = ["CC_Base_R_Hand", "CC_Base_L_Hand", "CC_Base_Head",
                     "CC_Base_R_Foot", "CC_Base_Hip", "CC_Base_JawRoot"]
                    .filter((b) => bones.has(b));
      const first = {}, ranges = {};
      const v = new THREE.Vector3();
      for (let i = 0; i < samples; i++) {
        mixer.setTime((clip.duration * i) / (samples - 1));
        gltf.scene.updateMatrixWorld(true);
        for (const b of probe) {
          bones.get(b).getWorldPosition(v);
          const p = [v.x, v.y, v.z];
          if (i === 0) { first[b] = p; ranges[b] = 0; }
          else {
            const d = Math.hypot(p[0]-first[b][0], p[1]-first[b][1], p[2]-first[b][2]);
            if (d > ranges[b]) ranges[b] = d;
          }
        }
      }
      const out = {};
      for (const b of probe) out[b] = +(ranges[b] * 100).toFixed(2); // cm of travel
      return { clip: name, duration: +clip.duration.toFixed(2), travel_cm: out };
    }

    window.__animTest = {
      count: gltf.animations.length,
      clips: names,
      play,
      current: () => current,
      bones: [...bones.keys()],
      motionProof,
    };
    // low-level refs for the full glitch scan
    window.__scan = { scene: gltf.scene, mixer, clips: clipsByName, bones, Vec: THREE.Vector3 };
  },
  (ev) => {
    if (ev.total) $("status").textContent = `loading ${((ev.loaded / ev.total) * 100) | 0}%`;
  },
  (err) => {
    $("status").textContent = "LOAD ERROR: " + err.message;
    console.error(err);
  }
);

const clock = new THREE.Clock();
renderer.setAnimationLoop(() => {
  const dt = clock.getDelta();
  if (mixer) mixer.update(dt);
  controls.update();
  renderer.render(scene, camera);
});
