"""
vehicle_reid.py - Unified Cross-Camera Vehicle Re-Identification & Junction Occlusion Engine
Matches both Plated and Unplated (Ghost) vehicles across distributed CCTV cameras using:
1. Deep visual embeddings (64-D normalized vector cosine similarity)
2. Exterior forensic features (color, make/model, body subtype, aspect ratio, scratches)
3. In-cabin biometric signatures (occupant headcount, driver/passenger cultural & formal attire, dashboard idols/FASTags)
4. Junction Lead-Vehicle Bumper Occlusion Disambiguation
"""

import json
import random
import numpy as np
import database as db
import vehicle_profiler


def cosine_similarity(vec1, vec2):
    """Computes cosine similarity between two normalized feature vectors."""
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0
    try:
        a = np.array(vec1, dtype=np.float32)
        b = np.array(vec2, dtype=np.float32)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))
    except Exception:
        return 0.0


def generate_ghost_id(dom_color, body_subtype):
    """Generates a clean, human-readable Ghost Vehicle Identifier."""
    color_tag = dom_color.split()[0].upper()[:3] if dom_color else "UNK"
    type_tag = body_subtype.split()[0].upper()[:3] if body_subtype else "VEH"
    rand_num = random.randint(1000, 9999)
    return f"UNPLATED-{color_tag}-{type_tag}-{rand_num}"


def compute_fingerprint_similarity(curr, cand):
    """
    Computes a comprehensive multi-cue similarity score between a newly observed vehicle
    and a candidate profile (plated vehicle fingerprint or ghost profile).
    Returns (composite_score: float, matched_reasons: list).
    """
    reasons = []

    # 1. Base Vehicle Class (Strict: Car vs Bike vs Truck)
    curr_type = (curr.get("vehicle_type") or "Car").lower()
    cand_type = (cand.get("vehicle_type") or "Car").lower()
    if curr_type != cand_type:
        return 0.0, []

    # 2. Make & Model Similarity (Weight: 0.20)
    curr_make = (curr.get("estimated_make") or "").strip().lower()
    cand_make = (cand.get("estimated_make") or "").strip().lower()
    curr_model = (curr.get("estimated_model") or "").strip().lower()
    cand_model = (cand.get("estimated_model") or "").strip().lower()

    if curr_make and cand_make and curr_make == cand_make:
        if curr_model and cand_model and curr_model == cand_model:
            make_score = 1.0
            reasons.append(f"Matching Make/Model ({cand.get('estimated_make')} {cand.get('estimated_model')})")
        else:
            make_score = 0.65
            reasons.append(f"Matching Brand Family ({cand.get('estimated_make')})")
    elif not curr_make or not cand_make:
        make_score = 0.50
    else:
        make_score = 0.10

    # 3. Dominant Color Match (Weight: 0.20)
    curr_color = (curr.get("dominant_color") or "UNKNOWN").upper()
    cand_color = (cand.get("dominant_color") or "UNKNOWN").upper()
    if curr_color == cand_color and curr_color != "UNKNOWN":
        color_score = 1.0
        reasons.append(f"Identical Body Color ({cand_color.title()})")
    elif ("SILVER" in curr_color and "WHITE" in cand_color) or ("WHITE" in curr_color and "SILVER" in cand_color):
        color_score = 0.70
        reasons.append("High Chromatic Hue Proximity (White/Silver)")
    elif ("BLACK" in curr_color and "BLUE" in cand_color) or ("BLUE" in curr_color and "BLACK" in cand_color):
        color_score = 0.55
    else:
        color_score = 0.10

    # 4. Visual Embedding Cosine Similarity (Weight: 0.20)
    try:
        curr_emb = json.loads(curr.get("visual_embedding", "[]")) if isinstance(curr.get("visual_embedding"), str) else curr.get("visual_embedding", [])
        cand_emb = json.loads(cand.get("visual_embedding", "[]")) if isinstance(cand.get("visual_embedding"), str) else cand.get("visual_embedding", [])
    except Exception:
        curr_emb, cand_emb = [], []

    emb_sim = max(0.0, cosine_similarity(curr_emb, cand_emb))
    if emb_sim > 0.85:
        reasons.append(f"Visual Embedding Alignment ({round(emb_sim*100)}%)")

    # 5. In-Cabin Occupants & Driver Attire (Weight: 0.20)
    curr_occ = int(curr.get("occupant_count") or curr.get("total_people_count") or 1)
    cand_occ = int(cand.get("occupant_count") or 1)

    if curr_occ == cand_occ:
        occ_score = 1.0
        reasons.append(f"Matching Occupancy ({curr_occ} Person{'s' if curr_occ>1 else ''})")
    elif abs(curr_occ - cand_occ) == 1:
        occ_score = 0.50
    else:
        occ_score = 0.10

    # Attire comparison
    curr_att = (curr.get("driver_attire") or "").lower()
    cand_att = (cand.get("driver_attire") or "").lower()
    att_score = 0.50
    if curr_att and cand_att:
        # Check cultural archetype or key tokens (kurta, polo, hoodie, jacket, blue, white, etc.)
        curr_tokens = set(curr_att.replace(":", " ").replace("-", " ").split())
        cand_tokens = set(cand_att.replace(":", " ").replace("-", " ").split())
        common = curr_tokens.intersection(cand_tokens)
        if len(common) >= 2 or ("kurta" in common) or ("polo" in common) or ("hoodie" in common) or ("leather" in common):
            att_score = 1.0
            reasons.append(f"Driver Attire Match ({cand.get('driver_attire')})")
        elif len(common) >= 1:
            att_score = 0.75

    cabin_composite = 0.5 * occ_score + 0.5 * att_score

    # 6. Micro-Distinguishing Features & Dashboard Items (Weight: 0.15)
    curr_dash = (curr.get("dashboard_items") or "").lower()
    cand_dash = (cand.get("dashboard_items") or "").lower()
    dash_score = 0.50
    if curr_dash and cand_dash and "none" not in curr_dash and "none" not in cand_dash:
        dash_tokens = set(curr_dash.replace("+", " ").replace("(", " ").replace(")", " ").split())
        cand_dash_tokens = set(cand_dash.replace("+", " ").replace("(", " ").replace(")", " ").split())
        common_dash = dash_tokens.intersection(cand_dash_tokens)
        if len(common_dash) >= 2 or ("ganesha" in common_dash) or ("fastag" in common_dash) or ("beads" in common_dash) or ("bobblehead" in common_dash):
            dash_score = 1.0
            reasons.append(f"Dashboard Fingerprint Match ({cand.get('dashboard_items')})")
        elif len(common_dash) >= 1:
            dash_score = 0.75

    # 7. Body Subtype & Aspect Ratio (Weight: 0.05)
    curr_subtype = (curr.get("body_subtype") or "Passenger Car").lower()
    cand_subtype = (cand.get("body_subtype") or "Passenger Car").lower()
    subtype_score = 1.0 if curr_subtype == cand_subtype else 0.40

    composite_score = (
        0.20 * make_score +
        0.20 * color_score +
        0.20 * emb_sim +
        0.20 * cabin_composite +
        0.15 * dash_score +
        0.05 * subtype_score
    )

    return composite_score, reasons


