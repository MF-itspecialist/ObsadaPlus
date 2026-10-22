# Obsada+ z trasami z własnego serwera OSRM (bez Google Maps).
# Uruchom z katalogu projektu:  powershell -ExecutionPolicy Bypass -File scripts\start-osrm.ps1
Set-Location (Join-Path $PSScriptRoot "..")
$env:GOOGLE_MAPS_API_KEY = ""
$env:ROUTING_PROVIDER = "osrm"
docker compose --profile osrm up --build
