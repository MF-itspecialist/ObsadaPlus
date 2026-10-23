# Obsada+ — automatyczna obsada sędziowska (MVP)

Aplikacja webowa, która układa obsadę sędziowską na mecze piłkarskie. Bierze pod uwagę
dyspozycyjność sędziów, czas i odległość dojazdu (także pomiędzy kolejnymi meczami),
wymagany czas przyjazdu, bufor bezpieczeństwa, limity dzienne i weekendowe oraz
równomierne rozłożenie spotkań. Logistyka ma największy wpływ na wybór.

* **Backend:** Python 3.11+, FastAPI, SQLAlchemy 2.0, Pydantic 2, Alembic
* **Baza:** PostgreSQL (docker) / SQLite (dev, testy)
* **Frontend:** React 19, TypeScript, Tailwind CSS 4, Vite, ikony lucide-react, font Inter
* **Optymalizacja:** własny algorytm scoringowy (strategia wymienna na OR-Tools / CP-SAT)
* **Routing:** `RoutingService` → Google Maps (Routes API, z kluczem) albo OSRM w Dockerze (bez klucza); szacunek, gdy serwis nie odpowiada

Szczegóły architektury, modele i punkty rozbudowy: [ARCHITECTURE.md](ARCHITECTURE.md).
Zrzuty ekranu: [docs/screenshots](docs/screenshots).

---

## Szybki start (Docker)

Dwie wersje — różnią się tylko źródłem tras:

| Wersja | Polecenie (Windows) | Polecenie (Linux/macOS) |
|---|---|---|
| **bez Google** — własny serwer OSRM na mapie OpenStreetMap | `powershell -ExecutionPolicy Bypass -File scripts\start-osrm.ps1` | `scripts/start-osrm.sh` |
| **z Google Maps** — klucz `GOOGLE_MAPS_API_KEY` w `.env` | `powershell -ExecutionPolicy Bypass -File scripts\start-google.ps1` | `scripts/start-google.sh` |

Bez skryptów: `docker compose --profile osrm up --build` (OSRM) lub `docker compose up --build`.
Przy `ROUTING_PROVIDER=auto` (domyślnie) backend wybiera sam: **Google, gdy jest klucz → OSRM →
szacunek** (linia prosta × 1,3). Wzór pliku `.env`: [.env.example](.env.example).

OSRM przy pierwszym starcie pobiera mapę województwa mazowieckiego (~150 MB, Geofabrik)
i przygotowuje ją do liczenia tras (kilka–kilkanaście minut, ok. 2–4 GB RAM dla Dockera).
Do tego czasu generator liczy trasy szacunkowo. Inny region: `OSRM_PBF_URL` w `.env`.
Klucz Google musi mieć włączone **Routes API** (trasy) i **Geocoding API** (adresy).
Każda trasa z Google/OSRM jest zapisywana w tabeli `route_cache`, więc za tę samą parę
punktów Google płaci się tylko raz.

| Usługa | Adres |
|---|---|
| Panel (frontend + proxy `/api`) | http://localhost:3000 |
| API / Swagger | http://localhost:8000/docs |
| Podgląd bazy (Adminer) | http://localhost:8080 (PostgreSQL, serwer `postgres`, obsada / obsada / baza obsada) |
| PostgreSQL | localhost:5432 (obsada / obsada) |

Przy pierwszym starcie backend wykonuje migracje i wczytuje dane testowe
(dni obsadowe **9–12.10.2026, piątek–poniedziałek**: 10 obiektów, 12 sędziów, 24 mecze). Wybierz ten okres
w nagłówku panelu i kliknij **Obsada → GENERUJ OBSADĘ**.

## Instalacja backendu (bez Dockera)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                       # domyślnie SQLite: ./obsada.db
python -m app.database.init_db --seed      # migracje + dane testowe
uvicorn app.main:app --reload              # http://localhost:8000/docs
```

Inne polecenia:

```bash
python -m app.database.init_db --reset     # wyczyść bazę i wczytaj dane testowe od nowa
pytest                                     # testy (generator, routing, API)
alembic revision --autogenerate -m "opis"  # nowa migracja po zmianie modeli
```

## Instalacja frontendu

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173 (proxy /api → http://localhost:8000)
npm run build      # produkcyjny build do dist/
```

