# VeloCiTI — Smart Urban Mobility & AI-Driven Green Corridor System

> **Smart India Hackathon (SIH) Prototype**  
> An enterprise-grade, multi-agent AI traffic management platform with real-time dynamic emergency green corridors, adaptive signal coordination, and live cloud telemetry.

---

## 🌟 Executive Summary

Urban traffic congestion impedes emergency vehicle response times and increases metropolitan transit delays. **VeloCiTI** provides an end-to-end intelligent transportation solution:
- **Multi-Agent Traffic Signal Control**: Distributed agents coordinating intersection phasing based on real-time vehicle density and queue metrics.
- **Dynamic Emergency Green Corridor**: Automated preemption along optimal Dijkstra transit paths, clearing intersections dynamically without halting surrounding traffic.
- **Autonomous In-Browser Simulation**: Dual-mode engine capable of running both local multi-agent Python backend workloads and high-performance in-browser client simulation ticks.
- **Live Cloud Telemetry**: Real-time bidirectional synchronization with Firebase Firestore for cross-platform situational awareness.

---

## 🏗️ Architecture & Technology Stack

```
                               ┌─────────────────────────────────────────┐
                               │       Client Browsers & Dashboards      │
                               └────────────────────┬────────────────────┘
                                                    │
                                     WebSocket / REST / Firestore
                                                    │
                               ┌────────────────────▼────────────────────┐
                               │      Production Container (Docker)      │
                               │                                         │
                               │  ┌───────────────────────────────────┐  │
                               │  │   React 19 + Vite Dashboard (SPA) │  │
                               │  │   - Leaflet Real GIS City Map     │  │
                               │  │   - 2D Canvas CityFlow Visualizer │  │
                               │  │   - Interactive Command Matrix    │  │
                               │  └─────────────────┬─────────────────┘  │
                               │                    │ /api/*             │
                               │  ┌─────────────────▼─────────────────┐  │
                               │  │   Python 3.11 Flask WSGI Server   │  │
                               │  │   - CityFlow Multi-Agent RL       │  │
                               │  │   - Traffic Signal Phasing Engine │  │
                               │  │   - Telemetry Streaming APIs      │  │
                               │  └───────────────────────────────────┘  │
                               └─────────────────────────────────────────┘
```

- **Frontend**: React 19, Vite, Leaflet GIS, GSAP, Chart.js, HTML5 Canvas 2D
- **Backend**: Python 3.11, Flask, Gunicorn WSGI, NumPy, CityFlow Simulation Engine
- **Cloud & DB**: Google Firebase Firestore, Render Cloud Containerization (Docker)

---

## 🚀 One-Click Cloud Deployment (Render.com)

This repository is pre-configured with a multi-stage production `Dockerfile` and `render.yaml` blueprint.

### Deploying on Render:
1. Go to **[Render.com](https://render.com)** and sign in with GitHub.
2. Click **"New +"** ➔ **"Web Service"**.
3. Connect your repository: **`ChinmayaBiswal7/SIH-Prototype`**.
4. In the settings:
   - **Name**: `sih-prototype`
   - **Runtime**: `Docker` (Auto-detected)
   - **Instance Type**: `Free`
5. Click **"Deploy Web Service"**.

Render will automatically build the React frontend, launch the Python multi-agent backend with Gunicorn, and provide an always-on **24/7 public HTTPS link**!

---

## 💻 Local Quickstart

### Option 1: One-Click Startup (Windows)
Double-click `start.bat` in the project root to automatically launch both the Python backend and React Vite frontend.

### Option 2: Manual Terminal Startup
```bash
# Terminal 1: Backend
cd "city flow model"
pip install -r requirements.txt
python server_standalone.py

# Terminal 2: Frontend
cd ClearWays-main/clearways-react
npm install
npm run dev
```

---

## 📊 Core Features

1. **46-Junction Real Bhubaneswar Road Network**:
   - Comprehensive arterial mapping of NH-16, Jayadev Vihar, Vani Vihar, Rasulgarh, Patia, and Master Canteen.
   - Dynamic lane occupancy and speed calculations.

2. **Emergency Vehicle Telemetry & Upright Navigation**:
   - Multi-unit emergency fleet tracking with continuous curve interpolation.
   - Dynamic direction flipping with horizontal scaling ensuring vehicles maintain upright orientation at all times.

3. **Accident Injection & Dynamic Rerouting**:
   - One-click incident triggers that automatically calculate diversion routes and notify adjacent junctions.

---

## 📄 License
Licensed under the MIT License. Developed for the Smart India Hackathon.
