import { useState, useEffect, useCallback } from "react";
import { initIntersections } from "../data/intersections";

// Deterministically assign realistic traffic tiers across the 100 nodes
function getNodeTier(id, index) {
  const name = String(id || "");
  const majorHubs = ["Rasulgarh", "Jaydev Vihar", "Vani Vihar", "Master Canteen", "Acharya Vihar", "Khandagiri", "Patia Square", "Cuttack Road"];
  const isMajor = majorHubs.some(h => name.includes(h));

  const hash = Math.abs((index * 2654435761) ^ (name.length * 37));
  const roll = hash % 100;

  if (isMajor && roll < 42) return "critical";
  if (roll < 12) return "critical";  // ~12% Critical citywide
  if (roll < 50) return "medium";    // ~38% Moderate citywide
  return "low";                      // ~50% Clear citywide
}

function generateLanes(tier, prevLanes = null) {
  const directions = ["North", "East", "South", "West"];

  return directions.map((dir, dIdx) => {
    const prev = prevLanes ? prevLanes.find(l => l.direction === dir) : null;
    if (prev && prev.manualActive) return prev;

    let baseVehicles, baseSpeed;
    if (tier === "critical") {
      baseVehicles = 40 + Math.floor(Math.random() * 24); // 40-63
      baseSpeed = 18 + Math.floor(Math.random() * 12);    // 18-29 km/h
    } else if (tier === "medium") {
      baseVehicles = 20 + Math.floor(Math.random() * 16); // 20-35
      baseSpeed = 33 + Math.floor(Math.random() * 13);    // 33-45 km/h
    } else {
      baseVehicles = 7 + Math.floor(Math.random() * 12);  // 7-18
      baseSpeed = 48 + Math.floor(Math.random() * 15);    // 48-62 km/h
    }

    let vehicleCount = baseVehicles;
    let averageSpeed = baseSpeed;

    // Organic drift over time so numbers dynamically pulse
    if (prev && prev.vehicleCount > 0) {
      const isGreen = prev.light === "green";
      const delta = isGreen ? -(Math.floor(Math.random() * 5) + 2) : (Math.floor(Math.random() * 4) + 1);
      vehicleCount = Math.max(5, Math.min(78, prev.vehicleCount + delta));
      const speedOffset = Math.floor((32 - vehicleCount) * 0.4);
      averageSpeed = Math.max(15, Math.min(68, 40 + speedOffset + (Math.floor(Math.random() * 5) - 2)));
    }

    return {
      direction: dir,
      vehicleCount,
      averageSpeed,
      light: prev ? prev.light : (dIdx % 2 === 0 ? "green" : "red"),
      manualActive: false
    };
  });
}

function runAI(intersections, isInitial = false) {
  return intersections.map((int, idx) => {
    const tier = getNodeTier(int.id, idx);
    const updatedLanes = generateLanes(tier, isInitial ? null : int.lanes);

    // AI Adaptive signal switching: lane with highest queue gets green light
    const autoLanes = updatedLanes.filter(l => !l.manualActive);
    let finalLanes = updatedLanes;
    if (autoLanes.length > 0) {
      const maxLane = autoLanes.reduce((max, l) => l.vehicleCount > max.vehicleCount ? l : max, autoLanes[0]);
      finalLanes = updatedLanes.map(lane => {
        if (lane.manualActive) return lane;
        let light = "red";
        if (lane.direction === maxLane.direction) {
          light = "green";
        } else if (lane.vehicleCount > maxLane.vehicleCount * 0.72) {
          light = "yellow";
        }
        return { ...lane, light };
      });
    }

    const totalVehicles = finalLanes.reduce((s, l) => s + l.vehicleCount, 0);
    const avgSpeed = Math.round(finalLanes.reduce((s, l) => s + l.averageSpeed, 0) / finalLanes.length);

    // Realistic congestion percentage (14% - 94%)
    let congestionPct = Math.max(14, Math.min(94, Math.round((totalVehicles / 200) * 100)));
    congestionPct = Math.max(12, Math.min(95, congestionPct + (Math.floor(Math.random() * 5) - 2)));

    const status = congestionPct >= 72 ? "critical" : congestionPct >= 40 ? "medium" : "low";

    return {
      ...int,
      lanes: finalLanes,
      vehicleCount: totalVehicles,
      averageSpeed: avgSpeed,
      congestionPct,
      status
    };
  });
}

export function useSimulation() {
  const [intersections, setIntersections] = useState(() => runAI(initIntersections(), true));

  useEffect(() => {
    // Dynamic updates every 2.5 seconds so grid numbers constantly and smoothly change
    const id = setInterval(() => {
      setIntersections(prev => runAI(prev, false));
    }, 2500);
    return () => clearInterval(id);
  }, []);

  const updateLane = useCallback((intersectionId, direction, light) => {
    setIntersections(prev => prev.map(int => {
      if (int.id !== intersectionId) return int;
      return { ...int, lanes: int.lanes.map(l => l.direction===direction ? {...l, light, manualActive:true} : l) };
    }));
  }, []);

  const revertLane = useCallback((intersectionId, direction) => {
    setIntersections(prev => prev.map(int => {
      if (int.id !== intersectionId) return int;
      return { ...int, lanes: int.lanes.map(l => l.direction===direction ? {...l, light:"red", manualActive:false} : l) };
    }));
  }, []);

  const revertAll = useCallback((intersectionId) => {
    setIntersections(prev => prev.map(int => {
      if (int.id !== intersectionId) return int;
      return { ...int, lanes: int.lanes.map(l => ({...l, light:"red", manualActive:false})) };
    }));
  }, []);

  const stats = {
    avgCongestion: Math.round(intersections.reduce((s, i) => s + i.congestionPct, 0) / intersections.length),
    avgSpeed: Math.round(intersections.reduce((s, i) => s + i.averageSpeed, 0) / intersections.length),
    criticalCount: intersections.filter(i => i.status === "critical").length,
    mediumCount: intersections.filter(i => i.status === "medium").length,
    clearCount: intersections.filter(i => i.status === "low").length,
    totalNodes: intersections.length,
  };

  return { intersections, stats, updateLane, revertLane, revertAll };
}