## Konfiguracja

Zmienne środowiskowe backendu (`backend/.env`):

| Zmienna | Domyślnie | Opis |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./obsada.db` | np. `postgresql+psycopg2://obsada:obsada@localhost:5432/obsada` |
| `CORS_ORIGINS` | `http://localhost:5173,…` | originy frontendu |
| `ROUTING_PROVIDER` | `auto` | `auto` (Google → OSRM → szacunek), `google`, `osrm`, `haversine` |
| `GOOGLE_MAPS_API_KEY` | pusty | klucz Google (Routes API + Geocoding API); ma pierwszeństwo |
| `OSRM_URL` | pusty (`http://osrm:5000` w Dockerze) | serwer OSRM |
| `AUTO_CREATE_TABLES` | `true` | migracje Alembic przy starcie |
| `SEED_ON_STARTUP` | `false` | dane testowe przy starcie, gdy baza pusta |

Frontend: `VITE_API_URL` (domyślnie pusty — ten sam host), `VITE_PROXY_TARGET` dla `npm run dev`.

Parametry biznesowe edytuje się w panelu (**Ustawienia**) — są w tabeli `system_settings`:
bufor bezpieczeństwa transportu (15 min), wagi scoringu, progi kar za odległość,
średnia prędkość i współczynnik krętości dróg, traktowanie braku zgłoszenia dyspozycyjności.

## Struktura projektu

```
backend/app/
  main.py            FastAPI, CORS, routery
  config.py          konfiguracja z ENV
  database/          engine i sesja, init_db (Alembic), seed + seed_data
  models/            Referee, Venue, Match, Availability, Assignment, SystemSetting, GenerationRun, enums
  schemas/           Pydantic: walidacja wejścia i odpowiedzi
  api/               referees, venues, matches, availability, assignments, optimization, settings, dashboard
  services/          routing_service, availability_service, problem_builder, scoring_service,
                     assignment_service, settings_service, statistics_service
  optimization/      domain, state, context, constraints, scoring, evaluator, generator (bez zależności od bazy)
  importers/         MatchImporter + Manual/JSON/CSV/LNP, import_service
backend/tests/       test_generator.py, test_routing.py, test_api.py
frontend/src/        pages, components, services/api.ts, context, hooks, types, utils
examples/            matches.json, matches.csv — przykładowe pliki importu
tools/               lnp-export.js — zakładka eksportu terminarza z laczynaspilka.pl
```

## Struktura bazy

| Tabela | Najważniejsze kolumny |
|---|---|
| `referees` | imię, nazwisko, miasto, adres, `latitude/longitude`, `active`, `preferred/max_matches_per_day`, `preferred/max_matches_per_weekend`, `notes` |
| `venues` | nazwa, miasto, adres, `latitude/longitude` |
| `matches` | `external_id` (unikalne), `date`, `start_time`, `estimated_end_time`, liga, drużyny, `venue_id`, `required_referees`, `arrival_before_minutes`, `status` |
| `availability` | `referee_id`, `date` (unikalna para), `available_from/to` (NULL = cały dzień), `available` |
| `assignments` | `match_id`, `referee_id`, `role` (MAIN, ASSISTANT_1, ASSISTANT_2, FOURTH, OBSERVER), `manually_modified`, `score`, `distance_km`, `travel_minutes`, `explanation` (JSON) |
| `system_settings` | `key`, `value` (JSON) |
| `generation_runs` | wynik generowania: `status` (PREVIEW / CONFIRMED), parametry, propozycja, statystyki |

Schemat tworzy migracja `backend/alembic/versions/0001_initial_schema.py` (PostgreSQL i SQLite).

## Generator obsady

`AssignmentGenerator.generate_assignments(problem)` (`app/optimization/generator.py`):

