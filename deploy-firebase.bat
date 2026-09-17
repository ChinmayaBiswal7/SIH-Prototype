@echo off
title ClearWays - Firebase Hosting Deployer
color 0a
echo ================================================================
echo            CLEARWAYS - DEPLOY TO FIREBASE HOSTING
echo ================================================================
echo.

if exist "%~dp0ClearWays-main\clearways-react\package.json" (
    cd /d "%~dp0ClearWays-main\clearways-react"
) else (
    cd /d "%~dp0"
)

echo [1/3] Building latest production code...
call npm run build

echo.
echo [2/3] Connecting to Firebase account...
echo A browser window will open. Click "Allow" with your Google account
echo (the one you have open in Chrome with "Clear Ways").
echo.
call firebase login --reauth

echo.
echo [3/3] Deploying files to https://clear-ways.web.app ...
call firebase deploy --only hosting

echo.
echo ================================================================
echo   DEPLOYMENT FINISHED!
echo   Open: https://clear-ways.web.app
echo ================================================================
echo.
pause
