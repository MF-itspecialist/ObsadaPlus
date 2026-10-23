#!/bin/sh
# Przygotowanie mapy dla OSRM (uruchamiane przez usługę osrm-prepare w docker-compose).
# Pomija pracę, gdy mapa jest już gotowa. Inny region: zmienna OSRM_PBF_URL (plik .osm.pbf z Geofabrik).
set -e
cd /data
if [ -f region.osrm.mldgr ] && [ "$(cat region.source 2>/dev/null)" = "$OSRM_PBF_URL" ]; then
  echo "Mapa OSRM gotowa ($OSRM_PBF_URL)."
  exit 0
fi
echo "Pobieram mapę: $OSRM_PBF_URL"
if command -v curl >/dev/null 2>&1; then
  curl -fL --retry 3 -o region.osm.pbf "$OSRM_PBF_URL"
elif command -v wget >/dev/null 2>&1; then
  wget -O region.osm.pbf "$OSRM_PBF_URL"
else
  apt-get update -qq && apt-get install -y -qq curl ca-certificates >/dev/null
  curl -fL --retry 3 -o region.osm.pbf "$OSRM_PBF_URL"
fi
echo "Przygotowuję trasy (extract → partition → customize)…"
osrm-extract -p /opt/car.lua region.osm.pbf
osrm-partition region.osrm
osrm-customize region.osrm
rm -f region.osm.pbf
echo "$OSRM_PBF_URL" > region.source
echo "Mapa OSRM gotowa."
