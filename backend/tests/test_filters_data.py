"""Dane do filtrów: podokręg, klasa z licencji, kod pocztowy obiektu."""

from sqlalchemy import select

from app.models import Referee, Venue
from app.optimization.licenses import license_class
from app.regions import region_for
from app.services.geocoding_service import GeocodeResult, Geocoder
from app.services.venue_address_service import fill_venue_addresses


def test_region_from_notes_tag_then_nearest_seat():
    assert region_for(52.25, 21.0, "Dane robocze (fikcyjne), podokręg Radom") == "Radom"
    assert region_for(52.25, 21.0, "Dane robocze (fikcyjne)") == "Warszawa"
    assert region_for(52.55, 19.70) == "Płock"
    assert region_for(53.11, 20.38) == "Ciechanów"  # Mława
    assert region_for(None, None) == ""


def test_license_class_is_highest_main_level():
    assert license_class(["Sędzia klasa A", "Sędzia IV liga"]) == (4, "IV liga")
    assert license_class(["Sędzia klasa okręgowa"])[1] == "Klasa okręgowa"
    assert license_class(["Asystent okręgowy / pozostali"])[1] == "Tylko asystent"
    assert license_class([])[1] == "Bez licencji"
    assert license_class(["Sędzia V liga"])[0] < license_class(["Sędzia klasa B"])[0]


def test_referee_read_exposes_region_and_class():
    ref = Referee(first_name="A", last_name="B", city="Płock", latitude=52.54, longitude=19.7, licenses=["Sędzia V liga"])
    assert (ref.region, ref.license_class) == ("Płock", "V liga")


class ReverseGeocoder(Geocoder):
    def __init__(self, hits):
        self.hits = hits
        self.calls = 0

    def geocode(self, address, city):
        return None

    def reverse(self, latitude, longitude):
        self.calls += 1
        return self.hits.get((latitude, longitude))


def test_fill_venue_addresses_only_fills_empty_fields(db_session):
    db = db_session()
    typed = Venue(name="Stadion A", city="Płock", address="ul. Ręczna 1", latitude=52.5, longitude=19.7)
    empty = Venue(name="Boisko B", city="", address="", latitude=52.2, longitude=21.0)
    unknown = Venue(name="Boisko C", city="Wieś", address="", latitude=51.0, longitude=20.0)
    shared = [Venue(name=f"Boisko {n}", city="Mława", address="", latitude=53.11, longitude=20.38) for n in "EF"]
    done = Venue(name="Stadion D", city="Radom", address="Struga 63", postal_code="26-600", latitude=51.4, longitude=21.1)
    db.add_all([typed, empty, unknown, done, *shared])
    db.commit()
    geo = ReverseGeocoder({
        (52.5, 19.7): GeocodeResult(52.5, 19.7, "Płock", "", "", postal_code="09-400", street="Mapowa 5"),
        (52.2, 21.0): GeocodeResult(52.2, 21.0, "Warszawa", "Wola", "", postal_code="01-234", street="Kolejowa 7"),
        (53.11, 20.38): GeocodeResult(53.11, 20.38, "Mława", "", "", postal_code="06-500", street="Rynek 1"),
    })
    report = fill_venue_addresses(db, geo)
    assert (report.checked, report.filled, geo.calls) == (5, 4, 5)
    assert report.not_found == ["Boisko C (Wieś)"]
    assert (typed.address, typed.postal_code) == ("ul. Ręczna 1", "09-400")
    assert (empty.address, empty.city, empty.postal_code) == ("Kolejowa 7", "Warszawa", "01-234")
    assert done.postal_code == "26-600"
    # pinezka w centrum Mławy (dwa obiekty w tym samym punkcie): kod tak, ulica nie
    assert [(v.address, v.postal_code) for v in shared] == [("", "06-500"), ("", "06-500")]


def test_reserve_teams_share_club_venue(db_session):
    import datetime as dt

    from app.importers.m90_importer import club_name
    from app.models import Match
    from app.services.venue_merge_service import merge_reserve_venues

    assert club_name("Agape II Białołęka (Warszawa)") == "Agape Białołęka (Warszawa)"
    assert club_name("KS II Wesoła (Warszawa)") == "KS Wesoła (Warszawa)"
    assert club_name("Ursus IV Warszawa") == "Ursus Warszawa"

    db = db_session()
    first = Venue(name="Boisko: Agape Białołęka (Warszawa)", city="Białołęka, Warszawa", latitude=52.32, longitude=21.0)
    reserve = Venue(name="Boisko: Agape II Białołęka (Warszawa)", city="Białołęka, Warszawa", latitude=52.2, longitude=21.1)
    only_reserve = Venue(name="Boisko: Orły II Zielonka", city="Zielonka", latitude=52.3, longitude=21.15)
    stadium = Venue(name="Stadion Hutnika", city="Warszawa", latitude=52.28, longitude=20.96)
    db.add_all([first, reserve, only_reserve, stadium])
    db.flush()
    m = Match(date=dt.date(2026, 10, 10), start_time=dt.time(11), estimated_end_time=dt.time(13), home_team="Agape II Białołęka (Warszawa)",
              away_team="X", league="Klasa B", venue_id=reserve.id)
    db.add(m)
    db.commit()

    report = merge_reserve_venues(db)
    assert report.merged == ["Boisko: Agape II Białołęka (Warszawa) → Boisko: Agape Białołęka (Warszawa)"]
    assert report.renamed == ["Boisko: Orły II Zielonka → Boisko: Orły Zielonka"]
    db.refresh(m)
    assert m.venue_id == first.id
    assert sorted(v.name for v in db.scalars(select(Venue))) == [
        "Boisko: Agape Białołęka (Warszawa)", "Boisko: Orły Zielonka", "Stadion Hutnika"]
    assert merge_reserve_venues(db).merged == []  # drugi raz nic nie zmienia


def test_locate_stadiums_moves_pin_to_google_place(db_session):
    from app.services.stadium_lookup_service import Place, locate_stadiums, query_for

    db = db_session()
    club = Venue(name="Boisko: Agape Białołęka (Warszawa)", city="Białołęka, Warszawa", latitude=52.32, longitude=21.0)
    far = Venue(name="Boisko: Chojniak Wieniawa", city="Wieniawa", latitude=51.35, longitude=20.80)
    missing = Venue(name="Boisko: GKS Łyse", city="Łyse", latitude=53.36, longitude=21.56)
    db.add_all([club, far, missing])
    db.commit()
    assert query_for(club) == "stadion Agape Białołęka Warszawa"

    class FakePlaces:
        def search(self, query):
            return {
                "stadion Agape Białołęka Warszawa": [
                    Place("Sklep", 52.0, 21.0, "", "", "Warszawa", False),
                    Place("Boisko Agape", 52.3301, 20.9702, "Talarowa 2", "03-187", "Warszawa", True),
                ],
                "stadion Chojniak Wieniawa": [Place("Wieniawa Lublin", 51.25, 22.54, "Racławickie 13", "20-059", "Lublin", True)],
            }.get(query, [])

    report = locate_stadiums(db, FakePlaces())
    assert report.updated == ["Boisko: Agape Białołęka (Warszawa)"]
    assert (club.latitude, club.longitude, club.address, club.postal_code) == (52.3301, 20.9702, "Talarowa 2", "03-187")
    assert len(report.too_far) == 1 and far.latitude == 51.35  # Lublin zamiast Wieniawy pod Przysuchą — bez zmian
    assert report.not_found == ["Boisko: GKS Łyse (Łyse)"]
