# Obsada+ z trasami z Google Maps (Routes API). Klucz: GOOGLE_MAPS_API_KEY w pliku .env
# Uruchom z katalogu projektu:  powershell -ExecutionPolicy Bypass -File scripts\start-google.ps1
Set-Location (Join-Path $PSScriptRoot "..")
$key = $env:GOOGLE_MAPS_API_KEY
if (-not $key -and (Test-Path ".env")) {
  $line = Select-String -Path ".env" -Pattern '^\s*GOOGLE_MAPS_API_KEY\s*=\s*(\S+)' | Select-Object -First 1
  if ($line) { $key = $line.Matches[0].Groups[1].Value }
}
if (-not $key) {
  Write-Error "Brak GOOGLE_MAPS_API_KEY w .env. Uzyj scripts\start-osrm.ps1 albo dodaj klucz."
  exit 1
}
$env:GOOGLE_MAPS_API_KEY = $key
$env:ROUTING_PROVIDER = "google"
docker compose up --build
