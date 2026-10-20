"""Import rozgrywek seniorskich z 90minut.pl (na zapisanym fragmencie HTML, bez sieci)."""

import datetime as dt

from app.importers.import_service import import_matches
from app.importers.m90_importer import League, M90MatchImporter, league_label, parse_league, parse_region, town_from_team

REGION = """
<a href="/liga/1/liga14742.html" class="main">III liga, gr. I</a>
<a href="/liga/1/liga14764.html" class="main">Decathlon IV liga 2026/2027, grupa: mazowiecka</a>
<a href="/liga/1/liga14870.html" class="main">Keeza Liga okręgowa 2026/2027, grupa: Warszawa I</a>
<a href="/liga/1/liga14939.html" class="main">Keeza Klasa B 2026/2027, grupa: Warszawa I</a>
<a href="/liga/1/liga15142.html" class="main">CLJ</a>
"""


def _row(home, away, when, note=None, score="-"):
    row = (f'<tr align="left"> <td nowrap valign="top" width="180"><b> {home} </b></td> '
           f'<td nowrap valign="top" align="center" width="50"><b>{score}</b></td> '
           f'<td nowrap valign="top" width="180"><b> {away} </b></td> '
           f'<td valign="top" nowrap align="left" width="190">{when}</td> </tr>')
    if note:
        row += f' <tr align="left"> <td colspan="4"><i>{note}</i></td> </tr>'
    return row


LEAGUE = "<table>" + "".join([
    _row("Talent II Warszawa", "Grom Warszawa", "9 sierpnia, 15:00", "na stadionie OSiR Targówek przy ul. Łabiszyńskiej", "2-2"),
    _row("Mazur Radzymin", "Świt II Nowy Dwór Mazowiecki", "8 sierpnia, 14:00", None, "7-0"),
    _row("Advit Wiązowna", "Madziar Nieporęt", "17 września, 20:00", "w pierwotnym terminie (2 września, 19:30) odwołany"),
    _row("KS Halinów", "Agape Białołęka (Warszawa)", "7 marca, 11:00"),
    _row("Ząbkovia II Ząbki", "Grom Warszawa", ""),  # przyszła kolejka bez terminu
]) + "</table>"


def test_region_lists_only_regional_senior_leagues():
    assert parse_region(REGION) == [
        League(14764, "IV liga – mazowiecka"),
        League(14870, "Liga okręgowa – Warszawa I"),
        League(14939, "Klasa B – Warszawa I"),
    ]
    assert league_label("Klasa A 2026/2027, grupa: Radom II") == "Klasa A – Radom II"


def test_league_matches_dates_venues_and_referee_counts():
    records, skipped = parse_league(LEAGUE, League(14870, "Liga okręgowa – Warszawa I"), 2026)
    assert skipped == 1
    first, second, moved, spring = records
    assert (first.date, first.start_time) == (dt.date(2026, 8, 9), dt.time(15, 0))
    assert (first.venue_name, first.venue_city, first.venue_address) == ("Stadion OSiR Targówek", "Warszawa", "ul. Łabiszyńskiej")
    assert (second.venue_name, second.venue_city) == ("Boisko: Mazur Radzymin", "Radzymin")
    assert moved.date == dt.date(2026, 9, 17) and moved.venue_name == "Boisko: Advit Wiązowna"
    assert spring.date == dt.date(2027, 3, 7)  # runda wiosenna = kolejny rok
    assert all(r.required_referees == 3 for r in records)
    assert first.external_id.startswith("90minut:14870:") and len({r.external_id for r in records}) == 4

    b_records, _ = parse_league(LEAGUE, League(14939, "Klasa B – Warszawa I"), 2026)
    assert b_records[0].required_referees == 1


def test_town_from_team_name():
    assert town_from_team("Świt II Nowy Dwór Mazowiecki") == "Nowy Dwór Mazowiecki"
    assert town_from_team("Agape Białołęka (Warszawa)") == "Białołęka, Warszawa"
    assert town_from_team("Pogoń Grodzisk Mazowiecki") == "Grodzisk Mazowiecki"
    assert town_from_team("KS Halinów") == "Halinów"
    assert town_from_team("Iskra Zbrosza Duża") == "Zbrosza Duża"


def test_import_twice_updates_instead_of_duplicating(db_session):
    from app.services.geocoding_service import GeocodeResult, Geocoder

    class TownGeocoder(Geocoder):
        def geocode(self, address, city):
            return None if address else GeocodeResult(52.2, 21.0, city, "", city)  # ulic nie zna → miasto

    pages = {"ligireg": REGION, "liga14764": "", "liga14870": LEAGUE, "liga14939": ""}
    fetch = lambda url: next(v for k, v in pages.items() if k in url)  # noqa: E731
    importer = M90MatchImporter(109, 6, 2026, fetch=fetch, delay_s=0)
    with db_session() as db:
        first = import_matches(db, importer, 105, TownGeocoder())
        again = import_matches(db, M90MatchImporter(109, 6, 2026, fetch=fetch, delay_s=0), 105, TownGeocoder())
    assert (first["created"], first["updated"]) == (4, 0)
    assert (again["created"], again["updated"]) == (0, 4)
    assert first["errors"] == ["Pominięto 1 meczów bez ustalonej daty lub godziny (przyszłe kolejki)"]