def match_or_create_ghost(profile, camera_id, timestamp, image_path, speed_kmph=0.0):
    """
    Compares newly extracted vehicle visual profile against existing active ghost profiles.
    Returns dict with ghost_id, match_score, is_new, and profile.
    """
    active_candidates = db.get_active_ghost_candidates(limit=40)
    best_match = None
    best_score = 0.0
    best_reasons = []

    for cand in active_candidates:
        score, reasons = compute_fingerprint_similarity(profile, cand)
        if score > best_score:
            best_score = score
            best_match = cand
            best_reasons = reasons

    # Re-ID Decision Threshold (0.74 represents high confidence cross-camera match)
    if best_match and best_score >= 0.74:
        ghost_id = best_match["ghost_id"]
        db.update_ghost_last_seen(
            ghost_id=ghost_id,
            last_seen_ts=timestamp,
            last_camera=camera_id,
            new_image_path=image_path
        )
        db.insert_ghost_sighting(
            ghost_id=ghost_id,
            camera_id=camera_id,
            timestamp=timestamp,
            image_path=image_path,
            match_score=round(best_score, 3),
            speed_kmph=speed_kmph
        )
        return {
            "ghost_id": ghost_id,
            "match_score": round(best_score, 3),
            "is_new": False,
            "profile": best_match,
            "reasons": best_reasons
        }
    else:
        # Create a new Ghost Profile
        curr_color = profile.get("dominant_color", "UNKNOWN")
        curr_subtype = profile.get("body_subtype", "Passenger Car")
        new_ghost_id = generate_ghost_id(curr_color, curr_subtype)
        runner_up_json = json.dumps(profile.get("runner_up")) if profile.get("runner_up") else ""
        db.upsert_ghost_profile(
            ghost_id=new_ghost_id,
            vehicle_type=profile.get("vehicle_type", "Car"),
            body_subtype=curr_subtype,
            dominant_color=curr_color,
            secondary_color=profile.get("secondary_color", ""),
            color_hex=profile.get("color_hex", "#64748B"),
            aspect_ratio=float(profile.get("aspect_ratio", 1.0)),
            visual_embedding=profile.get("visual_embedding", "[]"),
            first_seen_ts=timestamp,
            last_seen_ts=timestamp,
            first_camera=camera_id,
            last_camera=camera_id,
            best_image_path=image_path,
            status="ACTIVE_TRACKING",
            estimated_make=profile.get("estimated_make", ""),
            estimated_model=profile.get("estimated_model", ""),
            make_confidence=profile.get("make_confidence", 0.0),
            distinguishing_features=profile.get("distinguishing_features", ""),
            runner_up=runner_up_json,
            occupant_count=profile.get("occupant_count", profile.get("in_cabin_profile", {}).get("total_people_count", 1) if isinstance(profile.get("in_cabin_profile"), dict) else 1),
            driver_attire=profile.get("driver_attire", ""),
            dashboard_items=profile.get("dashboard_items", ""),
            driving_style=profile.get("driving_style", ""),
            twin_disambiguation=profile.get("twin_disambiguation", ""),
            in_cabin_profile=json.dumps(profile.get("in_cabin_profile")) if isinstance(profile.get("in_cabin_profile"), dict) else (profile.get("in_cabin_profile") or "{}")
        )
        db.insert_ghost_sighting(
            ghost_id=new_ghost_id,
            camera_id=camera_id,
            timestamp=timestamp,
            image_path=image_path,
            match_score=1.0,
            speed_kmph=speed_kmph
        )
        return {
            "ghost_id": new_ghost_id,
            "match_score": 1.0,
            "is_new": True,
            "profile": profile,
            "reasons": ["New Plate-Less Vehicle Dossier Created"]
        }


