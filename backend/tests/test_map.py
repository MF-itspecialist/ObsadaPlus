"""Mapa: obiekty z meczami i trasy sędziów."""

import httpx

from app.services import map_service

PERIOD = {"date_from": "2026-10-09", "date_to": "2026-10-12"}


def test_map_matches_statistics(seeded_client):
    c = seeded_client
    preview = c.post("/api/optimization/generate", json=PERIOD).json()
    c.post("/api/optimization/confirm", json={"run_id": preview["run_id"]})

    data = c.get("/api/map", params=PERIOD).json()
    stats = c.get("/api/statistics", params=PERIOD).json()
    assert sum(len(v["matches"]) for v in data["venues"]) == stats["summary"]["matches"]
    assert sum(m["filled"] for v in data["venues"] for m in v["matches"]) == stats["summary"]["slots_filled"]
    km = {r["referee_id"]: r["km"] for r in stats["referees"]}
    for r in data["referees"]:
        assert abs(sum(d["km"] for d in r["days"]) - km[r["referee_id"]]) < 0.5
        for d in r["days"]:
            assert d["stops"] and all(len(s["point"]) == 2 for s in d["stops"])


def test_route_without_osrm_is_a_straight_line(client):
    r = client.get("/api/map/route", params={"points": "52.2,21.0;52.3,21.1;52.2,21.0"}).json()
    assert r == {"path": [[52.2, 21.0], [52.3, 21.1], [52.2, 21.0]], "exact": False}
    assert client.get("/api/map/route", params={"points": "abc"}).status_code == 422
    assert client.get("/api/map/route", params={"points": "952.2,21.0"}).status_code == 422


def test_route_uses_osrm_shape(monkeypatch):
    calls = []

    def fake_get(url, params, timeout):
        calls.append(url)
        geo = {"coordinates": [[21.0, 52.2], [21.05, 52.25], [21.1, 52.3]]}
        return httpx.Response(200, json={"code": "Ok", "routes": [{"geometry": geo}]}, request=httpx.Request("GET", url))

    monkeypatch.setattr(map_service.httpx, "get", fake_get)
    map_service._osrm_shape.cache_clear()
    monkeypatch.setattr(map_service, "get_config", lambda: type("C", (), {"osrm_url": "http://osrm:5000"})())
    r = map_service.route_shape([(52.2, 21.0), (52.3, 21.1)])
    assert r["exact"] and r["path"][1] == [52.25, 21.05]
    assert calls[0].startswith("http://osrm:5000/route/v1/driving/21.000000,52.200000;")


def test_map_requires_admin(anon_client):
    assert anon_client.get("/api/map", params=PERIOD).status_code == 401
