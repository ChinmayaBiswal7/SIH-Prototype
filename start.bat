@echo off
title VeloCiTI Full-Stack Launcher
color 0b
echo ================================================================
echo           VELOCITI - URBAN TRAFFIC MANAGEMENT SYSTEM
echo ================================================================
echo.
echo [1/2] Launching CityFlow Multi-Agent Python Server (Port 5000)...
start "CityFlow Backend Server" cmd /k "cd /d \"%~dp0city flow model\" && python server_standalone.py"

echo [2/2] Launching VeloCiTI React Dashboard (Port 5173)...
start "VeloCiTI React Vite" cmd /k "cd /d \"%~dp0ClearWays-main\clearways-react\" && npm run dev"

echo.
echo ================================================================
echo   Both services are now running:
echo   - React Web Dashboard:  http://localhost:5173/
echo   - CityFlow API Backend: http://localhost:5000/
echo ================================================================
echo You can leave this window open or close it.
timeout /t 5 >nul