1. `problem_builder` buduje `Problem` z bazy: sloty (mecz × rola) w wybranym okresie,
   sędziowie z dyspozycyjnością, ustawienia. Przypisania **ręczne** oraz przypisania z
   tej samej kolejki spoza okresu są **zablokowane** (wliczają się do limitów i logistyki).
   Tryb „Generuj całość od nowa” blokuje tylko te spoza okresu.
2. Sloty przetwarzane chronologicznie. Dla każdego oceniani są wszyscy sędziowie.
3. **Twarde ograniczenia** (`constraints.py`, ewaluacja do pierwszego niespełnionego):
   aktywny → dyspozycyjność w dniu → mecz (od wymaganego przyjazdu do końca) w oknie godzin
   → brak nakładania się meczów → limit dzienny → limit weekendowy (dni obsadowe pt–pon)
   → możliwość dojazdu.
4. **Dojazd**: punkt startowy to poprzedni mecz tego dnia, a gdy go nie ma — dom.
   `koniec_poprzedniego + przejazd + bufor ≤ start − arrival_before`. Dla pierwszego meczu
   dnia: `początek_dyspozycyjności + przejazd + bufor ≤ wymagany przyjazd`. Sprawdzany jest
   też przejazd na **następny** już przydzielony mecz (np. ręczny).
5. Wybierany jest sędzia o najniższym SCORE; zapisywane jest uzasadnienie (✓ …) i rozbicie SCORE.
   Mecz z **jednym** sędzią: decyduje dojazd tego sędziego z jego lokalizacji.
   Mecz z **zespołem** (G + A1 + A2): generator wybiera cały skład naraz — najwięcej
   obsadzonych ról, potem najniższy koszt zespołu = suma SCORE trzech sędziów (każdy ze
   swoim dojazdem i limitami) + `crew_route_weight × km wspólnego dojazdu` (kierowca zabiera
   pozostałych po drodze; liczona najkrótsza kolejność). Wygrywają sędziowie mieszkający
   blisko obiektu i blisko siebie. Sędzia główny musi mieć licencję na ligę meczu.
6. Gdy nikt nie spełnia ograniczeń: mecz `UNASSIGNED` z policzonymi przyczynami
   („konflikty czasowe: 4 sędz.”, „brak możliwości transportu: 2 sędz.” …).
7. Statystyki: mecze, obsadzone, nieobsadzone, aktywni sędziowie, średnio meczów / sędziego,
   średnia i łączna odległość, liczba konfliktów.

Przepływ: **GENERUJ** (`POST /api/optimization/generate`) → **PODGLĄD** (zapisany jako
`generation_runs`, obsada bez zmian) → **ZATWIERDŹ** (`POST /api/optimization/confirm`).

## Scoring

Niższy SCORE = lepszy kandydat. `score = distance_penalty + travel_time_penalty +
daily_matches_penalty + weekend_matches_penalty + workload_balance_penalty`.

| Składnik | Wzór (domyślne wagi) |
|---|---|
| odległość | kara progowa (0–10 km: 0, 10–20: 10, 20–30: 30, 30–50: 70, 50–75: 150, 75+: 300) + `km × 2` |
| czas transportu | `min × 0.5` |
| mecze w dniu | każdy kolejny mecz w granicach `preferred`: `20 × 0.25 = 5`; powyżej `preferred`: `20 × 1.5 = 30`; `max` — twardy limit |
| mecze w weekend | analogicznie z wagą 10 |
| wyrównanie | `10 × max(0, mecze_sędziego − średnia)` |

Przykład z wymagań: sędzia A 5 km od meczu z 2 meczami tego dnia (trzeci mecz ≈ 5 + 30 kary
za obciążenie) wygrywa z sędzią B 55 km dalej bez meczów (sama odległość ≈ 150 + 110).
Logistyka wygrywa z idealną równością, a równość rozstrzyga przy podobnej logistyce.

Odległość i czas: z Google Maps lub OSRM (trasy drogowe). Bez nich szacunek: linia prosta × 1,3
(krętość dróg), czas: km / 40 km/h + 5 min (0 min, gdy to ten sam obiekt). Parametry w Ustawieniach.

## Logowanie i role

Całe API (poza `/api/health` i `/api/auth/*`) wymaga zalogowania. Role:

