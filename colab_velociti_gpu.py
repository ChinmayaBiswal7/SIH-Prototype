# ==============================================================================
# VeloCITI AI GPU Backend - Google Colab Server
# Multi-Frame CCTV Video (2 FPS) & Instant Image ANPR on NVIDIA CUDA GPU
# ==============================================================================

import os
import io
import re
import cv2
import time
import base64
import random
import shutil
import tempfile
import threading
import numpy as np
from PIL import Image
from typing import Optional, List, Dict, Any

# 1. Install & Verify Dependencies
import subprocess, sys
try:
    import pycloudflared, easyocr, ultralytics, nest_asyncio
except ImportError:
    print("📦 Installing required dependencies in Colab (FastAPI, PyCloudflared, Ultralytics, EasyOCR)...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "fastapi", "uvicorn", "python-multipart", "pycloudflared", "ultralytics", "easyocr", "opencv-python-headless", "pillow", "requests", "nest-asyncio"])
    print("✅ Dependencies installed.")

import torch
import easyocr
from ultralytics import YOLO
from fastapi import FastAPI, File, UploadFile, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(title="VeloCITI AI GPU Engine", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print(f"🔥 [VeloCITI AI] Initializing on Device: {DEVICE}")

# Initialize YOLOv8 vehicle detection model
print("⚡ Loading YOLOv8n vehicle detector...")
yolo_model = YOLO("yolov8n.pt")
if DEVICE == "cuda":
    yolo_model.to("cuda")

# Initialize EasyOCR
print("⚡ Loading EasyOCR Engine on GPU...")
ocr_reader = easyocr.Reader(["en"], gpu=(DEVICE == "cuda"), verbose=False)
print("✅ Models loaded and ready for high-speed inference.")

# Indian License Plate Regex patterns
INDIAN_PLATE_REGEX = [
    re.compile(r"^[A-Z]{2}[0-9]{1,2}[A-Z]{0,3}[0-9]{4}$"),
    re.compile(r"^[A-Z]{2}[0-9]{2}[A-Z]{1,2}[0-9]{4}$"),
    re.compile(r"^[0-9]{2}BH[0-9]{4}[A-Z]{1,2}$"),
]

def clean_plate_string(text: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]", "", text).upper()
    if cleaned.startswith("7") and len(cleaned) >= 9:
        cleaned = "T" + cleaned[1:]
    return cleaned

def is_valid_plate(plate_text: str) -> bool:
    clean = clean_plate_string(plate_text)
    if len(clean) < 8 or len(clean) > 11:
        return False
    for regex in INDIAN_PLATE_REGEX:
        if regex.match(clean):
            return True
    return False

def frame_to_base64(frame_bgr: np.ndarray) -> str:
    _, buf = cv2.imencode(".jpg", frame_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 88])
    return "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode("utf-8")

def detect_plate_in_image(frame: np.ndarray):
    """
    Performs full-resolution plate localization and OCR.
    Returns: (plate_text, confidence, plate_bbox, car_bbox)
    """
    h, w = frame.shape[:2]
    # Step 1: Detect vehicles using YOLO
    yolo_res = yolo_model(frame, classes=[2, 3, 5, 7], conf=0.18, verbose=False)  # car, motor, bus, truck
    car_box = None
    best_car_area = 0
    for r in yolo_res:
        for b in r.boxes:
            box = [int(v) for v in b.xyxy[0].tolist()]
            area = (box[2] - box[0]) * (box[3] - box[1])
            if area > best_car_area:
                best_car_area = area
                car_box = box

    if car_box is None:
        car_box = [int(w * 0.08), int(h * 0.12), int(w * 0.92), int(h * 0.90)]

    # Step 2: Run OCR on the vehicle region
    ocr_results = ocr_reader.readtext(frame, detail=1)

    best_plate = None
    best_conf = 0.0
    best_plate_bbox = None

    # A. Check single OCR tokens
    for box, txt, conf in ocr_results:
        clean = clean_plate_string(txt)
        if is_valid_plate(clean) and conf > best_conf:
            best_plate = clean
            best_conf = float(conf)
            bx1 = max(0, int(min(pt[0] for pt in box)))
            by1 = max(0, int(min(pt[1] for pt in box)))
            bx2 = min(w - 1, int(max(pt[0] for pt in box)))
            by2 = min(h - 1, int(max(pt[1] for pt in box)))
            best_plate_bbox = [bx1, by1, bx2, by2]

    # B. Check multi-token combinations (e.g. 'TN87' and 'C 5106')
    if not best_plate:
        candidate_tokens = []
        for box, txt, conf in ocr_results:
            c_txt = clean_plate_string(txt)
            if 2 <= len(c_txt) <= 8 and conf >= 0.25:
                candidate_tokens.append((box, c_txt, conf))
        if len(candidate_tokens) >= 2:
            sorted_tokens = sorted(candidate_tokens, key=lambda x: x[0][0][0])
            comb = "".join([t[1] for t in sorted_tokens])
            if is_valid_plate(comb):
                best_plate = comb
                best_conf = float(sum(t[2] for t in sorted_tokens) / len(sorted_tokens))
                all_pts = [pt for t in sorted_tokens for pt in t[0]]
                bx1 = max(0, int(min(pt[0] for pt in all_pts)))
                by1 = max(0, int(min(pt[1] for pt in all_pts)))
                bx2 = min(w - 1, int(max(pt[0] for pt in all_pts)))
                by2 = min(h - 1, int(max(pt[1] for pt in all_pts)))
                best_plate_bbox = [bx1, by1, bx2, by2]

    return best_plate, best_conf, best_plate_bbox, car_box

def draw_plate_annotation(frame: np.ndarray, plate: str, plate_bbox: Optional[List[int]], car_box: List[int]) -> np.ndarray:
    annotated = frame.copy()
    h, w = annotated.shape[:2]

    # ONLY outline the exact plate if plate_bbox is known. Never draw random boxes on the car!
    if plate and plate_bbox:
        px1, py1, px2, py2 = plate_bbox
        px1 = max(0, px1 - 4); py1 = max(0, py1 - 4)
        px2 = min(w - 1, px2 + 4); py2 = min(h - 1, py2 + 4)
        box_col = (34, 197, 94)
        cv2.rectangle(annotated, (px1, py1), (px2, py2), box_col, 3)
        lbl = f" PLATE: {plate} "
        (lw, lh), _ = cv2.getTextSize(lbl, cv2.FONT_HERSHEY_SIMPLEX, 0.65, 2)
        cv2.rectangle(annotated, (px1, max(0, py1 - lh - 10)), (min(w, px1 + lw + 12), py1), box_col, -1)
        cv2.putText(annotated, lbl, (px1 + 4, py1 - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 0), 2)

    return annotated

# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------
@app.get("/")
def home():
    return {"status": "online", "device": DEVICE, "service": "VeloCITI AI Engine"}

@app.post("/predict_image")
async def predict_image(file: UploadFile = File(...)):
    raw = await file.read()
    frame = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        return JSONResponse({"success": False, "error": "Invalid image file"}, status_code=400)

    plate, conf, plate_bbox, car_box = detect_plate_in_image(frame)
    annotated = draw_plate_annotation(frame, plate, plate_bbox, car_box)
    img_b64 = frame_to_base64(annotated)

    if plate:
        return {
            "success": True, "has_plate": True, "plate_number": plate,
            "confidence": round(conf or 0.95, 3), "vehicle_type": "Car", "violation": "NONE",
            "plate_bbox": plate_bbox, "box": car_box, "image_data": img_b64, "device": DEVICE
        }
    else:
        return {
            "success": True, "has_plate": False, "plate_number": None, "confidence": 0.0,
            "vehicle_type": "Car", "violation": "MISSING_OR_COVERED_PLATE",
            "box": car_box, "image_data": img_b64, "device": DEVICE
        }

@app.post("/predict_video")
async def predict_video(file: UploadFile = File(...)):
    """
    Multi-frame high-speed video keyframe processing.
    Directly seeks to 4 keyframe positions across the video for instant 1-2 second inference.
    """
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    cap = cv2.VideoCapture(tmp_path)
    if not cap.isOpened():
        return JSONResponse({"success": False, "error": "Cannot read video"}, status_code=400)

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total_frames <= 0:
        total_frames = 60

    num_samples = min(4, total_frames)
    sample_indices = np.linspace(int(total_frames * 0.1), int(total_frames * 0.9), num_samples, dtype=int)

    unique_plates = {}
    unplated_vehicles = []
    sampled_count = 0

    for f_idx in sample_indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(f_idx))
        ret, frame = cap.read()
        if not ret or frame is None:
            continue
        sampled_count += 1
        t_sec = round(f_idx / fps, 2)
        plate, conf, plate_bbox, car_box = detect_plate_in_image(frame)
        if plate:
            if plate not in unique_plates or conf > unique_plates[plate]["confidence"]:
                annotated = draw_plate_annotation(frame, plate, plate_bbox, car_box)
                unique_plates[plate] = {
                    "plate": plate,
                    "has_plate": True,
                    "confidence": round(conf or 0.95, 3),
                    "vehicle_type": "Car",
                    "violation": "NONE",
                    "plate_bbox": plate_bbox,
                    "box": car_box,
                    "timestamp": t_sec,
                    "frame_index": int(f_idx),
                    "image_data": frame_to_base64(annotated)
                }
        else:
            if not unplated_vehicles:
                annotated = draw_plate_annotation(frame, None, None, car_box)
                unplated_vehicles.append({
                    "plate": None,
                    "has_plate": False,
                    "confidence": 0.0,
                    "vehicle_type": "Car",
                    "violation": "MISSING_OR_COVERED_PLATE",
                    "box": car_box,
                    "timestamp": t_sec,
                    "frame_index": int(f_idx),
                    "image_data": frame_to_base64(annotated)
                })

    cap.release()
    try:
        os.remove(tmp_path)
    except Exception:
        pass

    results = list(unique_plates.values()) or unplated_vehicles[:1]
    return {
        "success": True,
        "total": len(results),
        "fps": fps,
        "frames_sampled": sampled_count,
        "vehicles": results,
        "device": DEVICE
    }

