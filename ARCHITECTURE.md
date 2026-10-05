# Obsada+ — architektura MVP

Dokument opisuje proponowaną architekturę, strukturę folderów, modele danych,
algorytm generowania obsady oraz miejsca przygotowane pod rozbudowę.

## 1. Architektura

```
┌──────────────────────────┐   HTTP/JSON   ┌──────────────────────────────────────────┐
│ Frontend (React + TS)    │ ────────────▶ │ Backend (FastAPI)                        │
│ Vite, Tailwind, Router   │               │                                          │
│ pages / components /     │               │  api/        – cienkie routery REST       │
│ services(api) / types    │               │  schemas/    – Pydantic (walidacja I/O)   │
└──────────────────────────┘               │  services/   – logika aplikacyjna          │
                                           │  optimization/ – czysty silnik obsady     │
                                           │      (bez bazy, bez FastAPI → testowalny) │
                                           │  importers/  – MatchImporter (JSON/CSV)   │
                                           │  models/     – SQLAlchemy 2.0 ORM          │
                                           │  database/   – sesja, init, seed           │
                                           └───────────────┬──────────────────────────┘
                                                           │ SQLAlchemy
                                             PostgreSQL (prod/docker) │ SQLite (dev/testy)
```

Zasady:

* **Warstwy**: `api → services → (optimization | models)`. Routery nie zawierają logiki.
* **Silnik optymalizacji jest czysty**: `optimization/` operuje na dataclassach
  (`Problem`, `Slot`, `RefereeProfile`, `ScheduleState`) i nie wie nic o bazie.
  `services/assignment_service.py` buduje `Problem` z bazy i zapisuje wynik.
  Dzięki temu ten sam `Problem` można później przekazać do solvera OR-Tools / CP-SAT.
* **Routing za interfejsem** `RoutingService` (`get_distance`, `get_travel_time`, `get_route`).
  MVP: `HaversineRoutingService` (odległość po łuku × współczynnik drogowy, średnia prędkość).
  Wybór implementacji przez konfigurację (`ROUTING_PROVIDER`) w fabryce `get_routing_service()`.
* **Ograniczenia twarde jako osobne klasy** (`HardConstraint`), składane w listę.
  Nowe ograniczenie = nowa klasa + dopisanie do listy, bez zmian w generatorze.
* **Scoring jako suma składników** (`ScoreComponent`) z wagami z ustawień systemu.
* **Podgląd → zatwierdzenie**: generator zapisuje propozycję jako `GenerationRun`
  (status `PREVIEW`), a `POST /api/optimization/confirm` zapisuje ją jako obsadę.
* **Ustawienia w bazie** (`system_settings`, klucz → wartość JSON) z domyślnymi
  wartościami w kodzie; edytowalne w UI (np. `transport_safety_buffer_minutes = 15`).

## 2. Struktura folderów

```
obsada-plus/
├── docker-compose.yml          # postgres + backend + frontend
├── README.md
├── ARCHITECTURE.md
├── backend/
│   ├── Dockerfile, requirements.txt, alembic.ini, pytest.ini
│   ├── alembic/                # migracje (PostgreSQL / SQLite)
│   ├── app/
│   │   ├── main.py             # FastAPI app, CORS, routery
│   │   ├── config.py           # konfiguracja z ENV (DATABASE_URL, ROUTING_PROVIDER…)
│   │   ├── database/           # db.py (engine, SessionLocal, Base), init_db.py, seed.py
│   │   ├── models/             # enums, referee, venue, match, availability, assignment,
│   │   │                       # system_setting, generation_run
│   │   ├── schemas/            # Pydantic: referee, venue, match, availability, assignment,
│   │   │                       # optimization, settings, dashboard
│   │   ├── api/                # referees, venues, matches, availability, assignments,
│   │   │                       # optimization, settings, dashboard
│   │   ├── services/           # routing_service, availability_service, scoring_service,
│   │   │                       # assignment_service, settings_service, statistics_service
│   │   ├── optimization/       # domain, constraints, scoring, generator, explanations
│   │   └── importers/          # base (MatchImporter), json_importer, csv_importer,
│   │                           # manual_importer, import_service
│   └── tests/                  # test_generator.py, test_routing.py, test_api.py
└── frontend/
    ├── Dockerfile, nginx.conf, package.json, vite.config.ts
    └── src/
        ├── pages/              # Dashboard, Matches, Referees, Availability,
        │                       # Assignments (Obsada), Venues, Settings
        ├── components/         # Layout, StatCard, Modal, PeriodPicker, Explanation…
        ├── services/           # api.ts (klient REST)
        ├── context/            # PeriodContext (wybrany weekend)
        ├── types/              # typy odpowiadające schematom Pydantic
        └── utils/              # formatowanie dat, godzin, km
```

## 3. Modele danych

