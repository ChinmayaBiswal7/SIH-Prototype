// Dynamic Emergency Fleet & Realistic SVG Ambulance Engine for Bhubaneswar
// Generates random emergency calls, calculates real road routes, manages dynamic vehicle life cycles, and termination on arrival.

import { BBSR_INTERSECTIONS, BBSR_INTERSECTION_MAP } from "../data/bbsrCityData";
import { findFastestEmergencyRoute } from "./routingService";

const CALLSIGN_PRESETS = [
  { prefix: "AMB-108", hospital: "Capital Hospital", color: "#ef4444", type: "ambulance" },
  { prefix: "AMB-102", hospital: "Kalinga Cardiac", color: "#ec4899", type: "ambulance" },
  { prefix: "AMB-104", hospital: "AIIMS BBSR Trauma", color: "#06b6d4", type: "ambulance" },
  { prefix: "AMB-201", hospital: "SUM Ultimate Medicare", color: "#10b981", type: "ambulance" },
  { prefix: "AMB-305", hospital: "Care Emergency Care", color: "#3b82f6", type: "ambulance" },
  { prefix: "AMB-412", hospital: "Apollo Hospital Medevac", color: "#8b5cf6", type: "ambulance" },
  { prefix: "AMB-503", hospital: "Sishu Bhawan Pediatric", color: "#f59e0b", type: "ambulance" },
  { prefix: "FIRE-01", hospital: "Central Fire & Rescue", color: "#f97316", type: "fire" },
  { prefix: "AMB-608", hospital: "Patia Quick Response", color: "#14b8a6", type: "ambulance" },
  { prefix: "AMB-714", hospital: "Khandagiri Trauma Care", color: "#6366f1", type: "ambulance" },
];

const PARAMEDIC_NAMES = [
  "Paramedic S. Mohapatra",
  "Paramedic R. Jena",
  "Paramedic P. Das",
  "Paramedic A. Pradhan",
  "Paramedic M. Nayak",
  "Paramedic D. Sahoo",
  "Paramedic K. Behera",
  "Paramedic N. Tripathy",
  "Commander B. Mishra",
];

const EMERGENCY_STATUSES = [
  "Critical Transit (Code Red)",
  "Patient Onboard — En Route",
  "Priority Trauma Dispatch",
  "Cardiac Rapid Response",
  "Emergency Medevac Transit",
];

let dispatchCounter = 108;

// Generate high-tech, realistic SVG ambulance / emergency vehicle icon HTML
export function getAmbulanceSvgHtml(unit, isCorridor = false) {
  const isFire = unit?.type === "fire";
  const bodyColor = isFire ? "#dc2626" : "#ffffff";
  const stripeColor = isFire ? "#facc15" : "#ef4444";
  const callsign = unit?.id || (isCorridor ? "CORRIDOR-108" : "AMB-108");
  const speed = unit?.speedKmh || 54;
  const color = unit?.color || (isCorridor ? "#10b981" : "#ef4444");

  return `
    <div class="modern-ambulance-marker ${isCorridor ? 'is-corridor-unit' : ''}" id="amb-marker-${unit?.id || 'corridor'}">
      <div class="amb-siren-wave" style="background: radial-gradient(circle, ${color}55 0%, transparent 70%);"></div>
      <div class="amb-vehicle-body">
        <svg viewBox="0 0 68 38" class="amb-svg" fill="none" xmlns="http://www.w3.org/2000/svg">
          <!-- Main Chassis Body -->
          <rect x="4" y="8" width="56" height="23" rx="4" fill="${bodyColor}" stroke="#1e293b" stroke-width="1.2"/>
          <!-- Front Cab Slant -->
          <path d="M44 8 H56 Q60 8 60 14 L60 27 H44 Z" fill="${isFire ? '#b91c1c' : '#f8fafc'}"/>
          <!-- Windshield with dynamic reflection -->
          <path d="M46 10 H54 Q56 10 57 15 L46 15 Z" fill="#38bdf8" opacity="0.88"/>
          <!-- Side Window -->
          <rect x="25" y="10" width="15" height="5.5" rx="1" fill="#38bdf8" opacity="0.6"/>
          <!-- Emergency Reflective Stripes -->
          <rect x="4" y="18" width="56" height="4.5" fill="${stripeColor}"/>
          <rect x="4" y="22.5" width="56" height="1.8" fill="#eab308"/>
          <!-- Medical Cross or Fire Emblem -->
          ${isFire ? `
            <circle cx="14" cy="14" r="4.5" fill="#facc15"/>
            <path d="M14 11 L15.5 13.5 H12.5 Z" fill="#b91c1c"/>
          ` : `
            <rect x="10.5" y="12.5" width="8" height="3" rx="0.5" fill="#ef4444"/>
            <rect x="13" y="10" width="3" height="8" rx="0.5" fill="#ef4444"/>
          `}
          <!-- Emergency Strobe Roof Light Bar -->
          <rect x="24" y="4" width="18" height="4" rx="2" fill="#0f172a"/>
          <circle cx="28" cy="6" r="2.4" fill="#ef4444" class="strobe-red"/>
          <circle cx="38" cy="6" r="2.4" fill="#38bdf8" class="strobe-blue"/>
          <!-- Dual Chrome Alloy Wheels -->
          <circle cx="16" cy="30.5" r="5" fill="#0f172a"/>
          <circle cx="16" cy="30.5" r="2" fill="#cbd5e1"/>
          <circle cx="48" cy="30.5" r="5" fill="#0f172a"/>
          <circle cx="48" cy="30.5" r="2" fill="#cbd5e1"/>
          <!-- Forward Headlight Beam -->
          <polygon points="60,19 72,13 72,28 60,23" fill="#fef08a" opacity="0.65" class="headlight-beam"/>
        </svg>
      </div>
      <div class="amb-marker-tag" style="border-color:${color}">
        <span class="amb-tag-id">${callsign}</span>
        <span class="amb-tag-speed">${speed} km/h</span>
      </div>
    </div>
  `;
}