- **Obsadzający** (`ADMIN`) — pełny dostęp, zarządza kontami w zakładce *Użytkownicy*.
- **Sędzia** (`REFEREE`) — konto powiązane z sędzią z listy; widzi tylko swoje dane (panel sędziego).

Hasła są przechowywane jako skrót scrypt, sesja to losowy token w ciasteczku HttpOnly
(w bazie tylko jego SHA-256), ważny 30 dni (`SESSION_DAYS`). Po 5 błędnych hasłach login
jest blokowany na 5 minut. Pierwsze konto: zmienne `ADMIN_LOGIN` / `ADMIN_PASSWORD`
(tworzone przy starcie, gdy w bazie nie ma żadnego konta).

## Przykładowe API

Pełna dokumentacja: http://localhost:8000/docs.

| Metoda | Ścieżka | Opis |
|---|---|---|
| GET / POST | `/api/referees` | lista / dodanie sędziego |
| PUT / DELETE | `/api/referees/{id}` | edycja / usunięcie |
| GET | `/api/referees/overview?date_from&date_to` | dostępność i liczba meczów per dzień |
| GET / POST / PUT / DELETE | `/api/venues[/{id}]` | obiekty |
| GET / POST | `/api/matches` | lista (`date_from`, `date_to`, `status`) / dodanie |
| PUT / DELETE | `/api/matches/{id}` | edycja (także odwołanie) / usunięcie |
| POST | `/api/matches/import` | import pliku `.json` / `.csv` (upsert po `external_id`) |
| POST | `/api/matches/import/json` | import listy rekordów w treści żądania |
| GET / POST | `/api/availability` | lista / zapis (upsert) dyspozycyjności |
| POST | `/api/availability/bulk` | zapis wielu dni naraz |
| GET | `/api/assignments` | przypisania |
| GET | `/api/assignments/board?date_from&date_to` | widok obsady z bieżącymi konfliktami |
| GET | `/api/assignments/candidates?match_id&role` | ranking sędziów dla meczu |
| POST / PUT / DELETE | `/api/assignments[/{id}]` | ręczne przypisanie / zmiana / usunięcie |
| GET | `/api/assignments/export.pdf?date_from&date_to` | bieżąca obsada jako PDF (A4 poziomo) |
| GET | `/api/assignments/export.xlsx?date_from&date_to` | obsada w Excelu: arkusz meczów + rozpiska na sędziów z km |
| POST | `/api/publications` | publikacja obsady okresu jako kolejnej wersji (zamrożona kopia) |
| GET | `/api/publications/latest?date_from&date_to` | ostatnia wersja i mecze zmienione od publikacji |
| GET | `/api/publications/{id}[/pdf]` | opublikowana wersja (JSON / PDF) |
| POST | `/api/auth/login` · `/api/auth/logout` | logowanie (ciasteczko `obsada_session`, HttpOnly) / wylogowanie |
| GET / POST | `/api/auth/me` · `/api/auth/password` | zalogowany użytkownik / zmiana własnego hasła |
| GET / POST / PUT / DELETE | `/api/users[/{id}]` | konta (tylko obsadzający); `POST /api/users/{id}/reset-password` |
| GET | `/api/me/matches` | panel sędziego: jego mecze z opublikowanej obsady |
| GET / PUT | `/api/me/availability` | panel sędziego: własna dyspozycyjność (od jutra, do 120 dni) |
| POST | `/api/optimization/generate` | propozycja obsady (podgląd) |
| POST | `/api/optimization/confirm` | zatwierdzenie podglądu |
| GET | `/api/optimization/runs[/{id}]` | historia generowań |
| GET / PUT | `/api/settings` | ustawienia systemu |
| GET | `/api/dashboard?date_from&date_to` | statystyki weekendu |

