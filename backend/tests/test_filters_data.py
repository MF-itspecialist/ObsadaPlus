"""Dane do filtrów: podokręg, klasa z licencji, kod pocztowy obiektu."""

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
