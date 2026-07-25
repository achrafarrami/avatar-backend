@echo off
REM Double-click launcher: starts the backend AI analyzer + data/asset API.
REM Closing this window (or Ctrl+C) stops it. The web client is a separate
REM repo (..\avatar-frontend) started with `npm run dev`.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run.ps1"
