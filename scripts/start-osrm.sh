#!/bin/sh
# Obsada+ z trasami z własnego serwera OSRM (bez Google Maps).
cd "$(dirname "$0")/.." || exit 1
GOOGLE_MAPS_API_KEY= ROUTING_PROVIDER=osrm exec docker compose --profile osrm up --build