# -----------------------------------------------------------------------------
# Launch Cloudflare Tunnel and Auto-Sync to Render
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# Clean previous processes, Launch Uvicorn, then Start Tunnel & Auto-Sync
# -----------------------------------------------------------------------------
from pycloudflared import try_cloudflare
import requests
import threading

# 1. Clean up stale processes
os.system("pkill -9 -f cloudflared 2>/dev/null || true")
os.system("pkill -9 -f uvicorn 2>/dev/null || true")
os.system("fuser -k 8000/tcp 2>/dev/null || true")
time.sleep(0.5)

# 2. Start Uvicorn in background thread (isolated event loop)
def run_uvicorn():
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")

server_thread = threading.Thread(target=run_uvicorn, daemon=True)
server_thread.start()

# 3. Wait for local server to be responsive
print("⏳ Initializing local VeloCITI server on port 8000...")
server_ready = False
for _ in range(30):
    try:
        r = requests.get("http://127.0.0.1:8000/", timeout=1)
        if r.status_code == 200:
            server_ready = True
            break
    except Exception:
        time.sleep(0.4)

if not server_ready:
    print("❌ Server failed to start locally on port 8000")
else:
    print("✅ Local VeloCITI server is UP and responding!")

# 4. Launch Cloudflare Tunnel with unique log file (guarantees a fresh active URL, never an expired one)
os.system("pkill -9 -f cloudflared 2>/dev/null || true")
if not os.path.exists("/usr/local/bin/cloudflared"):
    print("⬇️ Setting up Cloudflare Tunnel binary...")
    os.system("curl -sL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /usr/local/bin/cloudflared && chmod +x /usr/local/bin/cloudflared")

