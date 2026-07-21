@echo off
REM Double-click launcher: starts the AI analyzer + Avatar Sandbox together.
REM Closing this window (or Ctrl+C) stops both.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run.ps1"
