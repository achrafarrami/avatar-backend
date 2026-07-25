#requires -Version 5
<#
  Backend launcher for the AI-Avatar-Engine "brain".
  Starts the AI photo analyzer + shared-data/asset API in this window;
  Ctrl+C stops it.

    AI analyzer + data/asset API  ->  http://127.0.0.1:8100

  This repo is BACKEND-ONLY. The web client (Avatar Sandbox) lives in its own
  repo (../avatar-frontend) and is started separately with `npm run dev`; it
  reads everything from this API via VITE_API_BASE. The future mobile app is a
  second client hitting the same endpoints.

  Usage (from anywhere -- paths resolve relative to this file):
    powershell -ExecutionPolicy Bypass -File AI-Avatar-Engine\run.ps1
  or just double-click AI-Avatar-Engine\run.cmd
#>
$ErrorActionPreference = 'Stop'
$here   = $PSScriptRoot
$py     = Join-Path $here 'ai\.venv\Scripts\python.exe'
$server = Join-Path $here 'ai\photo_analyzer\server.py'

if (-not (Test-Path $py)) {
    throw "Python venv not found at $py -- see ai/photo_analyzer/README.md for setup."
}

Write-Host 'AI analyzer + data/asset API -> http://127.0.0.1:8100   (Ctrl+C stops it)' -ForegroundColor Cyan
Write-Host 'Web client lives in ../avatar-frontend -- run `npm run dev` there.' -ForegroundColor DarkGray
& $py $server