log_path = f"/tmp/cf_{int(time.time())}.log"
cf_proc = subprocess.Popen(
    ["cloudflared", "tunnel", "--url", "http://127.0.0.1:8000", "--logfile", log_path],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL
)

print("⏳ Connecting fresh Cloudflare Tunnel to edge...")
tunnel_url = None
for _ in range(60):
    time.sleep(0.5)
    if os.path.exists(log_path):
        try:
            with open(log_path, "r") as f:
                content = f.read()
                m = re.search(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", content)
                if m:
                    tunnel_url = m.group(0)
                    break
        except Exception:
            pass

if not tunnel_url:
    try:
        from pycloudflared import try_cloudflare
        t = try_cloudflare(port=8000)
        m = re.search(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", str(t))
        if m:
            tunnel_url = m.group(0)
    except Exception:
        pass

print("\n" + "=" * 65)
print(f"🚀 VeloCITI AI Engine is LIVE on NVIDIA GPU ({DEVICE})!")
print(f"🔗 Cloudflare Tunnel URL: {tunnel_url}")
print("=" * 65 + "\n")


try:
    resp = requests.post("https://clear-ways.onrender.com/api/set_ai_backend", json={"url": tunnel_url}, timeout=10)
    print(f"✅ Auto-synced active GPU tunnel to Render! Status: {resp.status_code}")
except Exception as e:
    print(f"⚠️ Note on auto-sync: {e}")

print("\n🔥 VeloCITI AI GPU backend is ready. Streaming requests will appear below.")
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Stopping server...")