// Generate a random dynamic emergency ambulance unit with real Bhubaneswar road route
export function generateDynamicEmergencyUnit(existingIds = []) {
  // Priority medical facilities for origin/destination
  const healthcareHubs = BBSR_INTERSECTIONS.filter(
    j => j.zone === "medical" || j.zone === "transport" || j.id === "CAPITAL" || j.id === "KALINGA" || j.id === "SISHU"
  );
  const randomOrigin = healthcareHubs[Math.floor(Math.random() * healthcareHubs.length)] || BBSR_INTERSECTIONS[0];

  // Pick a distinct destination anywhere across the 46 city junctions
  let randomDest = BBSR_INTERSECTIONS[Math.floor(Math.random() * BBSR_INTERSECTIONS.length)];
  while (randomDest.id === randomOrigin.id) {
    randomDest = BBSR_INTERSECTIONS[Math.floor(Math.random() * BBSR_INTERSECTIONS.length)];
  }

  // Calculate dynamic Dijkstra fastest path along real road curves
  const route = findFastestEmergencyRoute(randomOrigin.id, randomDest.id);

  const preset = CALLSIGN_PRESETS[Math.floor(Math.random() * CALLSIGN_PRESETS.length)];
  dispatchCounter++;
  const id = `${preset.type === "fire" ? "FIRE" : "AMB"}-${dispatchCounter}`;
  const driver = PARAMEDIC_NAMES[Math.floor(Math.random() * PARAMEDIC_NAMES.length)];
  const status = EMERGENCY_STATUSES[Math.floor(Math.random() * EMERGENCY_STATUSES.length)];
  const speedKmh = Math.floor(Math.random() * 14) + 48; // 48 - 62 km/h

  return {
    id,
    callsign: `${id} [${preset.hospital.split(" ")[0]}]`,
    type: preset.type,
    origin: route.startJunc.name,
    destination: route.endJunc.name,
    startNode: route.startJunc.id,
    endNode: route.endJunc.id,
    routeNodeIds: route.nodeIds,
    denseCoords: route.roadCoords,
    distanceMeters: route.distanceMeters,
    distanceKm: route.distanceKm,
    color: preset.color,
    speedKmh,
    progress: 0,
    status,
    statusBadge: "ACTIVE TRANSIT",
    driver,
    priority: "Level-1 Critical",
    etaSec: route.estimatedSeconds,
    isTerminating: false,
    terminationTime: null,
    createdAt: Date.now(),
  };
}

// Generate the initial fleet with random count (4-6 units) and staggered progress
export function createInitialRandomFleet() {
  const initialCount = Math.floor(Math.random() * 3) + 4; // 4 to 6 units
  const fleet = [];
  const existingIds = [];

  for (let i = 0; i < initialCount; i++) {
    const unit = generateDynamicEmergencyUnit(existingIds);
    // Stagger initial progress so vehicles are spread naturally along their routes
    unit.progress = Math.floor(Math.random() * 55) + 10;
    existingIds.push(unit.id);
    fleet.push(unit);
  }

  return fleet;
}
