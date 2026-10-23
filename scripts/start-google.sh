#!/bin/sh
# Obsada+ z trasami z Google Maps (Routes API). Klucz: GOOGLE_MAPS_API_KEY w .env lub w środowisku.
cd "$(dirname "$0")/.." || exit 1
if [ -z "$GOOGLE_MAPS_API_KEY" ] && [ -f .env ]; then
  GOOGLE_MAPS_API_KEY=$(sed -n 's/^[[:space:]]*GOOGLE_MAPS_API_KEY[[:space:]]*=[[:space:]]*//p' .env | head -n 1)
fi
if [ -z "$GOOGLE_MAPS_API_KEY" ]; then
  echo "Brak GOOGLE_MAPS_API_KEY w .env. Użyj scripts/start-osrm.sh albo dodaj klucz." >&2
  exit 1
fi
GOOGLE_MAPS_API_KEY=$GOOGLE_MAPS_API_KEY ROUTING_PROVIDER=google exec docker compose up --build
