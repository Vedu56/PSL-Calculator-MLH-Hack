import base64
import hashlib
import io
import json
import re
import time

import requests
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv
from PIL import Image, ImageOps

try:  # iPhone HEIC photos (from app.py); optional - install with: python -m pip install pillow-heif
    import pillow_heif

    pillow_heif.register_heif_opener()
    HEIC_SUPPORTED = True
except ImportError:
    HEIC_SUPPORTED = False

import landing_page
import pvp_page
import site_ui

# =====================================================================
# Config
# =====================================================================
load_dotenv()
HF_TOKEN = os.getenv("HF_TOKEN")
API_URL = "https://api-inference.huggingface.co/models/google/paligemma-3b-mix-224"
HEADERS = {"Authorization": f"Bearer {HF_TOKEN}", "Content-Type": "application/json"}

PROMPT = (
    "Rate the facial aesthetics of this photo on a 1-10 PSL scale and give constructive, "
    'objective advice. Reply ONLY with JSON: {"psl_score": <number>, "advice": "<short string>"}'
)

UPLOAD_TYPES = ["jpg", "jpeg", "png"] + (["heic", "heif"] if HEIC_SUPPORTED else [])

# ---- PSL tier scale and advice pools (from app.py) ----
# (score upper bound, tier label)
TIERS = [
    (2.0, "Deformed / Subhuman"),
    (3.0, "Very Unattractive"),
    (3.5, "Low-Tier Normie (LTN)"),
    (4.5, "Mid-Tier Normie (MTN)"),
    (5.0, "True Mid-Tier Normie"),
    (6.0, "High-Tier Normie (HTN)"),
    (7.0, "Chadlite"),
]
TOP_TIER = "Chad / True Adam"

EYES_JARGON = [
    "positive canthal tilt with strong hunter eyes giving an intense predatory gaze",
    "neutral orbital vector with deep-set sockets and solid under-eye support",
    "slight negative canthal tilt offset by optimal interpupillary distance and heavy brow ridge framing",
]
BONE_JARGON = [
    "outstanding maxilla forward growth and a razor-sharp gonial angle",
    "solid ramus height with well-defined zygomatic arches providing clean facial dimorphism",
    "clean mandibular plane angle and balanced lower third proportions",
]
ACTION_JARGON = [
    "Begin intensive softmaxxing: reduce sodium to eliminate submental water retention, maintain strict mewing posture for upward palatal force, and hit heavy compound lifts to optimize your overall frame.",
    "Execute hard-softmaxxing protocol: clear up skin micro-texture, focus on neck training for a thicker optical jaw base, and practice proper chewing mechanics to maximize masseter hypertrophy.",
    "Maintain your baseline while optimizing framing: grow out hair for ideal temporal width, maintain low body fat percentage for peak jawline definition, and lean into your natural dimorphic strengths.",
]

