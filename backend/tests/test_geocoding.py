"""Automatyczne uzupełnianie współrzędnych i dzielnicy z adresu (geokoder podmieniony, bez sieci)."""

import pytest

from app.main import app
from app.services.geocoding_service import GeocodeResult, Geocoder, GeocodingError, get_geocoder, normalize_street

KNOWN = {
    ("ul. Puławska 100", "Warszawa"): GeocodeResult(52.1962, 21.0238, "Warszawa", "Mokotów", "Puławska 100, Warszawa"),
    ("ul. Kościuszki 10", "Piaseczno"): GeocodeResult(52.0736, 21.0271, "Piaseczno", "", "Kościuszki 10, Piaseczno"),
    ("ul. Sosnkowskiego 3", "Warszawa"): GeocodeResult(52.1868, 20.8893, "Warszawa", "Ursus", "Sosnkowskiego 3, Warszawa"),
}


class FakeGeocoder(Geocoder):
    name = "fake"

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []
        self.down = False

    def geocode(self, address: str, city: str) -> GeocodeResult | None:
        self.calls.append((address, city))
        if self.down:
            raise GeocodingError("offline")
        return KNOWN.get((address, city))


@pytest.fixture()
def geocoder(client):
    fake = FakeGeocoder()
    app.dependency_overrides[get_geocoder] = lambda: fake
    return fake


def referee_body(**kw):
    return {"first_name": "Jan", "last_name": "Kowalski", "city": "Warszawa", "address": "ul. Puławska 100",
            "licenses": ["Sędzia IV liga", "Asystent okręgowy / pozostali"], **kw}


def test_create_referee_from_address_fills_coordinates_and_district(client, geocoder):
    r = client.post("/api/referees", json=referee_body())
    assert r.status_code == 201, r.text
    body = r.json()
    assert (body["latitude"], body["longitude"]) == (52.1962, 21.0238)
    assert body["district"] == "Mokotów"
    assert body["location_label"] == "Warszawa, Mokotów"
    assert body["licenses"] == ["Sędzia IV liga", "Asystent okręgowy / pozostali"]


def test_town_without_districts_shows_city_only(client, geocoder):
    r = client.post("/api/referees", json=referee_body(city="Piaseczno", address="ul. Kościuszki 10"))
    assert r.json()["location_label"] == "Piaseczno"


def test_update_regeocodes_only_when_address_changes(client, geocoder):
    ref = client.post("/api/referees", json=referee_body()).json()
    client.put(f"/api/referees/{ref['id']}", json=referee_body(first_name="Janusz"))
    assert len(geocoder.calls) == 1  # adres bez zmian — bez ponownego zapytania

    r = client.put(f"/api/referees/{ref['id']}", json=referee_body(city="Piaseczno", address="ul. Kościuszki 10"))
    assert r.json()["district"] == ""
    assert r.json()["latitude"] == 52.0736
    assert len(geocoder.calls) == 2


def test_unknown_address_is_rejected_with_readable_message(client, geocoder):
    r = client.post("/api/referees", json=referee_body(address="ul. Nieistniejąca 1"))
    assert r.status_code == 422
    assert "Nie znaleziono adresu" in r.json()["detail"]


def test_maps_service_down_returns_503(client, geocoder):
    geocoder.down = True
    assert client.post("/api/referees", json=referee_body()).status_code == 503


def test_explicit_coordinates_skip_geocoding(client, geocoder):
    r = client.post("/api/referees", json=referee_body(latitude=52.1, longitude=21.1, district="Wilanów"))
    assert r.status_code == 201
    assert r.json()["district"] == "Wilanów"
    assert geocoder.calls == []


def test_venue_from_address(client, geocoder):
    r = client.post("/api/venues", json={"name": "Stadion KS Ursus", "city": "Warszawa", "address": "ul. Sosnkowskiego 3"})
    assert r.status_code == 201, r.text
    assert (r.json()["latitude"], r.json()["longitude"]) == (52.1868, 20.8893)


def test_geocode_preview_endpoint(client, geocoder):
    r = client.get("/api/geocode", params={"address": "ul. Puławska 100", "city": "Warszawa"})
    assert r.json()["district"] == "Mokotów"
    assert client.get("/api/geocode", params={"address": "xyz", "city": "Warszawa"}).status_code == 404


def test_candidates_show_licenses_and_location_instead_of_score(seeded_client):
    match = seeded_client.get("/api/matches", params={"date_from": "2026-10-10", "date_to": "2026-10-10"}).json()[0]
    cands = seeded_client.get("/api/assignments/candidates", params={"match_id": match["id"]}).json()
    kowalski = next(c for c in cands if c["referee_name"] == "Jan Kowalski")
    assert kowalski["referee_licenses"][0] == "Sędzia III liga (TopAmator C)"
    assert kowalski["referee_location"] == "Warszawa, Ursynów"


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("ul. Puławska 100", "Puławska 100"),
        ("al. Jerozolimskie 1", "Aleja Jerozolimskie 1"),
        ("Plac Wojska Polskiego 28", "Plac Wojska Polskiego 28"),
        ("Marszałkowska 5", "Marszałkowska 5"),
    ],
)
def test_normalize_street(raw, expected):
    assert normalize_street(raw) == expected


def test_generated_preview_includes_license_and_location(seeded_client):
    preview = seeded_client.post(
        "/api/optimization/generate", json={"date_from": "2026-10-10", "date_to": "2026-10-11"}
    ).json()
    assert preview["assignments"]
    assert all(a["referee_licenses"] and a["referee_location"] for a in preview["assignments"])


def test_import_geocodes_new_venue_from_address(client, geocoder):
    records = [{"external_id": "X-1", "date": "2026-10-10", "start_time": "12:00", "home_team": "A", "away_team": "B",
                "venue_name": "Stadion KS Ursus", "venue_city": "Warszawa", "venue_address": "ul. Sosnkowskiego 3"}]
    r = client.post("/api/matches/import/json", json=records).json()
    assert r["created"] == 1 and r["errors"] == []
    venue = client.get("/api/venues").json()[0]
    assert (venue["latitude"], venue["longitude"]) == (52.1868, 20.8893)
