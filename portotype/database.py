"""
database.py - Central SQLite database for City Vehicle Intelligence System
Stores every camera detection, camera metadata, blacklist, and alerts.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "traffic.db")


def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """Create all tables if they don't exist. Called once at startup."""
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS cameras (
            id    TEXT PRIMARY KEY,
            name  TEXT NOT NULL,
            road  TEXT,
            lat   REAL,
            lon   REAL,
            area  TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS detections (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            plate        TEXT    NOT NULL,
            camera_id    TEXT    NOT NULL,
            timestamp    TEXT    NOT NULL,
            confidence   REAL    DEFAULT 0.0,
            speed_kmph   REAL    DEFAULT 0.0,
            lat          REAL,
            lon          REAL,
            direction    TEXT,
            vehicle_type TEXT    DEFAULT 'unknown',
            image_path   TEXT    DEFAULT '',
            voting_data  TEXT    DEFAULT ''
        )
    """)
    try:
        c.execute("ALTER TABLE detections ADD COLUMN image_path TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE detections ADD COLUMN voting_data TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE detections ADD COLUMN env_condition TEXT DEFAULT 'NORMAL'")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE detections ADD COLUMN quality_score REAL DEFAULT 0.85")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE detections ADD COLUMN plate_color TEXT DEFAULT 'WHITE'")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE detections ADD COLUMN category TEXT DEFAULT 'Private Vehicle'")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE detections ADD COLUMN violation TEXT DEFAULT 'NONE'")
    except sqlite3.OperationalError:
        pass


    c.execute("CREATE INDEX IF NOT EXISTS idx_plate ON detections(plate)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_ts    ON detections(timestamp)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_cam   ON detections(camera_id)")

    c.execute("""
        CREATE TABLE IF NOT EXISTS blacklist (
            plate  TEXT PRIMARY KEY,
            reason TEXT DEFAULT 'Flagged'
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            plate        TEXT    NOT NULL,
            camera_id    TEXT,
            timestamp    TEXT    NOT NULL,
            alert_type   TEXT    NOT NULL,
            message      TEXT,
            acknowledged INTEGER DEFAULT 0
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS ghost_profiles (
            ghost_id         TEXT PRIMARY KEY,
            vehicle_type     TEXT NOT NULL,
            body_subtype     TEXT NOT NULL,
            dominant_color   TEXT NOT NULL,
            secondary_color  TEXT DEFAULT '',
            color_hex        TEXT DEFAULT '#64748B',
            aspect_ratio     REAL DEFAULT 1.0,
            visual_embedding TEXT DEFAULT '[]',
            first_seen_ts    TEXT NOT NULL,
            last_seen_ts     TEXT NOT NULL,
            first_camera     TEXT NOT NULL,
            last_camera      TEXT NOT NULL,
            total_sightings  INTEGER DEFAULT 1,
            best_image_path  TEXT DEFAULT '',
            status           TEXT DEFAULT 'ACTIVE_TRACKING',
            estimated_make   TEXT DEFAULT '',
            estimated_model  TEXT DEFAULT '',
            make_confidence  REAL DEFAULT 0.0,
            distinguishing_features TEXT DEFAULT '',
            runner_up        TEXT DEFAULT ''
        )
    """)

    for col, col_type in [
        ("estimated_make", "TEXT DEFAULT ''"),
        ("estimated_model", "TEXT DEFAULT ''"),
        ("make_confidence", "REAL DEFAULT 0.0"),
        ("distinguishing_features", "TEXT DEFAULT ''"),
        ("runner_up", "TEXT DEFAULT ''")
    ]:
        try:
            c.execute(f"ALTER TABLE ghost_profiles ADD COLUMN {col} {col_type}")
        except sqlite3.OperationalError:
            pass

    c.execute("""
        CREATE TABLE IF NOT EXISTS ghost_sightings (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            ghost_id    TEXT NOT NULL,
            camera_id   TEXT NOT NULL,
            timestamp   TEXT NOT NULL,
            image_path  TEXT DEFAULT '',
            match_score REAL DEFAULT 1.0,
            speed_kmph  REAL DEFAULT 0.0
        )
    """)

    c.execute("CREATE INDEX IF NOT EXISTS idx_ghost_id ON ghost_sightings(ghost_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_ghost_ts ON ghost_sightings(timestamp)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_ghost_prof_ts ON ghost_profiles(last_seen_ts)")

    # Seed all default Bhubaneswar Smart City Cameras if not present
    default_cameras = [
        ("CAM_01", "Bhubaneswar Railway Station", "Station Road", 20.2640, 85.8354, "Central"),
        ("CAM_02", "Master Canteen Square", "MG Road", 20.2683, 85.8316, "Central"),
        ("CAM_03", "Vani Vihar", "Vani Vihar Road", 20.2961, 85.8245, "North"),
        ("CAM_04", "Patia Square", "NH-16", 20.3516, 85.8189, "North"),
        ("CAM_05", "Infocity Entrance", "Infocity Road", 20.3587, 85.8149, "North"),
        ("CAM_06", "Rasulgarh Overbridge", "Ring Road", 20.2795, 85.8702, "East"),
        ("CAM_07", "Jaydev Vihar Square", "Jaydev Vihar Road", 20.3051, 85.8148, "West"),
        ("CAM_08", "Khandagiri Square", "NH-57", 20.2524, 85.7796, "West"),
        ("CAM_LIVE", "Live CCTV Edge Node", "Station Road", 20.2640, 85.8354, "Central"),
    ]
    for cam in default_cameras:
        c.execute("INSERT OR REPLACE INTO cameras (id, name, road, lat, lon, area) VALUES (?,?,?,?,?,?)", cam)

    conn.commit()
    conn.close()
    print("Database initialised with 8 connected Bhubaneswar Smart City cameras:", DB_PATH)


CAM_FALLBACKS = {
    "CAM_01": {"name": "Bhubaneswar Railway Station", "road": "Station Road", "lat": 20.2640, "lon": 85.8354, "area": "Central"},
    "CAM_02": {"name": "Master Canteen Square", "road": "MG Road", "lat": 20.2683, "lon": 85.8316, "area": "Central"},
    "CAM_03": {"name": "Vani Vihar", "road": "Vani Vihar Road", "lat": 20.2961, "lon": 85.8245, "area": "North"},
    "CAM_04": {"name": "Patia Square", "road": "NH-16", "lat": 20.3516, "lon": 85.8189, "area": "North"},
    "CAM_05": {"name": "Infocity Entrance", "road": "Infocity Road", "lat": 20.3587, "lon": 85.8149, "area": "North"},
    "CAM_06": {"name": "Rasulgarh Overbridge", "road": "Ring Road", "lat": 20.2795, "lon": 85.8702, "area": "East"},
    "CAM_07": {"name": "Jaydev Vihar Square", "road": "Jaydev Vihar Road", "lat": 20.3051, "lon": 85.8148, "area": "West"},
    "CAM_08": {"name": "Khandagiri Square", "road": "NH-57", "lat": 20.2524, "lon": 85.7796, "area": "West"},
    "CAM_LIVE": {"name": "Live CCTV Edge Node", "road": "Station Road", "lat": 20.2640, "lon": 85.8354, "area": "Central"},
}

# --- Camera helpers ---

def upsert_camera(cam_id, name, road, lat, lon, area=""):
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO cameras (id, name, road, lat, lon, area) VALUES (?,?,?,?,?,?)",
        (cam_id, name, road, lat, lon, area)
    )
    conn.commit(); conn.close()


def get_all_cameras():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM cameras ORDER BY id").fetchall()
    conn.close()
    res = [dict(r) for r in rows]
    if not res:
        for c_id, c_info in CAM_FALLBACKS.items():
            res.append({"id": c_id, "name": c_info["name"], "road": c_info["road"], "lat": c_info["lat"], "lon": c_info["lon"], "area": c_info["area"]})
    return res


# --- Detection helpers ---

def insert_detection(plate, camera_id, timestamp, confidence=0.0,
                     speed_kmph=0.0, lat=None, lon=None,
                     direction="", vehicle_type="unknown", image_path="", voting_data="",
                     env_condition="NORMAL", quality_score=0.85,
                     plate_color="WHITE", category="Private Vehicle", violation="NONE"):
    # Ensure coordinates are set from camera metadata if not provided
    cam_meta = CAM_FALLBACKS.get(camera_id, {})
    if lat is None:
        lat = cam_meta.get("lat")
    if lon is None:
        lon = cam_meta.get("lon")

    conn = get_conn()
    conn.execute("""
        INSERT INTO detections
            (plate, camera_id, timestamp, confidence, speed_kmph, lat, lon, direction, vehicle_type, image_path, voting_data, env_condition, quality_score, plate_color, category, violation)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (plate, camera_id, timestamp, confidence, speed_kmph, lat, lon, direction, vehicle_type, image_path, voting_data, env_condition, quality_score, plate_color, category, violation))
    conn.commit(); conn.close()

    # Automatically stream to Central Firebase Cloud Database (No local saves requirement)
    try:
        import firebase_sync
        firebase_sync.push_detection(
            plate=plate, camera_id=camera_id, timestamp=timestamp,
            confidence=confidence, speed_kmph=speed_kmph,
            vehicle_type=vehicle_type, image_path=image_path,
            plate_color=plate_color, category=category, violation=violation
        )
    except Exception:
        pass


def get_trajectory(plate):
    clean_p = plate.upper().replace(" ", "")
    conn = get_conn()
    rows = conn.execute("""
        SELECT d.*, c.name as camera_name, c.road, c.area, c.lat as cam_lat, c.lon as cam_lon
        FROM detections d
        LEFT JOIN cameras c ON c.id = d.camera_id
        WHERE d.plate = ?
        ORDER BY d.timestamp ASC
    """, (clean_p,)).fetchall()
    conn.close()

    results = []
    for r in rows:
        item = dict(r)
        cid = item.get("camera_id", "CAM_01")
        meta = CAM_FALLBACKS.get(cid, {})
        if not item.get("cam_lat") or not item.get("cam_lon"):
            item["cam_lat"] = item.get("lat") or meta.get("lat", 20.2961)
            item["cam_lon"] = item.get("lon") or meta.get("lon", 85.8245)
        if not item.get("camera_name"):
            item["camera_name"] = meta.get("name", cid)
        if not item.get("road"):
            item["road"] = meta.get("road", "Main Road")
        results.append(item)

    # Cloud fallback: if local container has no history, pull full journey from Firebase Firestore
    if not results:
        try:
            import firebase_sync
            fb_doc = firebase_sync.fetch_vehicle_plate(clean_p)
            if fb_doc and "sightings" in fb_doc:
                for s in fb_doc["sightings"]:
                    cid = s.get("camera_id", "CAM_01")
                    meta = CAM_FALLBACKS.get(cid, {})
                    results.append({
                        "plate": clean_p,
                        "camera_id": cid,
                        "camera_name": s.get("camera_name") or meta.get("name", cid),
                        "road": s.get("road") or meta.get("road", "Main Road"),
                        "area": meta.get("area", "Bhubaneswar"),
                        "cam_lat": float(s.get("lat") or meta.get("lat", 20.2961)),
                        "cam_lon": float(s.get("lon") or meta.get("lon", 85.8245)),
                        "timestamp": s.get("timestamp", ""),
                        "speed_kmph": float(s.get("speed_kmph", 40.0)),
                        "confidence": float(s.get("confidence", 0.95)),
                        "image_path": s.get("image_path", ""),
                        "vehicle_type": fb_doc.get("vehicle_type", "Car"),
                        "violation": s.get("violation", "NONE")
                    })
        except Exception:
            pass

    return results




def get_violations(limit=30):
    conn = get_conn()
    rows = conn.execute("""
        SELECT d.*, c.name as camera_name, c.road, c.area
        FROM detections d
        LEFT JOIN cameras c ON d.camera_id = c.id
        WHERE d.violation != 'NONE' OR d.plate LIKE '%NO PLATE%' OR d.plate LIKE '%UNREADABLE%'
        ORDER BY d.timestamp DESC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_recent_detections(minutes=15, limit=60):
    conn = get_conn()
    rows = conn.execute("""
        SELECT d.*, c.name as camera_name, c.road
        FROM detections d
        LEFT JOIN cameras c ON c.id = d.camera_id
        WHERE d.timestamp >= datetime('now', ?, 'localtime')
        ORDER BY d.timestamp DESC
    """, (f"-{minutes} minutes",)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_camera_traffic(minutes=15):
    conn = get_conn()
    rows = conn.execute("""
        SELECT d.camera_id,
               c.name AS camera_name, c.road, c.lat, c.lon, c.area,
               COUNT(DISTINCT d.plate)                                   AS unique_vehicles,
               COUNT(*)                                                   AS total_detections,
               COALESCE(AVG(CASE WHEN d.speed_kmph > 0 THEN d.speed_kmph END), 0) AS avg_speed
        FROM detections d
        LEFT JOIN cameras c ON c.id = d.camera_id
        WHERE d.timestamp >= datetime('now', ?, 'localtime')
        GROUP BY d.camera_id
        ORDER BY unique_vehicles DESC
    """, (f"-{minutes} minutes",)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_total_today():
    conn = get_conn()
    row = conn.execute("""
        SELECT COUNT(DISTINCT plate) AS unique_plates,
               COUNT(*)              AS total_detections
        FROM detections
        WHERE timestamp >= date('now', 'localtime')
    """).fetchone()
    conn.close()
    return dict(row)


def get_od_patterns(limit=10):
    conn = get_conn()
    rows = conn.execute("""
        WITH numbered AS (
            SELECT plate, camera_id, timestamp,
                   ROW_NUMBER() OVER (PARTITION BY plate ORDER BY timestamp) AS rn
            FROM detections
        )
        SELECT a.camera_id AS origin,
               b.camera_id AS destination,
               COUNT(*)    AS trips
        FROM numbered a
        JOIN numbered b ON a.plate = b.plate AND b.rn = a.rn + 1
        GROUP BY origin, destination
        ORDER BY trips DESC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def search_plates(query, limit=20):
    clean_q = query.strip().upper().replace(" ", "")
    conn = get_conn()
    rows = conn.execute("""
        SELECT DISTINCT plate FROM detections
        WHERE plate LIKE ?
        ORDER BY plate LIMIT ?
    """, (f"%{clean_q}%", limit)).fetchall()
    conn.close()
    results = [r["plate"] for r in rows]

    if len(results) < limit:
        try:
            import firebase_sync
            fb_plates = firebase_sync.list_vehicle_plates(limit=30)
            for p_doc in fb_plates:
                p_str = p_doc.get("plate", "")
                if clean_q in p_str.replace(" ", "") and p_str not in results:
                    results.append(p_str)
                    if len(results) >= limit:
                        break
        except Exception:
            pass

    return results



# --- Blacklist helpers ---

def add_to_blacklist(plate, reason="Flagged"):
    p = plate.upper().replace(" ", "")
    conn = get_conn()
    conn.execute("INSERT OR REPLACE INTO blacklist (plate, reason) VALUES (?,?)", (p, reason))
    conn.commit(); conn.close()


def remove_from_blacklist(plate):
    p = plate.upper().replace(" ", "")
    conn = get_conn()
    conn.execute("DELETE FROM blacklist WHERE plate=?", (p,))
    conn.commit(); conn.close()


def get_blacklist():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM blacklist ORDER BY plate").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def is_blacklisted(plate):
    p = plate.upper().replace(" ", "")
    conn = get_conn()
    row = conn.execute("SELECT reason FROM blacklist WHERE plate=?", (p,)).fetchone()
    conn.close()
    return dict(row) if row else None


# --- Alert helpers ---

def insert_alert(plate, camera_id, timestamp, alert_type, message):
    conn = get_conn()
    conn.execute("""
        INSERT INTO alerts (plate, camera_id, timestamp, alert_type, message)
        VALUES (?,?,?,?,?)
    """, (plate, camera_id, timestamp, alert_type, message))
    conn.commit(); conn.close()


def get_alerts(limit=50, unack_only=False):
    conn = get_conn()
    where = "WHERE acknowledged=0" if unack_only else ""
    rows = conn.execute(
        f"SELECT * FROM alerts {where} ORDER BY timestamp DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def acknowledge_alert(alert_id):
    conn = get_conn()
    conn.execute("UPDATE alerts SET acknowledged=1 WHERE id=?", (alert_id,))
    conn.commit(); conn.close()


# --- Ghost / Plate-less Vehicle Re-ID helpers ---

def upsert_ghost_profile(ghost_id, vehicle_type, body_subtype, dominant_color,
                         secondary_color="", color_hex="#64748B", aspect_ratio=1.0,
                         visual_embedding="[]", first_seen_ts="", last_seen_ts="",
                         first_camera="", last_camera="", total_sightings=1,
                         best_image_path="", status="ACTIVE_TRACKING",
                         estimated_make="", estimated_model="", make_confidence=0.0,
                         distinguishing_features="", runner_up=""):
    conn = get_conn()
    conn.execute("""
        INSERT INTO ghost_profiles
            (ghost_id, vehicle_type, body_subtype, dominant_color, secondary_color,
             color_hex, aspect_ratio, visual_embedding, first_seen_ts, last_seen_ts,
             first_camera, last_camera, total_sightings, best_image_path, status,
             estimated_make, estimated_model, make_confidence, distinguishing_features, runner_up)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(ghost_id) DO UPDATE SET
            last_seen_ts = excluded.last_seen_ts,
            last_camera = excluded.last_camera,
            total_sightings = ghost_profiles.total_sightings + 1,
            best_image_path = CASE WHEN excluded.best_image_path != '' THEN excluded.best_image_path ELSE ghost_profiles.best_image_path END,
            estimated_make = CASE WHEN excluded.estimated_make != '' THEN excluded.estimated_make ELSE ghost_profiles.estimated_make END,
            estimated_model = CASE WHEN excluded.estimated_model != '' THEN excluded.estimated_model ELSE ghost_profiles.estimated_model END,
            make_confidence = CASE WHEN excluded.make_confidence > 0 THEN excluded.make_confidence ELSE ghost_profiles.make_confidence END,
            distinguishing_features = CASE WHEN excluded.distinguishing_features != '' THEN excluded.distinguishing_features ELSE ghost_profiles.distinguishing_features END,
            runner_up = CASE WHEN excluded.runner_up != '' THEN excluded.runner_up ELSE ghost_profiles.runner_up END
    """, (ghost_id, vehicle_type, body_subtype, dominant_color, secondary_color,
          color_hex, aspect_ratio, visual_embedding, first_seen_ts, last_seen_ts,
          first_camera, last_camera, total_sightings, best_image_path, status,
          estimated_make, estimated_model, make_confidence, distinguishing_features, runner_up))
    conn.commit(); conn.close()


def update_ghost_last_seen(ghost_id, last_seen_ts, last_camera, new_image_path=""):
    conn = get_conn()
    conn.execute("""
        UPDATE ghost_profiles
        SET last_seen_ts = ?,
            last_camera = ?,
            total_sightings = total_sightings + 1,
            best_image_path = CASE WHEN ? != '' THEN ? ELSE best_image_path END
        WHERE ghost_id = ?
    """, (last_seen_ts, last_camera, new_image_path, new_image_path, ghost_id))
    conn.commit(); conn.close()


def insert_ghost_sighting(ghost_id, camera_id, timestamp, image_path="", match_score=1.0, speed_kmph=0.0):
    conn = get_conn()
    conn.execute("""
        INSERT INTO ghost_sightings
            (ghost_id, camera_id, timestamp, image_path, match_score, speed_kmph)
        VALUES (?,?,?,?,?,?)
    """, (ghost_id, camera_id, timestamp, image_path, match_score, speed_kmph))
    conn.commit(); conn.close()


def get_all_ghost_profiles(limit=50):
    conn = get_conn()
    rows = conn.execute("""
        SELECT * FROM ghost_profiles
        ORDER BY last_seen_ts DESC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_ghost_profile_by_id(ghost_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM ghost_profiles WHERE ghost_id=?", (ghost_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_active_ghost_candidates(limit=40):
    conn = get_conn()
    rows = conn.execute("""
        SELECT * FROM ghost_profiles
        ORDER BY last_seen_ts DESC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_ghost_trajectory(ghost_id):
    conn = get_conn()
    rows = conn.execute("""
        SELECT s.*, c.name as camera_name, c.road, c.lat, c.lon, c.area
        FROM ghost_sightings s
        LEFT JOIN cameras c ON s.camera_id = c.id
        WHERE s.ghost_id = ?
        ORDER BY s.timestamp ASC
    """, (ghost_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


if __name__ == "__main__":
    init_db()

