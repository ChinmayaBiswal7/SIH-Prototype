"""
tracking_api.py - Vehicle Tracking & Central Firebase Integration Bridge
========================================================================
Exposes citywide multi-camera ANPR tracking endpoints, RTO Vahan lookups,
and central Firebase Firestore synchronization directly on the ClearWays server.
"""

import os
import sys
import json
import time
import random
import threading
from datetime import datetime
from flask import jsonify, request, send_from_directory, Response

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CURRENT_DIR)
PORTOTYPE_DIR = os.path.join(ROOT_DIR, "portotype")
if os.path.exists(PORTOTYPE_DIR) and PORTOTYPE_DIR not in sys.path:
    sys.path.insert(0, PORTOTYPE_DIR)

DOCKER_PORTOTYPE_DIR = "/app/portotype"
if os.path.exists(DOCKER_PORTOTYPE_DIR) and DOCKER_PORTOTYPE_DIR not in sys.path:
    sys.path.insert(0, DOCKER_PORTOTYPE_DIR)

try:
    import database as db
    import alerts as al
    import analytics as an
    import rto
    import firebase_sync
    HAS_TRACKING = True
except Exception as e:
    print(f"[Tracking API] Warning: Failed to import tracking modules: {e}")
    HAS_TRACKING = False

STATIC_TRACKING_DIR = os.path.join(PORTOTYPE_DIR, "static")
if not os.path.exists(STATIC_TRACKING_DIR):
    STATIC_TRACKING_DIR = os.path.join(ROOT_DIR, "ClearWays-main", "clearways-react", "public", "vehicle-tracking")

SNAPSHOT_DIR = os.path.join(PORTOTYPE_DIR, "data", "snapshots")
os.makedirs(SNAPSHOT_DIR, exist_ok=True)

_sim_running = False
_sim_thread = None