# How long the scan + loading animation plays (the result is held back until it finishes).
SCAN_SECONDS = 10

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Audiowide&display=swap');
.stApp { background: radial-gradient(circle at 50% 0%, #1a1a1a 0%, #000 55%); color: #fff;
         font-family: 'Audiowide', sans-serif; }
h1, h2, h3, p, label, span, div { font-family: 'Audiowide', sans-serif; }
#MainMenu, footer, header { visibility: hidden; }
.hero { text-align: center; padding: 1.5rem 0 0.5rem; }
.hero h1 { font-size: 2.6rem; letter-spacing: 3px; margin: 0; }
.hero p { color: #8a8a8a; font-size: 0.85rem; letter-spacing: 2px; margin-top: 0.4rem; }
[data-testid="stFileUploadDropzone"] { border: 2px dashed #444; background: #080808;
    border-radius: 12px; transition: border-color .2s; }
[data-testid="stFileUploadDropzone"]:hover { border-color: #fff; }
.stButton > button { width: 100%; background: #fff; color: #000; border: 2px solid #fff;
    border-radius: 0; padding: 0.7rem; font-size: 1rem; letter-spacing: 2px; transition: all .2s; }
.stButton > button:hover { background: #000; color: #fff; }
.st-key-retake button { background: transparent; color: #999; border: 1px solid #333; padding: .4rem; font-size: .8rem; }
.st-key-retake button:hover { color: #fff; border-color: #fff; background: transparent; }
.card { border: 1px solid #333; background: #0a0a0a; border-radius: 14px; padding: 1.4rem; margin-top: 1rem; }
.score-wrap { text-align: center; }
.score { font-size: 4.5rem; line-height: 1; }
.score small { font-size: 1.4rem; color: #777; }
.tier { letter-spacing: 3px; color: #aaa; margin-top: .4rem; }
.bar { height: 10px; background: #1c1c1c; border-radius: 99px; margin-top: 1rem; overflow: hidden; }
.bar > div { height: 100%; background: linear-gradient(90deg, #555, #fff); border-radius: 99px; }
.advice { color: #ddd; font-size: .95rem; line-height: 1.6; }
.badge { display:inline-block; padding: 2px 10px; border:1px solid #ffb300; color:#ffb300;
         border-radius: 99px; font-size: .7rem; letter-spacing: 2px; margin-bottom: .8rem; }

/* Loader that takes the place of the CALCULATE button while the scan runs */
.loader { position: relative; overflow: hidden; box-sizing: border-box; width: 100%; height: 3.1rem;
          border: 2px solid #00ff66; background: #00140a; box-shadow: 0 0 16px rgba(0,255,102,.30); }
.loader .fill { position: absolute; left: 0; top: 0; bottom: 0; width: 0;
                background: linear-gradient(90deg, rgba(0,255,102,.10), rgba(0,255,102,.42));
                border-right: 2px solid #00ff66; box-shadow: 6px 0 18px rgba(0,255,102,.9);
                animation: pslfill var(--dur) cubic-bezier(.45,.05,.35,1) forwards; }
.loader .msg { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center;
               color: #00ff66; font-size: .95rem; letter-spacing: 3px; opacity: 0;
               text-shadow: 0 0 10px rgba(0,255,102,.8);
               animation: pslmsg calc(var(--dur) / 4) ease-in-out both;
               animation-delay: calc(var(--dur) / 4 * var(--i)); }
.loader .msg.last { animation-name: pslmsglast; }
@keyframes pslfill { to { width: 100%; } }
@keyframes pslmsg { 0% { opacity: 0; transform: translateY(8px); } 18%, 82% { opacity: 1; transform: none; }
                    100% { opacity: 0; transform: translateY(-8px); } }
@keyframes pslmsglast { 0% { opacity: 0; transform: translateY(8px); } 25%, 100% { opacity: 1; transform: none; } }
</style>
"""

LOADER_HTML = (
    '<div class="loader" style="--dur:%ds">'
    '<div class="fill"></div>'
    '<div class="msg" style="--i:0">LOCATING FACE</div>'
    '<div class="msg" style="--i:1">MAPPING LANDMARKS</div>'
    '<div class="msg" style="--i:2">ANALYSING FEATURES</div>'
    '<div class="msg last" style="--i:3">COMPILING RESULT</div>'
    "</div>" % SCAN_SECONDS
)

# =====================================================================
# Face-scan animation (runs entirely in the viewer's browser).
# MediaPipe Face Mesh finds ~468 landmarks on the actual face, so the green mesh fits that
# person's face. The photo is NOT uploaded anywhere for this step.
# Modes: "idle" / "done" (clean photo) and "scanning" (animated green scan that fades out by itself).
# =====================================================================
SCAN_HTML = r"""<!doctype html>
<html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Audiowide&display=swap" rel="stylesheet">
<style>
  html, body { margin: 0; background: transparent; overflow: hidden; font-family: 'Audiowide', sans-serif; }
  #wrap { position: relative; display: block; width: fit-content; max-width: 100%; margin: 0 auto; }
  canvas { display: block; max-width: 100%; max-height: __H__px; width: auto; height: auto; border-radius: 12px; }
  #status { position: absolute; left: 14px; bottom: 12px; right: 14px; color: #00ff66; font-size: 12px;
            letter-spacing: 2px; text-shadow: 0 0 8px #00ff66, 0 0 2px #000; }
</style>
</head>
<body>
<div id="wrap"><canvas id="c"></canvas><div id="status"></div></div>
<script>
const MODE = "__MODE__";            // "idle" | "scanning" | "done"
const TOTAL = __TOTAL__;            // ms the scanning animation runs before it settles
const G = "0,255,102";              // scan colour (green)
const img = new Image();
const canvas = document.getElementById("c");
const ctx = canvas.getContext("2d");
const statusEl = document.getElementById("status");
let pts = null, edges = [], bb = null, base = null, S = 1;
const START = performance.now();   // the scan length counts from when the photo appears

function setStatus(t) { statusEl.textContent = t; }
function ease(u) { return 0.5 - 0.5 * Math.cos(Math.PI * u); }

function paintPlain(tint) {            // tint: true/1 = full green tint, 0/false = clean photo, 0..1 = in between
  ctx.drawImage(img, 0, 0);
  const a = tint === true ? 1 : (tint || 0);
  if (a > 0) { ctx.fillStyle = "rgba(0,18,8," + (0.28 * a).toFixed(3) + ")"; ctx.fillRect(0, 0, canvas.width, canvas.height); }
}

function loadLib() {
  return new Promise((resolve, reject) => {
    if (typeof FaceMesh !== "undefined") { resolve(); return; }
    const s = document.createElement("script");
    s.src = "https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/face_mesh.js";
    s.crossOrigin = "anonymous";
    s.onload = () => resolve();
    s.onerror = () => reject("lib");
    document.head.appendChild(s);
  });
}

async function detect() {
  await loadLib();
  return new Promise((resolve, reject) => {
    if (typeof FaceMesh === "undefined") { reject("lib"); return; }
    const fm = new FaceMesh({ locateFile: f => "https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/" + f });
    fm.setOptions({ maxNumFaces: 1, refineLandmarks: false, minDetectionConfidence: 0.4, minTrackingConfidence: 0.4 });
    fm.onResults(r => {
      const lm = r.multiFaceLandmarks && r.multiFaceLandmarks[0];
      resolve(lm ? lm.map(p => ({ x: p.x * canvas.width, y: p.y * canvas.height })) : null);
    });
    fm.send({ image: img }).catch(() => reject("lib"));
    setTimeout(() => reject("lib"), 25000);
  });
}

// Fallback mesh if the library's own triangulation table is unavailable: link each point to its nearest neighbours.
function knnEdges(points, k) {
  const seen = new Set(), out = [];
  for (let i = 0; i < points.length; i++) {
    const d = [];
    for (let j = 0; j < points.length; j++) if (j !== i) d.push([(points[i].x-points[j].x)**2 + (points[i].y-points[j].y)**2, j]);
    d.sort((a, b) => a[0] - b[0]);
    for (let n = 0; n < k; n++) {
      const j = d[n][1], key = i < j ? i + "-" + j : j + "-" + i;
      if (!seen.has(key)) { seen.add(key); out.push([i, j]); }
    }
  }
  return out;
}

function prepare() {
  S = canvas.width / 400;
  let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
  for (const p of pts) { x0 = Math.min(x0, p.x); y0 = Math.min(y0, p.y); x1 = Math.max(x1, p.x); y1 = Math.max(y1, p.y); }
  const px = (x1 - x0) * 0.08, py = (y1 - y0) * 0.10;
  bb = { x0: x0 - px, y0: y0 - py, x1: x1 + px, y1: y1 + py };

  const T = (typeof FACEMESH_TESSELATION !== "undefined" && FACEMESH_TESSELATION.length) ? FACEMESH_TESSELATION : knnEdges(pts, 4);
  edges = T.map(([a, b]) => ({ a: pts[a], b: pts[b], ym: (pts[a].y + pts[b].y) / 2 }));

  base = document.createElement("canvas");
  base.width = canvas.width; base.height = canvas.height;
  const b = base.getContext("2d");
  b.lineCap = "round";
  b.strokeStyle = "rgba(" + G + ",0.42)"; b.lineWidth = Math.max(0.6, S * 0.8);
  b.beginPath();
  for (const e of edges) { b.moveTo(e.a.x, e.a.y); b.lineTo(e.b.x, e.b.y); }
  b.stroke();

  // brighter contours: face outline, eyes, brows, lips
  const contours = [
    typeof FACEMESH_FACE_OVAL !== "undefined" ? FACEMESH_FACE_OVAL : null,
    typeof FACEMESH_LEFT_EYE !== "undefined" ? FACEMESH_LEFT_EYE : null,
    typeof FACEMESH_RIGHT_EYE !== "undefined" ? FACEMESH_RIGHT_EYE : null,
    typeof FACEMESH_LEFT_EYEBROW !== "undefined" ? FACEMESH_LEFT_EYEBROW : null,
    typeof FACEMESH_RIGHT_EYEBROW !== "undefined" ? FACEMESH_RIGHT_EYEBROW : null,
    typeof FACEMESH_LIPS !== "undefined" ? FACEMESH_LIPS : null
  ];
  b.strokeStyle = "rgba(" + G + ",0.95)"; b.lineWidth = Math.max(1, S * 1.5);
  b.shadowColor = "rgb(" + G + ")"; b.shadowBlur = S * 4;
  b.beginPath();
  for (const c of contours) { if (!c) continue; for (const [i, j] of c) { b.moveTo(pts[i].x, pts[i].y); b.lineTo(pts[j].x, pts[j].y); } }
  b.stroke();
  b.shadowBlur = 0;

  // glowing nodes
  b.fillStyle = "rgba(" + G + ",0.95)";
  for (let i = 0; i < pts.length; i += 7) { b.beginPath(); b.arc(pts[i].x, pts[i].y, Math.max(1, S * 1.7), 0, 6.2832); b.fill(); }
}

function brackets(alpha) {
  const L = Math.min(bb.x1 - bb.x0, bb.y1 - bb.y0) * 0.2;
  const x0 = bb.x0, y0 = bb.y0, x1 = bb.x1, y1 = bb.y1;
  ctx.save();
  ctx.globalAlpha = alpha;
  ctx.strokeStyle = "rgb(" + G + ")"; ctx.lineWidth = Math.max(2, S * 2.4); ctx.lineCap = "square";
  ctx.shadowColor = "rgb(" + G + ")"; ctx.shadowBlur = S * 6;
  [[x0, y0, 1, 1], [x1, y0, -1, 1], [x0, y1, 1, -1], [x1, y1, -1, -1]].forEach(([x, y, dx, dy]) => {
    ctx.beginPath(); ctx.moveTo(x + dx * L, y); ctx.lineTo(x, y); ctx.lineTo(x, y + dy * L); ctx.stroke();
  });
  ctx.restore();
}

function loop(ts) {
  const el = ts - START;
  if (el >= TOTAL) { drawFinal(); return; }

  const HALF = 2600;                                   // one sweep (down or up), eased in/out for smoothness
  const k = Math.floor(el / HALF), f = ease((el % HALF) / HALF);
  const y = bb.y0 + (bb.y1 - bb.y0) * (k % 2 === 0 ? f : 1 - f);
  const fade = Math.min(1, (TOTAL - el) / 1200);       // scan bar + glow fade out at the end
  const enter = Math.min(1, el / 500);                 // brackets fade in at the start
  paintPlain(fade);                                    // green tint fades away together with everything else

  // first sweep reveals the mesh; afterwards the whole mesh stays and gently "breathes"
  ctx.save();
  ctx.globalAlpha = (0.85 + 0.15 * Math.sin(el / 350)) * fade;
  if (k === 0) { ctx.beginPath(); ctx.rect(0, 0, canvas.width, y); ctx.clip(); }
  ctx.drawImage(base, 0, 0);
  ctx.restore();

  // bright edges near the scan line, drawn in 5 alpha buckets for speed
  const band = (bb.y1 - bb.y0) * 0.09, NB = 5, paths = [];
  for (let i = 0; i < NB; i++) paths.push(new Path2D());
  for (const e of edges) {
    const d = Math.abs(e.ym - y);
    if (d < band && (k > 0 || e.ym <= y)) {
      const bi = Math.min(NB - 1, Math.floor((1 - d / band) * NB));
      paths[bi].moveTo(e.a.x, e.a.y); paths[bi].lineTo(e.b.x, e.b.y);
    }
  }
  ctx.save(); ctx.lineCap = "round"; ctx.lineWidth = Math.max(1, S * 1.4);
  ctx.shadowColor = "rgb(" + G + ")"; ctx.shadowBlur = S * 5;
  for (let i = 0; i < NB; i++) { ctx.strokeStyle = "rgba(" + G + "," + (((i + 1) / NB) * fade).toFixed(2) + ")"; ctx.stroke(paths[i]); }
  ctx.restore();

  // the scan bar itself
  const grad = ctx.createLinearGradient(bb.x0, 0, bb.x1, 0);
  grad.addColorStop(0, "rgba(" + G + ",0)"); grad.addColorStop(0.5, "rgba(" + G + "," + fade.toFixed(2) + ")"); grad.addColorStop(1, "rgba(" + G + ",0)");
  ctx.save(); ctx.shadowColor = "rgb(" + G + ")"; ctx.shadowBlur = S * 12; ctx.fillStyle = grad;
  ctx.fillRect(bb.x0, y - S * 1.5, bb.x1 - bb.x0, S * 3); ctx.restore();

  brackets(enter * fade);
  statusEl.style.opacity = fade.toFixed(2);
  setStatus("SCANNING / " + pts.length + " POINTS" + ".".repeat(1 + Math.floor(el / 400) % 3));
  requestAnimationFrame(loop);
}

// Scan finished: leave just the clean photo (no mesh, brackets, tint or text).
function drawFinal() {
  paintPlain(false);
  statusEl.style.display = "none";
}

function noFace(reason) {
  const msg = reason === "lib" ? "SCAN VISUAL UNAVAILABLE (CHECK INTERNET)" : "NO FACE FOUND - USE A CLEAR FRONT-FACING PHOTO";
  S = canvas.width / 400;
  if (MODE !== "scanning") { paintPlain(true); setStatus(msg); return; }
  (function frame(ts) {
    const el = ts - START;
    paintPlain(true);
    setStatus(msg);
    if (el >= TOTAL) return;
    const f = ease((el % 2600) / 2600), y = (Math.floor(el / 2600) % 2 === 0 ? f : 1 - f) * canvas.height;
    const a = Math.min(1, (TOTAL - el) / 1200);
    const g = ctx.createLinearGradient(0, 0, canvas.width, 0);
    g.addColorStop(0, "rgba(" + G + ",0)"); g.addColorStop(0.5, "rgba(" + G + "," + a.toFixed(2) + ")"); g.addColorStop(1, "rgba(" + G + ",0)");
    ctx.save(); ctx.shadowColor = "rgb(" + G + ")"; ctx.shadowBlur = S * 12; ctx.fillStyle = g;
    ctx.fillRect(0, y - S * 1.5, canvas.width, S * 3); ctx.restore();
    requestAnimationFrame(frame);
  })(performance.now());
}

img.onload = async () => {
  canvas.width = img.naturalWidth; canvas.height = img.naturalHeight;
  if (MODE === "idle" || MODE === "done") { paintPlain(false); statusEl.style.display = "none"; return; }  // clean photo, no scan
  paintPlain(true);
  setStatus("LOCATING FACE...");
  try { pts = await detect(); } catch (e) { noFace("lib"); return; }
  if (!pts) { noFace("none"); return; }
  prepare();
  if (MODE === "scanning") requestAnimationFrame(loop); else drawFinal();
};
img.src = "__IMG__";
</script>
</body></html>
"""


# =====================================================================
# Model call
# =====================================================================
def call_model(file_bytes: bytes) -> dict:
    """Call the HF inference API and parse JSON. Raises on any failure."""
    payload = {"inputs": {"image": base64.b64encode(file_bytes).decode(), "question": PROMPT}}
    r = requests.post(API_URL, headers=HEADERS, json=payload, timeout=20)
    r.raise_for_status()
    body = r.json()
    if isinstance(body, list):
        raw = body[0].get("generated_text") or body[0].get("answer") or ""
    else:
        raw = str(body)
    match = re.search(r"\{.*\}", raw, re.S)  # find the JSON object even inside code fences
    if not match:
        raise ValueError("Model did not return JSON")
    data = json.loads(match.group(0))
    data["psl_score"] = max(1.0, min(10.0, float(data["psl_score"])))
    return data


def tier_for(score: float) -> str:
    for cap, name in TIERS:
        if score <= cap:
            return name
    return TOP_TIER


def sample_result(photo) -> dict:
    """Score + advice from app.py's generator, used when the live model can't answer.
    It does NOT look at the face: the numbers come from the file's name and size, so the
    result is shown with the "SAMPLE RESULT" badge."""
    seed = (len(photo.name) * 17 + photo.size) % 100
    score = round(3.5 + (seed % 44) / 10, 1)      # 3.5 to 7.8
    tier = tier_for(score)
    advice = (
        f"Classified ranking: {tier}. Facial features display {EYES_JARGON[seed % len(EYES_JARGON)]} "
        f"paired with {BONE_JARGON[seed % len(BONE_JARGON)]}. {ACTION_JARGON[seed % len(ACTION_JARGON)]}"
    )
    return {"psl_score": score, "advice": advice}


def as_jpeg(file_bytes: bytes) -> bytes:
    """Re-encode any upload (including HEIC) as JPEG before sending it to the model."""
    img = ImageOps.exif_transpose(Image.open(io.BytesIO(file_bytes))).convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=92)
    return buf.getvalue()


# =====================================================================
# Photo handling
# =====================================================================
class Photo:
    """Minimal stand-in for an uploaded file (lets us keep a camera shot after hiding the camera widget)."""

    def __init__(self, data: bytes, name: str):
        self._data, self.name, self.size = data, name, len(data)

    def getvalue(self) -> bytes:
        return self._data


def pick_photo():
    """Upload OR live camera. Returns a Photo (or None)."""
    source = st.radio("Source", ["Upload", "Camera"], horizontal=True, label_visibility="collapsed")
    if source == "Upload":
        f = st.file_uploader("Upload a selfie", type=UPLOAD_TYPES, label_visibility="collapsed")
        return Photo(f.getvalue(), f.name) if f else None, source

    if "cam_bytes" in st.session_state:                       # already captured: show our big scan stage instead
        return Photo(st.session_state["cam_bytes"], "camera photo"), source
    st.caption("Your browser will ask permission to use the camera. Allow it, then press the capture button.")
    cam = st.camera_input("Take a selfie", label_visibility="collapsed", key=f"cam_{st.session_state.get('cam_n', 0)}")
    if cam:
        st.session_state["cam_bytes"] = cam.getvalue()
        st.rerun()
    return None, source


def prepare_image(photo, max_side: int = 900):
    """Fix phone rotation, shrink, and return (data_url, (width, height)) for the scan animation."""
    img = Image.open(io.BytesIO(photo.getvalue()))
    img = ImageOps.exif_transpose(img).convert("RGB")
    img.thumbnail((max_side, max_side))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode(), img.size


def render_stage(photo, mode: str):
    """The large photo area. mode: 'idle' | 'scanning' | 'done'."""
    data_url, (w, h) = prepare_image(photo)
    height = min(round(700 * h / w), 560)
    html = (
        SCAN_HTML.replace("__IMG__", data_url)
        .replace("__MODE__", mode)
        .replace("__TOTAL__", str(int(SCAN_SECONDS * 1000) - 700))  # ends just before the result swaps in
        .replace("__H__", str(height))
    )
    components.html(html, height=height + 6)


# =====================================================================
# UI components
# =====================================================================
def render_header():
    st.markdown(
        '<div class="hero"><h1>🗿 PSL CALCULATOR</h1>'
        "<p>AI AESTHETICS RATER · POWERED BY PALIGEMMA 3B</p></div>",
        unsafe_allow_html=True,
    )


def render_result(data: dict, fallback: bool):
    score = float(data["psl_score"])
    badge = '<div class="badge">SAMPLE RESULT · LIVE ANALYSIS UNAVAILABLE</div>' if fallback else ""
    st.markdown(
        f"""
<div class="card">
  {badge}
  <div class="score-wrap">
    <div class="score">{score:.1f}<small>/10</small></div>
    <div class="tier">{tier_for(score)}</div>
    <div class="bar"><div style="width:{score * 10}%"></div></div>
  </div>
</div>
<div class="card"><b>💡 Looksmaxxing advice</b><p class="advice">{data.get("advice", "")}</p></div>
""",
        unsafe_allow_html=True,
    )

# =====================================================================
# PSL Score page (opened from the home page)
# =====================================================================
def render_score_page():
    st.markdown(CSS, unsafe_allow_html=True)
    render_header()

    photo, source = pick_photo()

    if not photo:
        st.session_state.pop("result", None)
        if source == "Upload":
            st.info("Upload a JPG/PNG or switch to Camera to take a selfie.")
    else:
        pid = hashlib.md5(photo.getvalue()).hexdigest()
        res = st.session_state.get("result")
        if res and res["pid"] != pid:          # a different photo was chosen: forget the old result
            res = None
            st.session_state.pop("result", None)

        st.caption(f"TARGET LOCKED 🎯 · {photo.name} · {photo.size / 1024:.0f} KB")
        stage_slot = st.empty()                # the big photo, which is where the scan plays
        btn_slot = st.empty()                  # the CALCULATE button, which turns into the loader

        def show_stage(mode: str):
            with stage_slot.container():
                render_stage(photo, mode)

        btn_n = st.session_state.setdefault("btn_n", 0)
        show_stage("done" if res else "idle")
        clicked = btn_slot.button("RESCAN" if res else "CALCULATE PSL", key=f"calc_{btn_n}")

        if source == "Camera":
            if st.button("RETAKE PHOTO", key="retake"):
                st.session_state.pop("cam_bytes", None)
                st.session_state.pop("result", None)
                st.session_state["cam_n"] = st.session_state.get("cam_n", 0) + 1
                st.rerun()

        if clicked:
            show_stage("scanning")
            btn_slot.markdown(LOADER_HTML, unsafe_allow_html=True)
            started = time.time()
            fallback = False
            try:
                data = call_model(as_jpeg(photo.getvalue()))
            except Exception:
                data, fallback = sample_result(photo), True      # live analysis failed: show a labelled sample result
            time.sleep(max(0.0, SCAN_SECONDS - (time.time() - started)))
            show_stage("done")                                    # analysis finished: remove the green scan
            res = {"pid": pid, "data": data, "fallback": fallback}
            st.session_state["result"] = res
            st.session_state["btn_n"] = btn_n + 1                 # fresh key so the next click is registered
            btn_slot.button("RESCAN", key=f"calc_{btn_n + 1}")

        if res:
            render_result(res["data"], res["fallback"])


# =====================================================================
# App: home page, routing to the PSL Score and PSL PvP pages
# =====================================================================
page = site_ui.current_page()
st.set_page_config(page_title="PSL Calculator", page_icon="🗿", layout="wide" if page == "home" else "centered")
site_ui.inject_theme(page)

if page == "score":
    site_ui.back_button()
    render_score_page()
elif page == "pvp":
    site_ui.back_button()
    pvp_page.render()
else:
    landing_page.render()
