// ── Simulation Play/Pause UI Sync ──
function updatePlayPauseUI(running) {
  const btnStart = document.getElementById('btn-start');
  const btnPause = document.getElementById('btn-pause');
  if (!btnStart || !btnPause) return;
  if (running) {
    btnStart.className = 'btn btn-primary active';
    btnPause.className = 'btn';
  } else {
    btnStart.className = 'btn';
    btnPause.className = 'btn btn-pause-active';
  }
}

const canvas = document.getElementById('simCanvas');
    const ctx = canvas.getContext('2d');
    let width, height;

    let view = {
      x: 0,
      y: 0,
      scale: 1.35,
      isDragging: false,
      startX: 0,
      startY: 0
    };

    let roadnet = null;
    let simState = null;
    let roadGeom = {};
    let intersections = {};
    let selectedJunction = "J3";
    let isIncidentActive = false;
    let gridInitialized = false;

    const EW_CORRIDOR_ROADS = new Set([
      'road_VW1_J1', 'road_J1_VW1',
      'road_J1_J3', 'road_J3_J1',
      'road_J3_J4', 'road_J4_J3',
      'road_J4_VE4', 'road_VE4_J4'
    ]);

    const VEHICLE_COLORS = [
      '#38bdf8', '#22c55e', '#eab308', '#f97316', '#a855f7', '#ec4899', '#06b6d4', '#f8fafc', '#64748b'
    ];

    function hashColor(str) {
      let hash = 0;
      for (let i = 0; i < str.length; i++) hash = str.charCodeAt(i) + ((hash << 5) - hash);
      return VEHICLE_COLORS[Math.abs(hash) % VEHICLE_COLORS.length];
    }

    function resize() {
      width = window.innerWidth;
      height = window.innerHeight;
      canvas.width = width * window.devicePixelRatio;
      canvas.height = height * window.devicePixelRatio;
      ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
    }
    window.addEventListener('resize', resize);
    resize();

    function centerView() {
      view.scale = 1.35;
      view.x = (width / 2) - 300 * view.scale;
      view.y = (height / 2) - 300 * view.scale;
    }
    centerView();

    function worldToScreen(wx, wy) {
      return {
        x: wx * view.scale + view.x,
        y: (600 - wy) * view.scale + view.y
      };
    }

    function screenToWorld(sx, sy) {
      return {
        x: (sx - view.x) / view.scale,
        y: 600 - (sy - view.y) / view.scale
      };
    }

    async function loadRoadnet() {
      try {
        let res;
        try {
          res = await fetch('/api/roadnet');
          if (!res.ok) throw new Error();
        } catch {
          res = await fetch('./roadnet_5j.json');
        }
        roadnet = await res.json();

        roadnet.intersections.forEach(j => {
          intersections[j.id] = {
            ...j,
            pos: { x: j.point.x, y: j.point.y }
          };
        });

        roadnet.roads.forEach(r => {
          const p1 = r.points[0];
          const p2 = r.points[r.points.length - 1];
          const dx = p2.x - p1.x;
          const dy = p2.y - p1.y;
          const len = Math.sqrt(dx*dx + dy*dy);
          const angle = Math.atan2(dy, dx);

          roadGeom[r.id] = {
            p1, p2, dx, dy, len, angle,
            lanes: r.lanes.length
          };
        });

        initDashboardGridOnce();
      } catch (err) {}
    }

    // Build the Dashboard Grid cards ONCE so they never flicker or drop clicks!
    function initDashboardGridOnce() {
      if (gridInitialized) return;
      const grid = document.getElementById('modal-agent-grid');
      const jids = ['J1', 'J2', 'J3', 'J4', 'J5'];
      let html = '';
      jids.forEach(jid => {
        html += `
          <div class="agent-summary-card" id="card-${jid}" onclick="selectAndClose('${jid}')">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
              <span style="font-weight:700; font-size:14px;">${jid}</span>
              <span id="ag-phase-${jid}" style="font-size:10px; font-weight:700; color:#22c55e;">EW</span>
            </div>
            <div style="font-size:11px; color:var(--text-muted); display:flex; flex-direction:column; gap:3px;">
              <div>Density: <b id="ag-dens-${jid}" style="color:#fff;">0%</b></div>
              <div>Queued: <b id="ag-queue-${jid}" style="color:#fff;">0 cars</b></div>
              <div>Downstream Cap: <b id="ag-cap-${jid}" style="color:#22c55e;">100%</b></div>
            </div>
          </div>
        `;
      });
      grid.innerHTML = html;
      gridInitialized = true;
    }

    // ── High-Performance 60 FPS Dead Reckoning & Smooth Motion Engine ──
    const smoothVehicles = new Map();
    let smoothAmbDist = 0;
    let lastAnimTime = performance.now();
    let lastUserActionTime = 0;

    // ── Clean SUMO 2D Renderer (60 FPS Butter Smooth) ──
    function render() {
      const now = performance.now();
      const dt = Math.min((now - lastAnimTime) / 1000, 0.05);
      lastAnimTime = now;

      ctx.clearRect(0, 0, width, height);
      ctx.fillStyle = '#080b11';
      ctx.fillRect(0, 0, width, height);

      ctx.strokeStyle = 'rgba(255, 255, 255, 0.02)';
      ctx.lineWidth = 1;
      const gridSize = 60 * view.scale;
      const startX = (view.x % gridSize);
      const startY = (view.y % gridSize);

      for (let x = startX; x < width; x += gridSize) {
        ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, height); ctx.stroke();
      }
      for (let y = startY; y < height; y += gridSize) {
        ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(width, y); ctx.stroke();
      }

      if (!roadnet) return;

      const phases = simState?.tl_phases || {};
      const amb = simState?.ambulance;
      const isAmbulanceActive = amb && amb.active;
      const incidents = simState?.active_incidents || [];

      // 1. Draw Clean Asphalt Roads (or Glowing Emerald Green Corridor)
      roadnet.roads.forEach(r => {
        const g = roadGeom[r.id];
        if (!g) return;

        const s = worldToScreen(g.p1.x, g.p1.y);
        const e = worldToScreen(g.p2.x, g.p2.y);

        const roadW = 20 * view.scale;
        const offsetPx = 8 * view.scale;
        const offX = -Math.sin(g.angle) * offsetPx;
        const offY = Math.cos(g.angle) * offsetPx;

        const sx = s.x + offX;
        const sy = s.y + offY;
        const ex = e.x + offX;
        const ey = e.y + offY;

        const isCorridorRoad = isAmbulanceActive && EW_CORRIDOR_ROADS.has(r.id);

        if (isCorridorRoad) {
          ctx.strokeStyle = '#15803d';
          ctx.lineWidth = roadW;
          ctx.lineCap = 'butt';
          ctx.shadowColor = '#22c55e';
          ctx.shadowBlur = 12;
          ctx.beginPath();
          ctx.moveTo(sx, sy);
          ctx.lineTo(ex, ey);
          ctx.stroke();
          ctx.shadowBlur = 0;
        } else {
          ctx.strokeStyle = '#181d28';
          ctx.lineWidth = roadW;
          ctx.lineCap = 'butt';
          ctx.beginPath();
          ctx.moveTo(sx, sy);
          ctx.lineTo(ex, ey);
          ctx.stroke();
        }

        ctx.strokeStyle = isCorridorRoad ? '#4ade80' : 'rgba(255, 255, 255, 0.16)';
        ctx.lineWidth = isCorridorRoad ? 2.0 : 1.2;
        const borderOff = (roadW / 2);
        const bX = -Math.sin(g.angle) * borderOff;
        const bY = Math.cos(g.angle) * borderOff;

        ctx.beginPath();
        ctx.moveTo(sx + bX, sy + bY);
        ctx.lineTo(ex + bX, ey + bY);
        ctx.moveTo(sx - bX, sy - bY);
        ctx.lineTo(ex - bX, ey - bY);
        ctx.stroke();

        ctx.strokeStyle = isCorridorRoad ? '#86efac' : 'rgba(255, 255, 255, 0.3)';
        ctx.lineWidth = 1;
        ctx.setLineDash([8 * view.scale, 8 * view.scale]);
        ctx.beginPath();
        ctx.moveTo(sx, sy);
        ctx.lineTo(ex, ey);
        ctx.stroke();
        ctx.setLineDash([]);

        const mx = (sx + ex) / 2;
        const my = (sy + ey) / 2;
        ctx.save();
        ctx.translate(mx, my);
        ctx.rotate(g.angle + Math.PI/2);
        ctx.fillStyle = isCorridorRoad ? '#bbf7d0' : 'rgba(255, 255, 255, 0.2)';
        ctx.font = `bold ${8 * view.scale}px sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText('▲', 0, 0);
        ctx.restore();
      });

      // 2. Draw Intersections
      roadnet.intersections.forEach(j => {
        const sc = worldToScreen(j.point.x, j.point.y);
        const jSize = (j.virtual ? 14 : 36) * view.scale;
        const isReal = !j.virtual;

        if (isReal) {
          const phInfo = phases[j.id];
          const isEWGreen = phInfo?.phase_idx === 0;
          const isYellow = phInfo?.is_yellow;

          ctx.fillStyle = (isAmbulanceActive && (j.id === 'J1' || j.id === 'J3' || j.id === 'J4')) ? '#064e3b' : '#141824';
          ctx.strokeStyle = selectedJunction === j.id ? 'rgba(56, 189, 248, 0.85)' : 'rgba(255, 255, 255, 0.15)';
          ctx.lineWidth = selectedJunction === j.id ? 2.5 : 1.5;
          ctx.beginPath();
          ctx.roundRect(sc.x - jSize/2, sc.y - jSize/2, jSize, jSize, 6);
          ctx.fill();
          ctx.stroke();

          const armLen = jSize / 2;
          const zebraW = 5 * view.scale;

          function drawZebra(zx, zy, ang) {
            ctx.save();
            ctx.translate(zx, zy);
            ctx.rotate(ang);
            ctx.fillStyle = '#dc2626';
            ctx.fillRect(-10 * view.scale, -zebraW/2, 20 * view.scale, 2);
            ctx.fillRect(-10 * view.scale, zebraW/2 - 2, 20 * view.scale, 2);
            ctx.fillStyle = '#ffffff';
            for (let i = -8; i <= 8; i += 4) {
              ctx.fillRect(i * view.scale, -zebraW/2, 2 * view.scale, zebraW);
            }
            ctx.restore();
          }

          drawZebra(sc.x - armLen - 4, sc.y, Math.PI/2);
          drawZebra(sc.x + armLen + 4, sc.y, Math.PI/2);
          drawZebra(sc.x, sc.y - armLen - 4, 0);
          drawZebra(sc.x, sc.y + armLen + 4, 0);

          function drawStopBar(bx, by, ang, isGreen) {
            ctx.save();
            ctx.translate(bx, by);
            ctx.rotate(ang);
            const color = isYellow ? '#eab308' : isGreen ? '#22c55e' : '#ef4444';
            ctx.fillStyle = color;
            ctx.shadowColor = color;
            ctx.shadowBlur = 6;
            ctx.fillRect(-8 * view.scale, -1.5 * view.scale, 16 * view.scale, 3 * view.scale);
            ctx.shadowBlur = 0;
            ctx.restore();
          }

          drawStopBar(sc.x - armLen - 1, sc.y, Math.PI/2, isEWGreen);
          drawStopBar(sc.x + armLen + 1, sc.y, Math.PI/2, isEWGreen);
          drawStopBar(sc.x, sc.y - armLen - 1, 0, !isEWGreen);
          drawStopBar(sc.x, sc.y + armLen + 1, 0, !isEWGreen);

          ctx.fillStyle = '#f8fafc';
          ctx.font = `bold ${10 * view.scale}px sans-serif`;
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillText(j.id, sc.x, sc.y);

          const tagCol = isYellow ? '#eab308' : isEWGreen ? '#22c55e' : '#38bdf8';
          ctx.font = `bold ${8 * view.scale}px sans-serif`;
          ctx.fillStyle = tagCol;
          ctx.fillText(isYellow ? 'YELLOW' : isEWGreen ? 'EW GREEN' : 'NS GREEN', sc.x, sc.y - jSize/2 - 10);
        } else {
          ctx.fillStyle = '#1e293b';
          ctx.strokeStyle = 'rgba(255,255,255,0.1)';
          ctx.beginPath();
          ctx.arc(sc.x, sc.y, 5 * view.scale, 0, Math.PI * 2);
          ctx.fill();
          ctx.stroke();
        }
      });

      // 3. Draw Active Accident Scene & Blockade on the specific blocked lane
      incidents.forEach(inc => {
        if (!inc.active) return;
        const g = roadGeom[inc.road];
        if (!g) return;

        const wx = (g.p1.x + g.p2.x) / 2;
        const wy = (g.p1.y + g.p2.y) / 2;
        const sc = worldToScreen(wx, wy);

        const offsetPx = 8 * view.scale;
        const offX = -Math.sin(g.angle) * offsetPx;
        const offY = Math.cos(g.angle) * offsetPx;

        const ax = sc.x + offX;
        const ay = sc.y + offY;

        ctx.save();
        ctx.translate(ax, ay);

        const flash = Math.floor(Date.now() / 250) % 2 === 0;
        ctx.fillStyle = flash ? 'rgba(239, 68, 68, 0.4)' : 'rgba(234, 179, 8, 0.4)';
        ctx.beginPath();
        ctx.arc(0, 0, 14 * view.scale, 0, Math.PI * 2);
        ctx.fill();

        ctx.fillStyle = '#f97316';
        ctx.save();
        ctx.rotate(0.4);
        ctx.fillRect(-5 * view.scale, -3 * view.scale, 10 * view.scale, 6 * view.scale);
        ctx.restore();

        ctx.fillStyle = '#ef4444';
        ctx.save();
        ctx.rotate(-0.35);
        ctx.fillRect(-4 * view.scale, -2 * view.scale, 9 * view.scale, 5 * view.scale);
        ctx.restore();

        ctx.fillStyle = '#eab308';
        ctx.fillRect(-12 * view.scale, -8 * view.scale, 24 * view.scale, 3 * view.scale);
        ctx.fillStyle = '#000000';
        for (let i = -10; i <= 10; i += 6) {
          ctx.fillRect(i * view.scale, -8 * view.scale, 3 * view.scale, 3 * view.scale);
        }

        ctx.font = `bold ${9 * view.scale}px sans-serif`;
        ctx.fillStyle = '#ef4444';
        ctx.textAlign = 'center';
        ctx.fillText('⚠️ ROAD BLOCKED: ACCIDENT', 0, -14 * view.scale);

        ctx.restore();
      });

      // 3b. Draw J3 North Exit Barricade & Detour Signage during Active Accident
      if (isIncidentActive && intersections['J3']) {
        const j3sc = worldToScreen(intersections['J3'].point.x, intersections['J3'].point.y);
        
        // No Entry Barricade at North Exit of J3
        ctx.save();
        ctx.translate(j3sc.x + (8 * view.scale), j3sc.y - (18 * view.scale));
        
        // Red/White Striped Barricade
        ctx.fillStyle = '#dc2626';
        ctx.fillRect(-10 * view.scale, -2 * view.scale, 20 * view.scale, 4 * view.scale);
        ctx.fillStyle = '#ffffff';
        for (let i = -8; i <= 8; i += 4) {
          ctx.fillRect(i * view.scale, -2 * view.scale, 2 * view.scale, 4 * view.scale);
        }
        
        // No Entry Round Sign
        ctx.fillStyle = '#dc2626';
        ctx.beginPath();
        ctx.arc(0, -7 * view.scale, 5 * view.scale, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillStyle = '#ffffff';
        ctx.fillRect(-3 * view.scale, -8 * view.scale, 6 * view.scale, 2 * view.scale);
        
        ctx.restore();

        // Glowing Detour Signage at J3 (Pointing Left to J1 and Right to J4)
        ctx.save();
        ctx.translate(j3sc.x, j3sc.y + (28 * view.scale));
        ctx.fillStyle = '#22c55e';
        ctx.shadowColor = '#22c55e';
        ctx.shadowBlur = 8;
        ctx.font = `bold ${8 * view.scale}px sans-serif`;
        ctx.textAlign = 'center';
        ctx.fillText('⬅️ DETOUR VIA J1 & J4 ➡️', 0, 0);
        ctx.shadowBlur = 0;
        ctx.restore();
      }

      // 4. Draw 2D Vehicles with Butter-Smooth 60 FPS Continuous Motion & Detour Logic
      const vehList = (simState?.vehicles && simState.vehicles.length > 0) 
        ? simState.vehicles 
        : clientSim.vehicles;

      if (vehList && vehList.length > 0) {
        vehList.forEach(v => {
          let road = v.road;
          if (!road) return;

          let serverDist = parseFloat(v.distance) || 0;
          let spd = parseFloat(v.speed) || 0;
          let isBraking = spd < 0.5;

          // Continuous 60 FPS dead reckoning between server ticks
          let vSmooth = smoothVehicles.get(v.id);
          if (!vSmooth || vSmooth.road !== road) {
            vSmooth = { road: road, dist: serverDist, speed: spd };
            smoothVehicles.set(v.id, vSmooth);
          } else {
            vSmooth.speed = spd;
            if (simState?.running || clientSim.running) {
              vSmooth.dist += vSmooth.speed * dt;
              // Smooth exponential blend to authoritative position (eliminates jitter)
              const err = serverDist - vSmooth.dist;
              if (Math.abs(err) > 30) {
                vSmooth.dist = serverDist;
              } else {
                vSmooth.dist += err * 0.15;
              }
            } else {
              vSmooth.dist = serverDist;
            }
          }

          let dist = vSmooth.dist;

          // ACTIVE ACCIDENT DETOUR: Prevent cars from entering road_J3_J2
          if (isIncidentActive) {
            if (road === 'road_J3_J2') {
              // Cars entering J3 towards North are DETOURED onto road_J3_J1 (West/Left) or road_J3_J4 (East/Right)
              if (dist < 45) {
                const charCode = v.id.charCodeAt(v.id.length - 1) || 0;
                road = (charCode % 2 === 0) ? 'road_J3_J4' : 'road_J3_J1';
              } else {
                // Cars already caught near the crash stop completely before the barrier
                const crashStopLine = 75;
                if (dist > crashStopLine) {
                  dist = crashStopLine;
                  isBraking = true;
                }
              }
            }
          }

          const g = roadGeom[road];
          if (!g || g.len === 0) return;

          dist = Math.min(Math.max(dist, 0), g.len);
          const t = dist / g.len;

          const wx = g.p1.x + t * g.dx;
          const wy = g.p1.y + t * g.dy;
          const sc = worldToScreen(wx, wy);

          const offsetPx = 8 * view.scale;
          const offX = -Math.sin(g.angle) * offsetPx;
          const offY = Math.cos(g.angle) * offsetPx;

          const vx = sc.x + offX;
          const vy = sc.y + offY;

          const vehColor = hashColor(v.id);

          ctx.save();
          ctx.translate(vx, vy);
          ctx.rotate(g.angle + Math.PI/2);

          const carW = 4.8 * view.scale;
          const carL = 8.5 * view.scale;

          ctx.fillStyle = vehColor;
          ctx.beginPath();
          ctx.roundRect(-carW/2, -carL/2, carW, carL, 2);
          ctx.fill();

          ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
          ctx.fillRect(-carW/2 + 0.8, -carL/4, carW - 1.6, carL/3.2);

          if (!isBraking) {
            ctx.fillStyle = '#fef08a';
            ctx.fillRect(-carW/2 + 0.5, -carL/2, 1.2, 1.2);
            ctx.fillRect(carW/2 - 1.7, -carL/2, 1.2, 1.2);
          }

          ctx.fillStyle = isBraking ? '#ff1111' : '#660000';
          ctx.fillRect(-carW/2 + 0.5, carL/2 - 1, 1.3, 1);
          ctx.fillRect(carW/2 - 1.8, carL/2 - 1, 1.3, 1);

          ctx.restore();
        });
      }

      // 5. Draw Ambulance with 60 FPS Motion Interpolation
      const isAmbActive = (amb && amb.active) || clientSim.ambulance.active;
      const ambData = (amb && amb.active) ? amb : clientSim.ambulance;

      if (isAmbActive && ambData.current_road) {
        const g = roadGeom[ambData.current_road];
        if (g) {
          let serverDist = parseFloat(ambData.road_dist) || 0;
          if (simState?.running || clientSim.running) {
            smoothAmbDist += 7.5 * dt;
            const err = serverDist - smoothAmbDist;
            if (Math.abs(err) > 30) smoothAmbDist = serverDist;
            else smoothAmbDist += err * 0.15;
          } else {
            smoothAmbDist = serverDist;
          }

          const dist = Math.min(Math.max(smoothAmbDist, 0), g.len);
          const t = dist / g.len;
          const wx = g.p1.x + t * g.dx;
          const wy = g.p1.y + t * g.dy;
          const sc = worldToScreen(wx, wy);

          const offsetPx = 8 * view.scale;
          const offX = -Math.sin(g.angle) * offsetPx;
          const offY = Math.cos(g.angle) * offsetPx;
          const ax = sc.x + offX;
          const ay = sc.y + offY;

          ctx.save();
          ctx.translate(ax, ay);
          ctx.rotate(g.angle + Math.PI/2);

          const ambW = 6.0 * view.scale;
          const ambL = 12.0 * view.scale;

          ctx.fillStyle = '#ffffff';
          ctx.shadowColor = '#38bdf8';
          ctx.shadowBlur = 10;
          ctx.beginPath();
          ctx.roundRect(-ambW/2, -ambL/2, ambW, ambL, 3);
          ctx.fill();
          ctx.shadowBlur = 0;

          ctx.fillStyle = '#0f172a';
          ctx.fillRect(-ambW/2 + 1, -ambL/4, ambW - 2, ambL/3.5);

          ctx.fillStyle = '#dc2626';
          ctx.fillRect(-1 * view.scale, 0, 2 * view.scale, 4 * view.scale);
          ctx.fillRect(-2 * view.scale, 1 * view.scale, 4 * view.scale, 2 * view.scale);

          const flash = Math.floor(Date.now() / 150) % 2 === 0;
          ctx.fillStyle = flash ? '#ef4444' : '#38bdf8';
          ctx.shadowColor = ctx.fillStyle;
          ctx.shadowBlur = 10;
          ctx.fillRect(-ambW/2 + 1, -ambL/2 - 2, 2 * view.scale, 2 * view.scale);

          ctx.fillStyle = flash ? '#38bdf8' : '#ef4444';
          ctx.shadowColor = ctx.fillStyle;
          ctx.fillRect(ambW/2 - 3, -ambL/2 - 2, 2 * view.scale, 2 * view.scale);
          ctx.shadowBlur = 0;

          ctx.restore();

          ctx.font = `bold ${9 * view.scale}px sans-serif`;
          ctx.fillStyle = '#ef4444';
          ctx.textAlign = 'center';
          ctx.fillText('🚨 AMBULANCE', ax, ay - 16);
        }
      }
    }

    // Standalone client simulation state for 5-junction network (used when Python is not running)
    const CLIENT_ROADS = [
      "road_VW1_J1", "road_J1_VW1", "road_J1_J3", "road_J3_J1",
      "road_VN2_J2", "road_J2_VN2", "road_J2_J3", "road_J3_J2",
      "road_J3_J4", "road_J4_J3", "road_VE4_J4", "road_J4_VE4",
      "road_VS5_J5", "road_J5_VS5", "road_J5_J3", "road_J3_J5",
    ];

    let clientSim = {
      step: 0,
      running: true,
      ambulance: { active: false, current_road: "road_VW1_J1", progress_m: 0, road_dist: 0 },
      active_incidents: [],
      vehicles: Array.from({ length: 38 }, (_, i) => ({
        id: `veh_${i}`,
        road: CLIENT_ROADS[i % CLIENT_ROADS.length],
        distance: Math.random() * 180,
        speed: 6.5 + Math.random() * 7.5
      }))
    };

    function stepClientSim() {
      if (!clientSim.running) return;
      clientSim.step++;

      clientSim.vehicles.forEach(v => {
        v.distance += v.speed * 0.4;
        if (v.distance > 195) {
          v.distance = 0;
          v.road = CLIENT_ROADS[Math.floor(Math.random() * CLIENT_ROADS.length)];
        }
      });

      if (clientSim.ambulance.active) {
        clientSim.ambulance.progress_m += 4.5;
        const ambRoads = ["road_VW1_J1", "road_J1_J3", "road_J3_J4", "road_J4_VE4"];
        const curIdx = ambRoads.indexOf(clientSim.ambulance.current_road);
        if (clientSim.ambulance.progress_m > 190) {
          clientSim.ambulance.progress_m = 0;
          if (curIdx >= 0 && curIdx < ambRoads.length - 1) {
            clientSim.ambulance.current_road = ambRoads[curIdx + 1];
          } else {
            clientSim.ambulance.active = false;
          }
        }
      }
    }

    // ── Flicker-Free Telemetry Updating (Direct DOM mutation) ──
    async function updateTelemetry() {
      // In Full City mode, CitySim handles all HUD metrics directly — skip polling mini-sim
      if (isCityMode) return;

      try {
        const res = await fetch('/api/state');
        if (!res.ok) throw new Error();
        simState = await res.json();
      } catch (err) {
        // Standalone browser simulation fallback
        stepClientSim();
        const jids = ['J1', 'J2', 'J3', 'J4', 'J5'];
        const tl_phases = {};
        const agents = {};

        jids.forEach((jid, idx) => {
          const p = Math.floor(clientSim.step / (18 + idx * 3)) % 2;
          const y = (clientSim.step % (18 + idx * 3)) > (18 + idx * 3 - 3);
          tl_phases[jid] = { phase_idx: p, is_yellow: y };
          agents[jid] = {
            current_phase: p === 0 ? 'EW' : 'NS',
            is_yellow: y,
            steps_on_phase: clientSim.step % 18,
            allocated_green: 30,
            local_obs: {
              EW: { density: 0.42, queue_length: 3, average_speed: 8.8, status: 'MEDIUM' },
              NS: { density: 0.32, queue_length: 2, average_speed: 9.4, status: 'LOW' }
            }
          };
        });

        simState = {
          step: clientSim.step,
          running: clientSim.running,
          total_vehicles: clientSim.vehicles.length,
          total_waiting: 4,
          avg_speed: +(8.6).toFixed(1),
          avg_travel_time: +(15.0).toFixed(1),
          ambulance: clientSim.ambulance,
          active_incidents: clientSim.active_incidents,
          tl_phases,
          agents,
          vehicles: clientSim.vehicles
        };
      }

      if (!simState) return;

      // Top HUD updates
      document.getElementById('metric-step').textContent = simState.step;
      document.getElementById('metric-veh').textContent = simState.total_vehicles;
      document.getElementById('metric-waiting').textContent = simState.total_waiting;
      document.getElementById('metric-speed').textContent = `${simState.avg_speed} km/h`;
      document.getElementById('metric-travel').textContent = `${simState.avg_travel_time}s`;

      // Sync control button active state (don't overwrite recently clicked user action within 1.5s)
      if (typeof simState.running === 'boolean' && (Date.now() - lastUserActionTime > 1500)) {
        updatePlayPauseUI(simState.running);
      }

      // Ambulance banner
      const isAmb = simState.ambulance && simState.ambulance.active;
      document.getElementById('corridor-banner').classList.toggle('active', isAmb);

      // Accident button state
      const hasInc = simState.active_incidents && simState.active_incidents.length > 0;
      isIncidentActive = hasInc;
      const incBtn = document.getElementById('btn-incident-toggle');
      if (hasInc) {
        if (incBtn.textContent !== '🚨 Clear Accident (J3)') {
          incBtn.textContent = '🚨 Clear Accident (J3)';
          incBtn.className = 'btn btn-active-incident';
        }
      } else {
        if (incBtn.textContent !== '⚠️ Inject Accident (J3)') {
          incBtn.textContent = '⚠️ Inject Accident (J3)';
          incBtn.className = 'btn btn-amber';
        }
      }

      // Sync node drawer values without recreating innerHTML
      updateNodeDrawerValues();

      // Sync dashboard grid values without recreating innerHTML
      updateDashboardGridValues();
    }

    function updateNodeDrawerValues() {
      if (!selectedJunction || !simState?.agents?.[selectedJunction]) return;

      const ag = simState.agents[selectedJunction];
      document.getElementById('drw-junc-name').textContent = `Junction ${selectedJunction} (Agent)`;
      document.getElementById('drw-phase-name').textContent = `${ag.current_phase} GREEN`;
      document.getElementById('drw-phase-time').textContent = `Hold: ${ag.steps_on_phase}s / Dynamic Max: ${ag.allocated_green}s`;

      const ind = document.getElementById('drw-sig-indicator');
      ind.className = 'signal-indicator ' + (ag.is_yellow ? 'sig-yellow' : 'sig-green');

      const obs = ag.local_obs || {};
      ['EW', 'NS'].forEach(dir => {
        const d = obs[dir] || { density: 0, queue_length: 0, average_speed: 0, congestion_score: 0, waiting_time: 0, status: 'LOW' };
        const statusCol = d.status === 'HIGH' ? '#ef4444' : d.status === 'MEDIUM' ? '#eab308' : '#22c55e';

        const stEl = document.getElementById(`dir-${dir}-status`);
        if (stEl) {
          stEl.textContent = `${d.status} (${Math.round(d.density * 100)}%)`;
          stEl.style.color = statusCol;
        }

        const barEl = document.getElementById(`dir-${dir}-bar`);
        if (barEl) {
          barEl.style.width = `${d.density * 100}%`;
          barEl.style.background = statusCol;
        }

        const qEl = document.getElementById(`dir-${dir}-queue`);
        if (qEl) qEl.textContent = d.queue_length;

        const spEl = document.getElementById(`dir-${dir}-speed`);
        if (spEl) spEl.textContent = d.average_speed;

        const scEl = document.getElementById(`dir-${dir}-score`);
        if (scEl) scEl.textContent = d.congestion_score;

        const wEl = document.getElementById(`dir-${dir}-wait`);
        if (wEl) wEl.textContent = `${d.waiting_time}s`;
      });

      document.getElementById('drw-ai-reasoning').textContent = ag.decision_reason || 'Observing traffic flow...';
    }

    let cityGridInitialized = false;

    function updateCityDashboardGrid() {
      if (!citySimInstance) return;
      const grid = document.getElementById('modal-agent-grid');
      const agents = citySimInstance.agents;

      // Build all 33 junction cards when entering city mode
      if (!cityGridInitialized) {
        let html = '';
        BBSR_INTERSECTIONS.forEach(j => {
          const zCol = {
            heritage: '#fbbf24', commercial: '#38bdf8', govt: '#86efac',
            medical: '#f472b6', it: '#4ade80', residential: '#94a3b8',
            transport: '#fb923c', edu: '#c084fc'
          }[j.zone] || '#94a3b8';

          html += `
            <div class="agent-summary-card" id="city-card-${j.id}" onclick="selectCityJunctionAndFly('${j.id}')" style="cursor:pointer;">
              <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                <div>
                  <span style="font-weight:700; font-size:13px; color:#fff;">${j.id}</span>
                  <span style="font-size:9px; background:${zCol}22; color:${zCol}; padding:2px 6px; border-radius:4px; margin-left:4px; border:1px solid ${zCol}44; text-transform:uppercase;">${j.zone}</span>
                </div>
                <span id="city-ag-phase-${j.id}" style="font-size:10px; font-weight:700; color:#22c55e; background:rgba(34,197,94,0.12); padding:2px 6px; border-radius:4px; border:1px solid rgba(34,197,94,0.3);">EW</span>
              </div>
              <div style="font-size:11px; color:#cbd5e1; font-weight:500; margin-bottom:6px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
                ${j.name}
              </div>
              <div style="font-size:11px; color:var(--text-muted); display:flex; flex-direction:column; gap:3px;">
                <div style="display:flex; justify-content:space-between;"><span>Density:</span> <b id="city-ag-dens-${j.id}" style="color:#fff;">0%</b></div>
                <div style="display:flex; justify-content:space-between;"><span>Queued:</span> <b id="city-ag-queue-${j.id}" style="color:#fff;">0 cars</b></div>
                <div style="display:flex; justify-content:space-between;"><span>CCTV AI Status:</span> <b id="city-ag-cctv-${j.id}" style="color:#22c55e;">CLEAR</b></div>
              </div>
            </div>
          `;
        });
        grid.innerHTML = html;
        cityGridInitialized = true;
      }

      // Update values for all 33 cards in real time
      BBSR_INTERSECTIONS.forEach(j => {
        const ag = agents[j.id];
        if (!ag) return;

        const phEl = document.getElementById(`city-ag-phase-${j.id}`);
        if (phEl) {
          const isYellow = ag.isYellow;
          phEl.textContent = isYellow ? 'YELLOW' : `${ag.phaseName} GREEN`;
          phEl.style.color = isYellow ? '#eab308' : '#22c55e';
          phEl.style.borderColor = isYellow ? 'rgba(234,179,8,0.4)' : 'rgba(34,197,94,0.3)';
        }

        const avgDens = Math.round(((ag.obs.EW.density + ag.obs.NS.density) / 2) * 100);
        const densEl = document.getElementById(`city-ag-dens-${j.id}`);
        if (densEl) densEl.textContent = `${avgDens}%`;

        const totalQ = ag.obs.EW.queue + ag.obs.NS.queue;
        const qEl = document.getElementById(`city-ag-queue-${j.id}`);
        if (qEl) qEl.textContent = `${totalQ} cars`;

        const cctvEl = document.getElementById(`city-ag-cctv-${j.id}`);
        if (cctvEl) {
          if (citySimInstance.ambulanceActive && citySimInstance.activePreemptJuncs?.has(j.id)) {
            cctvEl.innerHTML = '<span style="color:#10b981; font-weight:700;">🚨 AMBULANCE IN CCTV RANGE</span>';
          } else {
            cctvEl.innerHTML = '<span style="color:#94a3b8;">NORMAL ADAPTIVE</span>';
          }
        }
      });

      // Update live message stream from multi-agent network
      const msgBox = document.getElementById('modal-msg-stream');
      const msgs = citySimInstance.agentMessages || [];
      if (msgs.length) {
        msgBox.innerHTML = msgs.slice(-12).map(m => `
          <div class="msg-line">
            <span class="sender" style="color:#38bdf8;">[${m.sender}]</span>
            <span style="color:#64748b;">(Step ${m.timestamp}):</span>
            <span class="reason" style="color:#e2e8f0;">${m.text}</span>
          </div>
        `).join('');
      }
    }

    function selectCityJunctionAndFly(jId) {
      document.getElementById('dash-modal').classList.remove('active');
      const j = BBSR_INTERSECTIONS.find(x => x.id === jId);
      if (j && bbsrLeafletMap) {
        bbsrLeafletMap.flyTo([j.lat, j.lon], 15, { animate: true, duration: 0.8 });
      }
      document.getElementById('city-junction-drawer').classList.add('active');
      updateCityDrawer(jId);
    }

    function updateDashboardGridValues() {
      if (isCityMode) {
        updateCityDashboardGrid();
        return;
      }

      const modal = document.getElementById('dash-modal');
      if (!modal || !modal.classList.contains('active')) return;

      if (!simState?.agents) return;

      for (const [jid, ag] of Object.entries(simState.agents)) {
        const phEl = document.getElementById(`ag-phase-${jid}`);
        if (phEl) {
          phEl.textContent = ag.current_phase;
          phEl.style.color = ag.current_phase === 'EW' ? '#22c55e' : '#38bdf8';
        }

        const densEl = document.getElementById(`ag-dens-${jid}`);
        if (densEl) densEl.textContent = `${Math.round(ag.overall_density * 100)}%`;

        const qEl = document.getElementById(`ag-queue-${jid}`);
        if (qEl) qEl.textContent = `${ag.total_queue} cars`;

        const capEl = document.getElementById(`ag-cap-${jid}`);
        if (capEl) capEl.textContent = `${Math.round(ag.available_capacity * 100)}%`;
      }

      // Update message feed
      const msgBox = document.getElementById('modal-msg-stream');
      const msgs = simState.agent_messages || [];
      msgBox.innerHTML = msgs.slice(-8).map(m => `
        <div class="msg-line">
          <span class="sender">[${m.sender}]</span>
          <span>(Step ${m.timestamp}):</span>
          <span class="reason">${m.decision_reason}</span>
        </div>
      `).join('');
    }

    function selectAndClose(jid) {
      selectedJunction = jid;
      document.getElementById('node-drawer').classList.add('active');
      document.getElementById('dash-modal').classList.remove('active');
      updateNodeDrawerValues();
    }

    // ── Mouse & Pan/Zoom Handlers ──
    const container = document.getElementById('canvas-container');

    container.addEventListener('mousedown', e => {
      view.isDragging = true;
      view.startX = e.clientX - view.x;
      view.startY = e.clientY - view.y;
    });

    window.addEventListener('mousemove', e => {
      if (view.isDragging) {
        view.x = e.clientX - view.startX;
        view.y = e.clientY - view.startY;
      }
    });

    window.addEventListener('mouseup', () => { view.isDragging = false; });

    container.addEventListener('wheel', e => {
      e.preventDefault();
      const zoomFactor = e.deltaY < 0 ? 1.15 : 0.85;
      const mouseWorld = screenToWorld(e.clientX, e.clientY);

      view.scale = Math.min(Math.max(view.scale * zoomFactor, 0.4), 4.0);
      view.x = e.clientX - mouseWorld.x * view.scale;
      view.y = e.clientY - (600 - mouseWorld.y) * view.scale;
    });

    container.addEventListener('click', e => {
      const clickWorld = screenToWorld(e.clientX, e.clientY);
      for (const [jid, j] of Object.entries(intersections)) {
        if (j.virtual) continue;
        const dx = clickWorld.x - j.pos.x;
        const dy = clickWorld.y - j.pos.y;
        if (Math.sqrt(dx*dx + dy*dy) < 30) {
          selectedJunction = jid;
          document.getElementById('node-drawer').classList.add('active');
          updateNodeDrawerValues();
          return;
        }
      }
    });

    // ── Instant UI Actions & API Calls ──
    async function apiCall(endpoint, payload) {
      try {
        const res = await fetch(endpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        if (!res.ok) throw new Error();
        const data = await res.json();
        if (data && data.state) {
          simState = data.state;
          document.getElementById('metric-step').textContent = simState.step;
          document.getElementById('metric-veh').textContent = simState.total_vehicles;
          document.getElementById('metric-waiting').textContent = simState.total_waiting;
          document.getElementById('metric-speed').textContent = `${simState.avg_speed} km/h`;
          document.getElementById('metric-travel').textContent = `${simState.avg_travel_time}s`;
        }
      } catch (err) {
        if (payload?.cmd === 'start') clientSim.running = true;
        if (payload?.cmd === 'pause') clientSim.running = false;
        if (payload?.cmd === 'reset') { clientSim.step = 0; clientSim.running = true; }
        if (payload?.cmd === 'step') { stepClientSim(); }
        if (endpoint.includes('incident')) {
          if (payload.active) clientSim.active_incidents = [payload];
          else clientSim.active_incidents = [];
        }
        if (endpoint.includes('ambulance')) {
          clientSim.ambulance.active = !clientSim.ambulance.active;
          clientSim.ambulance.progress_m = 0;
          clientSim.ambulance.current_road = "road_VW1_J1";
        }
      }
    }

    document.getElementById('btn-start').onclick = () => {
      lastUserActionTime = Date.now();
      if (isCityMode && citySimInstance) {
        citySimInstance.paused = false;
        updatePlayPauseUI(true);
      } else {
        clientSim.running = true;
        if (simState) simState.running = true;
        updatePlayPauseUI(true);
        apiCall('/api/control', { cmd: 'start' });
      }
    };

    document.getElementById('btn-pause').onclick = () => {
      lastUserActionTime = Date.now();
      if (isCityMode && citySimInstance) {
        citySimInstance.paused = true;
        updatePlayPauseUI(false);
      } else {
        clientSim.running = false;
        if (simState) simState.running = false;
        updatePlayPauseUI(false);
        apiCall('/api/control', { cmd: 'pause' });
      }
    };

    document.getElementById('btn-step').onclick = () => {
      lastUserActionTime = Date.now();
      const btnStep = document.getElementById('btn-step');
      btnStep.classList.add('btn-step-active');
      setTimeout(() => btnStep.classList.remove('btn-step-active'), 150);

      if (isCityMode && citySimInstance) {
        citySimInstance.paused = true;
        citySimInstance.tick(0.08 * citySimSpeedMultiplier);
        citySimInstance.render();
        updateCityHUD();
        updatePlayPauseUI(false);
      } else {
        if (simState) {
          simState.running = false;
          simState.step = (simState.step || 0) + 1;
        }
        clientSim.running = false;
        stepClientSim();
        updatePlayPauseUI(false);
        apiCall('/api/control', { cmd: 'step' });
      }
    };

    document.getElementById('btn-reset').onclick = () => {
      lastUserActionTime = Date.now();
      const btnReset = document.getElementById('btn-reset');
      btnReset.style.transform = 'rotate(180deg)';
      setTimeout(() => { btnReset.style.transform = ''; }, 250);

      if (isCityMode && citySimInstance) {
        citySimInstance.step = 0;
        citySimInstance.vehicles = [];
        citySimInstance.activePreemptJuncs = new Set();
        citySimInstance.cctvDetectedJunc = null;
        citySimInstance.ambulanceActive = false;
        citySimInstance.ambulanceVehicle = null;
        citySimInstance.ambulanceCorridorRoads = null;
        const banner = document.getElementById('corridor-banner');
        if (banner) banner.classList.remove('active');
        citySimInstance._spawnBatch(220);
        citySimInstance.render();
        updateCityHUD();
      } else {
        smoothVehicles.clear();
        if (simState) {
          simState.step = 0;
          simState.running = true;
        }
        clientSim.step = 0;
        clientSim.running = true;
        updatePlayPauseUI(true);
        apiCall('/api/control', { cmd: 'reset' });
      }
    };

    document.getElementById('slider-speed').oninput = function() {
      const v = parseInt(this.value);
      // Continuous smooth speed multiplier from 0.2x to 3.5x
      let mult = 1.0;
      if (v <= 50) {
        mult = 0.2 + (v / 50) * 0.8;
      } else {
        mult = 1.0 + ((v - 50) / 50) * 2.5;
      }
      citySimSpeedMultiplier = mult;
      document.getElementById('lbl-speed').textContent = mult.toFixed(1) + '×';

      // Dynamically adjust CityFlow backend step delay
      const delay = Math.max(0.015, 0.10 / mult);
      apiCall('/api/control', { cmd: 'speed', value: delay });
    };

    // Responsive Accident Toggle (Dual Mode)
    document.getElementById('btn-incident-toggle').onclick = function() {
      if (isCityMode && citySimInstance) {
        citySimInstance.injectIncident(citySimInstance.selectedJunction || 'MAST');
        if (citySimInstance.incidentActive) {
          this.textContent = '🚨 Clear Accident';
          this.className = 'btn btn-active-incident';
        } else {
          this.textContent = '⚠️ Inject Accident (MAST)';
          this.className = 'btn btn-amber';
        }
      } else {
        isIncidentActive = !isIncidentActive;
        this.textContent = isIncidentActive ? '🚨 Clear Accident (J3)' : '⚠️ Inject Accident (J3)';
        this.className = isIncidentActive ? 'btn btn-active-incident' : 'btn btn-amber';
        const incPayload = isIncidentActive ? [{ junction: 'J3', road: 'road_J3_J2', type: 'ACCIDENT', active: true }] : [];
        if (simState) simState.active_incidents = incPayload;
        clientSim.active_incidents = incPayload;
        apiCall('/api/incident', { junction: 'J3', road: 'road_J3_J2', type: 'ACCIDENT', active: isIncidentActive });
      }
    };

    document.getElementById('btn-ambulance-dispatch').onclick = function() {
      if (isCityMode && citySimInstance) {
        citySimInstance.dispatchAmbulance();
        document.getElementById('corridor-banner').classList.toggle('active', citySimInstance.ambulanceActive);
      } else {
        const nextActive = !(simState?.ambulance?.active || clientSim.ambulance.active);
        if (simState) {
          if (!simState.ambulance) simState.ambulance = {};
          simState.ambulance.active = nextActive;
          simState.ambulance.current_road = 'road_VW1_J1';
          simState.ambulance.progress_m = 0;
          simState.ambulance.road_dist = 0;
        }
        clientSim.ambulance.active = nextActive;
        clientSim.ambulance.progress_m = 0;
        clientSim.ambulance.road_dist = 0;
        clientSim.ambulance.current_road = 'road_VW1_J1';
        smoothAmbDist = 0;
        document.getElementById('corridor-banner').classList.toggle('active', nextActive);
        apiCall('/api/ambulance', {});
      }
    };

    document.getElementById('btn-override-ew').onclick = () => {
      apiCall('/api/override', { junction: selectedJunction, phase: 0 });
    };
    document.getElementById('btn-override-ns').onclick = () => {
      apiCall('/api/override', { junction: selectedJunction, phase: 1 });
    };

    document.getElementById('btn-zoom-in').onclick = () => {
      if (isCityMode && bbsrLeafletMap) {
        bbsrLeafletMap.zoomIn();
      } else {
        view.scale *= 1.2;
      }
    };
    document.getElementById('btn-zoom-out').onclick = () => {
      if (isCityMode && bbsrLeafletMap) {
        bbsrLeafletMap.zoomOut();
      } else {
        view.scale *= 0.8;
      }
    };
    document.getElementById('btn-recenter').onclick = () => {
      if (isCityMode && bbsrLeafletMap) {
        bbsrLeafletMap.setView([20.2961, 85.8245], 13);
      } else {
        centerView();
      }
    };

    document.getElementById('drw-close').onclick = () => {
      document.getElementById('node-drawer').classList.remove('active');
    };

    // Dashboard Modal
    document.getElementById('btn-open-dash').onclick = () => {
      document.getElementById('dash-modal').classList.add('active');
      updateDashboardGridValues();
    };
    document.getElementById('modal-close').onclick = () => {
      document.getElementById('dash-modal').classList.remove('active');
    };

    window.addEventListener('keydown', e => {
      if (e.code === 'Space') {
        e.preventDefault();
        if (isCityMode && citySimInstance) {
          citySimInstance.paused = !citySimInstance.paused;
          updatePlayPauseUI(!citySimInstance.paused);
        } else {
          const isRunning = simState?.running;
          apiCall('/api/control', { cmd: isRunning ? 'pause' : 'start' });
        }
      } else if (e.code === 'KeyR') {
        if (isCityMode && citySimInstance) {
          citySimInstance.step = 0;
          citySimInstance.vehicles = [];
          citySimInstance._spawnBatch(900);
        } else {
          apiCall('/api/control', { cmd: 'reset' });
        }
      } else if (e.code === 'KeyC') {
        if (isCityMode && bbsrLeafletMap) {
          bbsrLeafletMap.setView([20.2961, 85.8245], 13);
        } else {
          centerView();
        }
      }
    });

    // ── Animation Loop (60 FPS) & Telemetry Poller (200ms) ──
    let isCityMode = false;
    let citySimSpeedMultiplier = 1.0;
    let citySimInstance = null;
    let citySimRafId = null;
    let citySimTickInterval = null;
    let citySimTelemetryInterval = null;
    let bbsrLeafletMap = null;
    let bbsrCanvas = null;
    let bbsrCtx = null;

    // ── Mini Mode Render Loop ──
    function loop() {
      if (!isCityMode) {
        render();
        requestAnimationFrame(loop);
      }
    }

    // ── Full City Mode Activation (Bhubaneswar Real City Network) ──
    function enterCityMode() {
      isCityMode = true;
      cityGridInitialized = false;
      gridInitialized = false;
      if (citySimInstance) citySimInstance.paused = false;
      updatePlayPauseUI(true);
      document.getElementById('modal-agent-grid').innerHTML = '';

      // Switch containers: hide mini canvas, show real Bhubaneswar Leaflet container
      document.getElementById('canvas-container').style.display = 'none';
      document.getElementById('bbsr-map-container').style.display = 'block';

      // Update HUD labels
      document.getElementById('brand-title-text').textContent = 'CityFlow — Bhubaneswar Real City Network';
      document.getElementById('mini-agents-badge').style.display = 'none';
      const cityBadge = document.getElementById('city-agents-badge');
      cityBadge.textContent = `${(typeof BBSR_INTERSECTIONS !== 'undefined' ? BBSR_INTERSECTIONS.length : 46)} AGENTS ACTIVE`;
      cityBadge.classList.add('visible');

      // Update button text to allow quick swapping back
      const btn = document.getElementById('btn-fullcity-toggle');
      btn.textContent = '◀ Back to Mini Sim';
      btn.classList.remove('btn-fullcity');
      btn.classList.add('btn-minisim');

      // Initialize Leaflet map and city simulation ONCE on first switch
      if (!bbsrLeafletMap) {
        bbsrLeafletMap = L.map('bbsr-leaflet-map', {
          center: [20.2961, 85.8245],
          zoom: 13,
          minZoom: 11,
          maxZoom: 18,
          zoomControl: false
        });

        // 100% Free Esri Dark Gray Canvas — NO API KEY, NO WATERMARKS
        // maxNativeZoom:16 = Esri tiles only go to zoom 16, but Leaflet will
        // upscale them cleanly for zoom 17-18 instead of showing "Map data not yet available"
        L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}', {
          maxNativeZoom: 16,
          maxZoom: 18,
          attribution: '&copy; Esri, HERE, Garmin &mdash; CityFlow Multi-Agent Traffic'
        }).addTo(bbsrLeafletMap);

        bbsrCanvas = document.getElementById('bbsr-canvas');
        bbsrCtx = bbsrCanvas.getContext('2d');

        function resizeBbsrCanvas() {
          const w = window.innerWidth;
          const h = window.innerHeight;
          bbsrCanvas.width = w * window.devicePixelRatio;
          bbsrCanvas.height = h * window.devicePixelRatio;
          bbsrCtx.setTransform(1, 0, 0, 1, 0, 0);
          bbsrCtx.scale(window.devicePixelRatio, window.devicePixelRatio);
        }
        window.addEventListener('resize', resizeBbsrCanvas);
        resizeBbsrCanvas();

        citySimInstance = new BhubaneswarSim(bbsrCanvas, bbsrCtx, bbsrLeafletMap);

        bbsrLeafletMap.on('move', () => {
          if (isCityMode && citySimInstance) citySimInstance.render();
        });
        bbsrLeafletMap.on('zoom', () => {
          if (isCityMode && citySimInstance) citySimInstance.render();
        });

        // Reliable geographical click detection on Leaflet map
        bbsrLeafletMap.on('click', (e) => {
          if (!isCityMode || !citySimInstance) return;
          const jId = citySimInstance.handleMapClick(e);
          if (jId) {
            document.getElementById('city-junction-drawer').classList.add('active');
            updateCityDrawer(jId);
          } else {
            document.getElementById('city-junction-drawer').classList.remove('active');
          }
        });
      } else {
        setTimeout(() => {
          bbsrLeafletMap.invalidateSize();
          if (citySimInstance) citySimInstance.render();
        }, 100);
      }

      // City simulation tick at ~20 fps (dt ≈ 0.05s)
      citySimTickInterval = setInterval(() => {
        if (isCityMode && citySimInstance) citySimInstance.tick(0.05 * citySimSpeedMultiplier);
      }, 50);

      // City HUD telemetry update at 250ms
      citySimTelemetryInterval = setInterval(() => {
        if (isCityMode && citySimInstance) updateCityHUD();
      }, 250);

      // City render RAF loop
      function cityLoop() {
        if (!isCityMode) return;
        citySimInstance.render();
        citySimRafId = requestAnimationFrame(cityLoop);
      }
      citySimRafId = requestAnimationFrame(cityLoop);
    }

    // ── Full City Mode Exit ──
    function exitCityMode() {
      isCityMode = false;
      cityGridInitialized = false;
      gridInitialized = false;
      document.getElementById('modal-agent-grid').innerHTML = '';

      // Stop city loops
      clearInterval(citySimTickInterval);
      clearInterval(citySimTelemetryInterval);
      if (citySimRafId) cancelAnimationFrame(citySimRafId);

      // Restore view containers: hide real Bhubaneswar map, show mini canvas
      document.getElementById('bbsr-map-container').style.display = 'none';
      document.getElementById('canvas-container').style.display = 'block';

      // Restore HUD
      document.getElementById('brand-title-text').textContent = 'CityFlow Multi-Agent SIH';
      document.getElementById('mini-agents-badge').style.display = '';
      document.getElementById('city-agents-badge').classList.remove('visible');

      // Restore button
      const btn = document.getElementById('btn-fullcity-toggle');
      btn.textContent = '🏙️ Full City — Bhubaneswar';
      btn.classList.remove('btn-minisim');
      btn.classList.add('btn-fullcity');

      // Restore mini controls
      const incBtn = document.getElementById('btn-incident-toggle');
      incBtn.textContent = isIncidentActive ? '🚨 Clear Accident (J3)' : '⚠️ Inject Accident (J3)';
      incBtn.className = isIncidentActive ? 'btn btn-active-incident' : 'btn btn-amber';

      document.getElementById('corridor-banner').classList.remove('active');

      // Close city drawer
      document.getElementById('city-junction-drawer').classList.remove('active');

      // Re-initialize mini grid when opening dashboard in mini mode
      initDashboardGridOnce();

      // Restart mini render loop
      updatePlayPauseUI(simState?.running || false);
      requestAnimationFrame(loop);
    }

    // ── City HUD Telemetry ──
    function updateCityHUD() {
      if (!citySimInstance) return;
      const s = citySimInstance.stats;
      document.getElementById('metric-step').textContent = s.stepCount;
      document.getElementById('metric-veh').textContent = s.totalVehicles;
      document.getElementById('metric-waiting').textContent = s.queueTotal;
      document.getElementById('metric-speed').textContent = `${s.avgSpeed} km/h`;
      const travelEst = (26.0 + (s.queueTotal / Math.max(1, s.totalVehicles)) * 16.0).toFixed(1);
      document.getElementById('metric-travel').textContent = `~${travelEst}s`;
    }

    // ── City Junction Drawer Updates ──
    function updateCityDrawer(jId) {
      if (!citySimInstance) return;
      const ag = citySimInstance.agents[jId];
      const j  = BBSR_INTERSECTIONS.find(x => x.id === jId);
      if (!ag || !j) return;

      document.getElementById('city-drw-name').textContent = `${j.id} — ${j.name}`;
      document.getElementById('city-drw-phase').textContent = ag.isYellow ? 'YELLOW CLEARANCE' : `${ag.phaseName} GREEN`;
      document.getElementById('city-drw-hold').textContent = `Hold: ${Math.round(ag.stepsOnPhase)}s / Max: ${ag.allocatedGreen}s`;

      const ind = document.getElementById('city-drw-sig');
      ind.className = 'signal-indicator ' + (ag.isYellow ? 'sig-yellow' : 'sig-green');

      const ew = ag.obs.EW, ns = ag.obs.NS;
      document.getElementById('city-drw-ew-dens').textContent = `${Math.round(ew.density * 100)}%`;
      document.getElementById('city-drw-ew-q').textContent = ew.queue;
      document.getElementById('city-drw-ew-sc').textContent = (ew.score || 0).toFixed(2);
      document.getElementById('city-drw-ns-dens').textContent = `${Math.round(ns.density * 100)}%`;
      document.getElementById('city-drw-ns-q').textContent = ns.queue;
      document.getElementById('city-drw-ns-sc').textContent = (ns.score || 0).toFixed(2);
      document.getElementById('city-drw-reason').textContent = ag.decisionReason;

      citySimInstance.selectedJunction = jId;
    }

    // ── City Mode Event Handlers ──
    document.getElementById('btn-fullcity-toggle').onclick = () => {
      if (isCityMode) exitCityMode(); else enterCityMode();
    };

    document.getElementById('city-drw-close').onclick = () => {
      document.getElementById('city-junction-drawer').classList.remove('active');
    };

    // City mode manual signal overrides
    document.getElementById('city-btn-override-ew').onclick = () => {
      if (!citySimInstance || !citySimInstance.selectedJunction) return;
      const ag = citySimInstance.agents[citySimInstance.selectedJunction];
      if (ag) {
        ag.emergencyOverride = 'EW';
        ag.currentPhase = 0;
        ag.isYellow = false;
        ag.stepsOnPhase = 0;
        ag.decisionReason = '👤 Manual Force EW Green Override';
        updateCityDrawer(citySimInstance.selectedJunction);
      }
    };
    document.getElementById('city-btn-override-ns').onclick = () => {
      if (!citySimInstance || !citySimInstance.selectedJunction) return;
      const ag = citySimInstance.agents[citySimInstance.selectedJunction];
      if (ag) {
        ag.emergencyOverride = 'NS';
        ag.currentPhase = 1;
        ag.isYellow = false;
        ag.stepsOnPhase = 0;
        ag.decisionReason = '👤 Manual Force NS Green Override';
        updateCityDrawer(citySimInstance.selectedJunction);
      }
    };

    // Keep city drawer live while open
    setInterval(() => {
      if (!isCityMode || !citySimInstance || !citySimInstance.selectedJunction) return;
      if (document.getElementById('city-junction-drawer').classList.contains('active')) {
        updateCityDrawer(citySimInstance.selectedJunction);
      }
    }, 300);

    (async () => {
      await loadRoadnet();
      await updateTelemetry();
      setInterval(updateTelemetry, 200);
      requestAnimationFrame(loop);
    })();