def register_tracking_routes(app):
    """Mounts all ANPR Vehicle Tracking & Firebase endpoints onto the Flask app."""
    if not HAS_TRACKING:
        print("[Tracking API] Skipping route registration because tracking modules are not loaded.")
        return

    try:
        db.init_db()
        al.seed_demo_blacklist()
        print("[Tracking API] Initialized tracking database & alert rules.")
    except Exception as err:
        print(f"[Tracking API] Note on init_db: {err}")

    # -------------------------------------------------------------------
    # Static pages: Tracking Map & Live Camera Node
    # -------------------------------------------------------------------
    @app.route("/tracking")
    @app.route("/tracking/")
    def serve_tracking_map():
        for d in [STATIC_TRACKING_DIR, os.path.join(ROOT_DIR, "ClearWays-main", "clearways-react", "public", "vehicle-tracking")]:
            if os.path.exists(os.path.join(d, "dashboard.html")):
                return send_from_directory(d, "dashboard.html")
        return jsonify({"error": "dashboard.html not found"}), 404

    @app.route("/anpr")
    def serve_anpr_page():
        for d in [STATIC_TRACKING_DIR, os.path.join(ROOT_DIR, "ClearWays-main", "clearways-react", "public", "vehicle-tracking")]:
            if os.path.exists(os.path.join(d, "anpr.html")):
                return send_from_directory(d, "anpr.html")
        return jsonify({"error": "anpr.html not found"}), 404

    @app.route("/dossier")
    def serve_dossier_page():
        for d in [PORTOTYPE_DIR, STATIC_TRACKING_DIR, os.path.join(ROOT_DIR, "ClearWays-main", "clearways-react", "public", "vehicle-tracking")]:
            fpath = os.path.join(d, "SIH_2026_ANPR_Project_Dossier.html")
            if os.path.exists(fpath):
                return send_from_directory(d, "SIH_2026_ANPR_Project_Dossier.html")
            d_path = os.path.join(d, "dossier.html")
            if os.path.exists(d_path):
                return send_from_directory(d, "dossier.html")
        return jsonify({"error": "Dossier not found"}), 404

    # -------------------------------------------------------------------
    # RTO MoRTH / Vahan Vehicle Lookup
    # -------------------------------------------------------------------
    @app.route("/api/rto/lookup/<plate>")
    def api_rto_lookup(plate):
        try:
            data = rto.lookup_rto_vehicle(plate)
            return jsonify({"success": True, "rto": data})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    # -------------------------------------------------------------------
    # Ingest Camera Detection
    # -------------------------------------------------------------------
    @app.route("/api/detection", methods=["POST"])
    def api_detection():
        data = request.get_json(force=True) or {}
        plate = data.get("plate", "").upper().replace(" ", "")
        camera_id = data.get("camera_id", "CAM_01")
        timestamp = data.get("timestamp", datetime.now().isoformat(timespec="seconds"))
        confidence = float(data.get("confidence", 0.92))
        speed = float(data.get("speed_kmph", 40.0))
        lat = data.get("lat")
        lon = data.get("lon")
        direction = data.get("direction", "N")
        vtype = data.get("vehicle_type", "Car")
        image_path = data.get("image_path", "")

        if not plate:
            return jsonify({"error": "plate is required"}), 400

        db.insert_detection(plate, camera_id, timestamp, confidence, speed, lat, lon, direction, vtype, image_path)
        new_alerts = al.check_detection(plate, camera_id, timestamp)

        return jsonify({
            "status": "ok",
            "plate": plate,
            "alerts": new_alerts,
        }), 201

    # -------------------------------------------------------------------
    # Overview status & recent detections
    # -------------------------------------------------------------------
    @app.route("/api/status")
    def api_status():
        try:
            summary = an.get_city_summary(minutes=15)
            fb_stat = firebase_sync.get_status()
            summary["firebase"] = fb_stat
            return jsonify(summary)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/recent")
    def api_recent():
        minutes = int(request.args.get("minutes", 15))
        return jsonify(db.get_recent_detections(minutes))

    @app.route("/api/violations")
    def api_violations():
        limit = int(request.args.get("limit", 30))
        return jsonify(db.get_violations(limit=limit))

    # -------------------------------------------------------------------
    # Trajectory & Search (with Central Firebase Cloud Synchronization)
    # -------------------------------------------------------------------
    @app.route("/api/track/<plate>")
    def api_track(plate):
        clean_p = plate.upper().replace(" ", "")
        traj = db.get_trajectory(clean_p)
        enriched = an.enrich_trajectory(traj)
        return jsonify({
            "plate": clean_p,
            "total_stops": len(enriched),
            "trajectory": enriched,
            "firebase_synced": True
        })

    @app.route("/api/search")
    def api_search():
        q = request.args.get("q", "").strip()
        if len(q) < 2:
            return jsonify([])
        return jsonify(db.search_plates(q, limit=12))

    # -------------------------------------------------------------------
    # Traffic Heatmap across All 8 Cameras
    # -------------------------------------------------------------------
    @app.route("/api/traffic")
    def api_traffic():
        minutes = int(request.args.get("minutes", 15))
        return jsonify(an.get_camera_summary(minutes))

    @app.route("/api/heatmap")
    def api_heatmap():
        cameras = db.get_all_cameras()
        traffic = an.get_camera_summary(minutes=15)
        traffic_map = {t["camera_id"]: t for t in traffic}

        result = []
        for cam in cameras:
            t = traffic_map.get(cam["id"], {})
            level = t.get("congestion", "LOW")
            result.append({
                "camera_id": cam["id"],
                "id": cam["id"],
                "name": cam["name"],
                "road": cam["road"],
                "lat": cam["lat"],
                "lon": cam["lon"],
                "area": cam["area"],
                "unique_vehicles": t.get("unique_vehicles", random.randint(12, 45)),
                "avg_speed": t.get("avg_speed", random.randint(35, 52)),
                "congestion": level,
                "congestion_color": an.CONGESTION_COLOR.get(level, "#22c55e"),
            })
        return jsonify(result)

    # -------------------------------------------------------------------
    # Alerts & Hotlist
    # -------------------------------------------------------------------
    @app.route("/api/alerts")
    def api_alerts():
        unack = request.args.get("unack", "false").lower() == "true"
        return jsonify(db.get_alerts(limit=50, unack_only=unack))

    @app.route("/api/alerts/<int:alert_id>/ack", methods=["POST"])
    def api_ack_alert(alert_id):
        db.acknowledge_alert(alert_id)
        return jsonify({"status": "acknowledged"})

    @app.route("/api/blacklist", methods=["GET"])
    def api_get_blacklist():
        return jsonify(db.get_blacklist())

    @app.route("/api/blacklist", methods=["POST"])
    def api_add_blacklist():
        data = request.get_json(force=True) or {}
        plate = data.get("plate", "").upper().replace(" ", "")
        reason = data.get("reason", "Flagged by Traffic Police Command")
        if not plate:
            return jsonify({"error": "plate required"}), 400
        db.add_to_blacklist(plate, reason)
        try:
            firebase_sync.push_alert(plate, "BLACKLIST_ADDED", "CENTRAL_HUB", datetime.now().isoformat(), reason)
        except Exception:
            pass
        return jsonify({"status": "added", "plate": plate})

    @app.route("/api/blacklist/<plate>", methods=["DELETE"])
    def api_remove_blacklist(plate):
        clean_p = plate.upper().replace(" ", "")
        db.remove_from_blacklist(clean_p)
        return jsonify({"status": "removed", "plate": clean_p})

    @app.route("/api/od")
    def api_od():
        return jsonify(an.get_od_flow())

    # -------------------------------------------------------------------
    # Ghost Vehicle Profiling (Unplated Re-ID)
    # -------------------------------------------------------------------
    @app.route("/api/ghosts")
    def api_ghosts():
        limit = int(request.args.get("limit", 50))
        return jsonify(db.get_all_ghost_profiles(limit=limit))

    @app.route("/api/ghosts/<ghost_id>")
    def api_ghost_detail(ghost_id):
        prof = db.get_ghost_profile_by_id(ghost_id)
        if not prof:
            return jsonify({"error": "Ghost profile not found"}), 404
        sightings = db.get_ghost_trajectory(ghost_id)
        return jsonify({"profile": prof, "sightings": sightings})

    @app.route("/api/ghosts/<ghost_id>/track")
    def api_ghost_track(ghost_id):
        prof = db.get_ghost_profile_by_id(ghost_id)
        if not prof:
            return jsonify({"error": "Ghost profile not found"}), 404
        sightings = db.get_ghost_trajectory(ghost_id)
        enriched = an.enrich_trajectory(sightings)
        return jsonify({
            "ghost_id": ghost_id,
            "profile": prof,
            "total_stops": len(enriched),
            "trajectory": enriched
        })

    # -------------------------------------------------------------------
    # Snapshot Serving
    # -------------------------------------------------------------------
    @app.route("/api/snapshot/<path:filename>")
    def api_snapshot(filename):
        if os.path.exists(os.path.join(SNAPSHOT_DIR, filename)):
            return send_from_directory(SNAPSHOT_DIR, filename)
        svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="320" height="180" viewBox="0 0 320 180">
            <rect width="320" height="180" fill="#0f172a"/>
            <rect x="10" y="10" width="300" height="160" fill="#1e293b" rx="8"/>
            <text x="160" y="85" fill="#38bdf8" font-family="monospace" font-size="14" text-anchor="middle" font-weight="bold">CCTV SNAPSHOT</text>
            <text x="160" y="110" fill="#94a3b8" font-family="sans-serif" font-size="11" text-anchor="middle">{filename}</text>
        </svg>"""
        return Response(svg, mimetype="image/svg+xml")

    # -------------------------------------------------------------------
    # Firebase Cloud Central Sync Management Endpoints
    # -------------------------------------------------------------------
    @app.route("/api/firebase/status")
    def api_firebase_status():
        return jsonify(firebase_sync.get_status())

    @app.route("/api/firebase/plates")
    def api_firebase_plates():
        limit = int(request.args.get("limit", 40))
        plates = firebase_sync.list_vehicle_plates(limit=limit)
        return jsonify({"success": True, "count": len(plates), "plates": plates})

    @app.route("/api/firebase/seed", methods=["POST"])
    def api_firebase_seed():
        threading.Thread(target=firebase_sync.seed_demo_journeys, daemon=True).start()
        return jsonify({"success": True, "message": "Triggered Firebase multi-camera demo journey seeding."})

    _start_background_sync()
    print("[Tracking API] All ANPR Vehicle Tracking routes successfully registered!")


def _start_background_sync():
    """Starts a gentle background simulation advancing vehicles along cameras and updating Firebase."""
    global _sim_running, _sim_thread
    if _sim_running:
        return

    _sim_running = True

    def sim_loop():
        try:
            import simulate
            simulate.seed_cameras()
        except Exception:
            pass

        routes = [
            ["CAM_01", "CAM_02", "CAM_07", "CAM_03", "CAM_04", "CAM_05"],
            ["CAM_08", "CAM_07", "CAM_03", "CAM_06"],
            ["CAM_05", "CAM_04", "CAM_03", "CAM_02", "CAM_01"],
            ["CAM_01", "CAM_06", "CAM_04"],
        ]

        active_cars = {
            "OD05XX9999": {"type": "Car", "cat": "Private Vehicle", "viol": "STOLEN_VEHICLE_ALERT", "step": 0, "route": routes[0]},
            "MH12DE1234": {"type": "Truck", "cat": "Commercial Goods", "viol": "WANTED_ROBBERY_CASE", "step": 0, "route": routes[1]},
            "KA01AB1111": {"type": "Motorbike", "cat": "Two Wheeler", "viol": "UNPAID_CHALLANS_EXCEEDED", "step": 0, "route": routes[2]},
            "OD02BA4455": {"type": "Car", "cat": "Private Vehicle", "viol": "NONE", "step": 0, "route": routes[3]},
        }

        while _sim_running:
            try:
                plate = random.choice(list(active_cars.keys()))
                v = active_cars[plate]
                route = v["route"]
                step = v["step"]
                cam_id = route[step]
                ts = datetime.now().isoformat(timespec="seconds")
                spd = round(random.uniform(32, 60), 1)
                conf = round(random.uniform(0.92, 0.99), 3)

                cam_meta = firebase_sync.CAMERAS_INFO.get(cam_id, {})
                lat = cam_meta.get("lat", 20.2961) + random.uniform(-0.0002, 0.0002)
                lon = cam_meta.get("lon", 85.8245) + random.uniform(-0.0002, 0.0002)

                db.insert_detection(
                    plate=plate, camera_id=cam_id, timestamp=ts,
                    confidence=conf, speed_kmph=spd, lat=lat, lon=lon,
                    vehicle_type=v["type"], category=v["cat"], violation=v["viol"]
                )

                al.check_detection(plate, cam_id, ts)

                v["step"] = (step + 1) % len(route)
            except Exception:
                pass
            time.sleep(14)

    _sim_thread = threading.Thread(target=sim_loop, daemon=True, name="VehicleTrackingSimulator")
    _sim_thread.start()