def match_or_resolve_vehicle(profile, camera_id, timestamp, image_path, speed_kmph=0.0, is_plate_visible=True, raw_plate=None):
    """
    Unified Junction Disambiguation Router:
    1. If plate is visible -> Upsert Plated Fingerprint and check if it resolves any active Ghost vehicles.
    2. If plate is occluded/missing -> Check active PLATED vehicles first! If high similarity, resolve
       as 'OCCLUDED_PLATED_MATCH', preserving journey continuity and suppressing false felony alerts.
       Otherwise fallback to Ghost matching.
    """
    if is_plate_visible and raw_plate and "NO PLATE" not in raw_plate and "UNREADABLE" not in raw_plate:
        clean_p = raw_plate.upper().replace(" ", "")
        # A. Store/Update Plated Vehicle Fingerprint
        db.upsert_vehicle_fingerprint(
            plate=clean_p,
            vehicle_type=profile.get("vehicle_type", "Car"),
            body_subtype=profile.get("body_subtype", "Passenger Car"),
            dominant_color=profile.get("dominant_color", "UNKNOWN"),
            secondary_color=profile.get("secondary_color", ""),
            color_hex=profile.get("color_hex", "#64748B"),
            aspect_ratio=float(profile.get("aspect_ratio", 1.0)),
            visual_embedding=profile.get("visual_embedding", "[]"),
            estimated_make=profile.get("estimated_make", ""),
            estimated_model=profile.get("estimated_model", ""),
            make_confidence=profile.get("make_confidence", 0.0),
            distinguishing_features=profile.get("distinguishing_features", ""),
            occupant_count=profile.get("occupant_count", 1),
            driver_attire=profile.get("driver_attire", ""),
            passenger_attire=profile.get("passenger_attire", ""),
            dashboard_items=profile.get("dashboard_items", ""),
            driving_style=profile.get("driving_style", ""),
            in_cabin_profile=json.dumps(profile.get("in_cabin_profile")) if isinstance(profile.get("in_cabin_profile"), dict) else (profile.get("in_cabin_profile") or "{}"),
            last_seen_ts=timestamp,
            last_camera=camera_id,
            best_image_path=image_path
        )

        # B. Check Bi-directional Reconciliation: Did this vehicle have prior unplated ghost sightings?
        active_ghosts = db.get_active_ghost_candidates(limit=30)
        resolved_ghosts = []
        for g in active_ghosts:
            if g.get("status") == "RESOLVED_TO_PLATED":
                continue
            sim_score, reasons = compute_fingerprint_similarity(profile, g)
            if sim_score >= 0.76:
                db.resolve_ghost_to_plated(
                    ghost_id=g["ghost_id"],
                    plate=clean_p,
                    reason=f"Resolved to {clean_p} (Score: {round(sim_score*100)}%) after plate visible at {camera_id}"
                )
                resolved_ghosts.append({
                    "ghost_id": g["ghost_id"],
                    "match_score": round(sim_score, 3),
                    "reasons": reasons
                })

        return {
            "status": "PLATED_VERIFIED",
            "plate": clean_p,
            "resolved_ghosts": resolved_ghosts,
            "is_occluded": False
        }

    else:
        # Plate is NOT visible (Occluded behind lead vehicle in junction queue or removed)
        # 1. First: Check active PLATED vehicles in the smart city network
        active_plated = db.get_active_plated_fingerprints(limit=50)
        best_plated = None
        best_plated_score = 0.0
        best_plated_reasons = []

        for p_cand in active_plated:
            score, reasons = compute_fingerprint_similarity(profile, p_cand)
            if score > best_plated_score:
                best_plated_score = score
                best_plated = p_cand
                best_plated_reasons = reasons

        # If high match with a known plated car (>= 0.75), DISAMBIGUATE AS OCCLUDED PLATED VEHICLE!
        if best_plated and best_plated_score >= 0.75:
            matched_plate = best_plated["plate"]
            reason_str = ", ".join(best_plated_reasons) if best_plated_reasons else "Biometric visual signature match"
            occlusion_text = (
                f"Front bumper/plate occluded behind lead vehicle in junction queue. "
                f"Re-identified as {matched_plate} ({round(best_plated_score*100)}% match) via {reason_str}."
            )

            # Insert sighting into the plated vehicle's journey history
            db.insert_detection(
                plate=matched_plate,
                camera_id=camera_id,
                timestamp=timestamp,
                confidence=round(best_plated_score, 3),
                speed_kmph=speed_kmph,
                vehicle_type=best_plated.get("vehicle_type", profile.get("vehicle_type", "Car")),
                image_path=image_path,
                violation="NONE",  # False felony suppressed
                occlusion_status="OCCLUDED_BEHIND_LEAD_VEHICLE",
                occlusion_reason=occlusion_text,
                matched_plate=matched_plate,
                vehicle_profile=json.dumps(profile) if isinstance(profile, dict) else str(profile)
            )

            # Update the plated vehicle's last seen time & camera
            db.upsert_vehicle_fingerprint(
                plate=matched_plate,
                vehicle_type=best_plated.get("vehicle_type", "Car"),
                body_subtype=best_plated.get("body_subtype", "Passenger Car"),
                dominant_color=best_plated.get("dominant_color", "UNKNOWN"),
                secondary_color=best_plated.get("secondary_color", ""),
                color_hex=best_plated.get("color_hex", "#64748B"),
                aspect_ratio=float(best_plated.get("aspect_ratio", 1.0)),
                visual_embedding=best_plated.get("visual_embedding", "[]"),
                estimated_make=best_plated.get("estimated_make", ""),
                estimated_model=best_plated.get("estimated_model", ""),
                make_confidence=best_plated.get("make_confidence", 0.0),
                distinguishing_features=best_plated.get("distinguishing_features", ""),
                occupant_count=best_plated.get("occupant_count", 1),
                driver_attire=best_plated.get("driver_attire", ""),
                passenger_attire=best_plated.get("passenger_attire", ""),
                dashboard_items=best_plated.get("dashboard_items", ""),
                driving_style=best_plated.get("driving_style", ""),
                in_cabin_profile=best_plated.get("in_cabin_profile", "{}"),
                last_seen_ts=timestamp,
                last_camera=camera_id,
                best_image_path=image_path if image_path else best_plated.get("best_image_path", "")
            )

            return {
                "status": "OCCLUDED_PLATED_MATCH",
                "plate": matched_plate,
                "display_plate": f"{matched_plate} [Plate Occluded]",
                "match_score": round(best_plated_score, 3),
                "is_new": False,
                "is_occluded": True,
                "occlusion_status": "OCCLUDED_BEHIND_LEAD_VEHICLE",
                "occlusion_reason": occlusion_text,
                "reasons": best_plated_reasons,
                "matched_profile": best_plated
            }

        # 2. If not matched to any active plated vehicle, match against Ghost profiles
        ghost_res = match_or_create_ghost(profile, camera_id, timestamp, image_path, speed_kmph)
        ghost_res["status"] = "GHOST_MATCH" if not ghost_res.get("is_new") else "GHOST_NEW"
        ghost_res["is_occluded"] = False
        ghost_res["occlusion_status"] = "GENUINE_UNPLATED"
        ghost_res["occlusion_reason"] = "No matching plated or ghost vehicle found in surveillance grid."
        return ghost_res