| Tabela | Kluczowe pola | Uwagi |
|---|---|---|
| `referees` | first_name, last_name, city, address, latitude, longitude, active, preferred/max_matches_per_day, preferred/max_matches_per_weekend, notes | pod rozbudowę: `level` (klasa), `licenses` przez osobną tabelę |
| `venues` | name, city, address, latitude, longitude | |
| `matches` | external_id (unikalne, do importu), date, start_time, estimated_end_time, league, home_team, away_team, venue_id, required_referees, arrival_before_minutes, status | `status`: UNASSIGNED / PARTIALLY_ASSIGNED / ASSIGNED / CANCELLED |
| `availability` | referee_id, date, available_from, available_to, available | unikalne (referee_id, date); `from/to = NULL` → cały dzień |
| `assignments` | match_id, referee_id, role, manually_modified, score, distance_km, travel_minutes, explanation (JSON) | unikalne (match_id, role); `role` enum: MAIN, ASSISTANT_1, ASSISTANT_2, FOURTH, OBSERVER |
| `system_settings` | key, value (JSON) | bufor bezpieczeństwa, wagi, progi kar |
| `generation_runs` | created_at, status, params, result, stats (JSON) | podgląd → zatwierdzenie, historia generowań |

Liczba sędziów na mecz: `required_referees` mapuje się na role
(`1 → MAIN`, `3 → MAIN + A1 + A2`, `4 → + FOURTH`). Generator obsługuje sloty
(mecz, rola) ogólnie, więc obsady 3-osobowe działają bez zmiany modelu;
dane testowe MVP używają 1 sędziego.

## 4. Algorytm MVP (`AssignmentGenerator`, strategia zachłanna ze scoringiem)

1. Zbuduj `Problem`: sloty (mecz × rola) w wybranym okresie, aktywni sędziowie,
   dyspozycyjność, ustawienia. Przypisania ręczne (`manually_modified`) są
   **zablokowane** i trafiają od razu do harmonogramu sędziów (chyba że tryb
   „Generuj całość od nowa”).
2. Sloty sortowane chronologicznie (data, godzina startu).
3. Dla każdego slotu, dla każdego sędziego sprawdź **ograniczenia twarde**:
   aktywny → dostępny w dniu → mecz (od wymaganego przyjazdu do końca) mieści się
   w oknie dyspozycyjności → brak nakładania się meczów → możliwość dojazdu
   (z poprzedniego meczu **i** na następny już przydzielony mecz) →
   `max_matches_per_day` → `max_matches_per_weekend`.
4. Punkt startowy dojazdu: **poprzedni mecz tego dnia** (jeśli jest), inaczej **dom**.
   Warunek: `koniec_poprzedniego + czas_przejazdu + bufor ≤ start − arrival_before`.
   Dla pierwszego meczu dnia: `available_from + czas_przejazdu ≤ wymagany przyjazd`.
5. Oblicz **SCORE** (niższy = lepszy):
   `kara_progowa(km) + km·DISTANCE_WEIGHT + min·TRAVEL_TIME_WEIGHT +
   kara_dzienna + kara_weekendowa + kara_wyrównania`.
   * progi km: 0–10: 0, 10–20: 10, 20–30: 30, 30–50: 70, 50–75: 150, 75+: 300,
   * kara dzienna: kolejny mecz w granicach `preferred` – mała (¼ wagi),
     powyżej `preferred` – duża (1,5× wagi); `max` – twarde ograniczenie,
   * analogicznie weekend,
   * wyrównanie: `WORKLOAD_WEIGHT × max(0, mecze_sędziego − średnia)` – działa jak
     rozstrzygnięcie przy podobnej logistyce, nie przebija odległości.
6. Wybierz sędziego z najniższym SCORE, dopisz do harmonogramu, zapisz
   uzasadnienie (✓ dostępny 08:00–18:00, ✓ odległość 7.4 km, …) i rozbicie SCORE.
7. Gdy brak kandydata: slot nieobsadzony, a przyczyny to zliczone odrzucenia
   (np. „konflikty czasowe: 4 sędziów, przekroczony limit: 2, brak dojazdu: 3”).
8. Statystyki: mecze, obsadzone, nieobsadzone, aktywni sędziowie, średnia
   meczów/sędziego, średnia i łączna odległość, liczba konfliktów.

## 5. Przygotowane pod rozbudowę

| Przyszła funkcja | Miejsce w kodzie |
|---|---|
| Google Maps / OSRM / OpenStreetMap | nowa klasa `RoutingService` + wpis w fabryce `get_routing_service()` |
| OR-Tools / CP-SAT / optymalizacja całego weekendu | nowa `AssignmentStrategy` operująca na tym samym `Problem` → `GenerationResult` |
| Terminarz Łączy Nas Piłka | `LNPMatchImporter` czyta eksport z zakładki `tools/lnp-export.js` (API LNP wymaga reCAPTCHA, więc pobiera przeglądarka użytkownika); upsert po `external_id` |
| Obsady G + A1 + A2, sędzia techniczny, obserwator | enum `RefereeRole`, sloty (mecz × rola), unikalność (match_id, role) |
| Klasy sędziowskie, uprawnienia do lig, preferowane ligi, regiony, unikanie klubów, konflikt interesów | nowe klasy `HardConstraint` / `ScoreComponent`, pola w `RefereeProfile` |
| Kilometrówka, mapa tras, wspólny przejazd | `distance_km` / `travel_minutes` per przypisanie, `RoutingService.get_route()` |
| Historia zmian, statystyki miesięczne/sezonowe | `generation_runs` (JSON z wynikiem), `statistics_service` |
| Ustawienia systemu | `system_settings` + `settings_service` (już edytowalne w UI) |
| Logowanie, role, panel sędziego, zgłaszanie dyspozycyjności | osobny moduł `auth/` + zależność FastAPI w `api/deps.py`; API dyspozycyjności już gotowe |
| Eksport PDF/Excel, publikacja, powiadomienia | nowe serwisy korzystające z `assignment_service` |