```bash
curl -c sesja.txt -X POST localhost:8000/api/auth/login \
  -H 'Content-Type: application/json' -d '{"login": "admin", "password": "…"}'

curl -b sesja.txt -X POST localhost:8000/api/optimization/generate \
  -H 'Content-Type: application/json' \
  -d '{"date_from": "2026-10-10", "date_to": "2026-10-11", "mode": "KEEP_MANUAL"}'
# → {"run_id": 1, "stats": {...}, "assignments": [...], "unassigned": [...]}

curl -b sesja.txt -X POST localhost:8000/api/optimization/confirm \
  -H 'Content-Type: application/json' -d '{"run_id": 1}'
```

Format importu (JSON lub CSV z tymi nagłówkami, separator `,` lub `;`): `external_id, date,
start_time, estimated_end_time (opcjonalnie), league, home_team, away_team, venue_id`
**lub** `venue_name` (+ `venue_city, venue_address, venue_latitude, venue_longitude`, aby
utworzyć nowy obiekt), `required_referees, arrival_before_minutes`. Przykłady w `examples/`.

### Terminarz z Łączy Nas Piłka

API terminarza laczynaspilka.pl wydaje token dopiero po przejściu Google reCAPTCHA, dlatego
Obsada+ nie pobiera go sama. Dane zbiera zakładka uruchamiana w Twojej przeglądarce:

1. Utwórz zakładkę, a jako jej adres wklej zawartość `tools/lnp-export.bookmarklet.txt`
   (po zmianie `tools/lnp-export.js`: `node tools/build-bookmarklet.mjs`). Zamiast zakładki
   możesz wkleić `tools/lnp-export.js` w konsoli przeglądarki (F12).
2. Otwórz terminarz na laczynaspilka.pl/rozgrywki z wybranym sezonem i województwem i kliknij
   zakładkę. Pobierze rozgrywki ZPN (IV liga – juniorzy D2) i zapisze `lnp-terminarz-RRRR-MM-DD.json`.
3. Wgraj plik w **Mecze → Import JSON / CSV**. Importowane są mecze od dziś; ponowny import
   aktualizuje mecze (klucz `lnp:<id meczu>`), bez dublowania.

Obiekty dopasowywane są po nazwie (bez nazwy boiska: boisko gospodarza). Nieznane obiekty
import wypisuje raz na obiekt; dodaj je w zakładce Obiekty i zaimportuj plik ponownie.
Liczba sędziów: IV liga, V liga, klasa okręgowa i klasa A 3 (główny + 2 asystentów), pozostałe 1 (`REFEREES_BY_LEVEL`
w `importers/lnp_importer.py`).

## Testy

`pytest` w katalogu `backend` (testy generatora, zespołów, tras i API). Scenariusze generatora: sędzia niedostępny,
konflikt dwóch meczów, brak czasu na transport (przykład 11:45 + 35 + 15 > 12:15),
konfigurowalny bufor, blokada dojazdu na późniejszy ręczny mecz, `max_matches_per_day`
i 4. mecz przy max 3, limit weekendowy, wybór bliższego sędziego, poprzedni mecz jako punkt
startowy, równomierne rozdawanie, brak dostępnego sędziego, reguła „logistyka przed równością”,
zachowanie ręcznych przypisań. Testy API: CRUD, walidacja, podgląd → zatwierdzenie,
ręczne zmiany a ponowne generowanie, ostrzeżenia o konfliktach, import JSON/CSV, ustawienia.

## Rozbudowa

* Routing: dopisz `OSRMRoutingService` / `GoogleMapsRoutingService` w `services/routing_service.py`
  i zarejestruj w `get_routing_service()`; wynik jest cache'owany przez `CachedRoutingService`.
* Optymalizacja globalna: nowa `AssignmentStrategy` (np. CP-SAT) w `optimization/generator.py`,
  przyjmuje ten sam `Problem`, zwraca ten sam `GenerationResult`.
* Nowe reguły (uprawnienia do lig, klasa sędziego, konflikt interesów, regiony): nowa klasa
  `HardConstraint` lub `ScoreComponent` i dopisanie do `DEFAULT_CONSTRAINTS` / `DEFAULT_COMPONENTS`.
* Zespoły G + A1 + A2: `required_referees = 3` już tworzy trzy sloty; do dodania zasady
  wspólnego przejazdu jako `ScoreComponent`.
