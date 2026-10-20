"""Przykładowe dane: Warszawa i okolice, dni obsadowe 9–12 października 2026 (pt–pon).

Niedziela jest celowo "ciasna" (mało dyspozycyjności wieczorem), żeby pokazać
mecz bez obsady i przyczyny w UI."""

FRIDAY = "2026-10-09"
SATURDAY = "2026-10-10"
SUNDAY = "2026-10-11"
MONDAY = "2026-10-12"

VENUES = [
    {"name": "Stadion KS Ursus", "city": "Warszawa", "address": "ul. Sosnkowskiego 3", "latitude": 52.1960, "longitude": 20.8840},
    {"name": "Stadion Polonii", "city": "Warszawa", "address": "ul. Konwiktorska 6", "latitude": 52.2560, "longitude": 21.0000},
    {"name": "Boisko Escola Varsovia", "city": "Warszawa", "address": "ul. Czerniakowska 128", "latitude": 52.2090, "longitude": 21.0500},
    {"name": "Stadion Hutnika", "city": "Warszawa", "address": "ul. Marymoncka 42", "latitude": 52.2850, "longitude": 20.9620},
    {"name": "Stadion Miejski Legionowo", "city": "Legionowo", "address": "ul. Parkowa 13", "latitude": 52.4010, "longitude": 20.9300},
    {"name": "Stadion OSiR Piaseczno", "city": "Piaseczno", "address": "ul. 1 Maja 16", "latitude": 52.0760, "longitude": 21.0170},
    {"name": "Stadion Znicza", "city": "Pruszków", "address": "ul. Bohaterów Warszawy 4", "latitude": 52.1650, "longitude": 20.8100},
    {"name": "Stadion Startu", "city": "Otwock", "address": "ul. Kraszewskiego 6", "latitude": 52.1060, "longitude": 21.2580},
    {"name": "Stadion Marcovii", "city": "Marki", "address": "ul. Wspólna 2", "latitude": 52.3270, "longitude": 21.1040},
    {"name": "Stadion Dolcanu", "city": "Ząbki", "address": "ul. Słowackiego 21", "latitude": 52.2930, "longitude": 21.1110},
]

# (imię, nazwisko, miasto, dzielnica, adres, lat, lng, licencje, aktywny, pref/dzień, max/dzień, pref/weekend, max/weekend)
REFEREES = [
    ("Jan", "Kowalski", "Warszawa", "Ursynów", "ul. Herbsta 4", 52.1500, 21.0300, ["Sędzia III liga (TopAmator C)", "Asystent III/IV/V liga (w tym asystenci mazowieccy)"], True, 2, 3, 4, 5),
    ("Piotr", "Nowak", "Warszawa", "Bielany", "ul. Kasprowicza 60", 52.2900, 20.9400, ["Sędzia IV liga"], True, 2, 3, 4, 5),
    ("Tomasz", "Wiśniewski", "Warszawa", "Praga-Południe", "ul. Grochowska 200", 52.2400, 21.0800, ["Sędzia klasa okręgowa"], True, 2, 3, 3, 4),
    ("Krzysztof", "Wójcik", "Warszawa", "Wola", "ul. Górczewska 30", 52.2350, 20.9700, ["Sędzia klasa A"], True, 1, 2, 3, 4),
    ("Michał", "Kamiński", "Warszawa", "Białołęka", "ul. Modlińska 150", 52.3200, 20.9750, ["Sędzia IV liga"], True, 2, 3, 4, 5),
    ("Paweł", "Lewandowski", "Piaseczno", "", "ul. Kościuszki 10", 52.0810, 21.0240, ["Sędzia klasa okręgowa"], True, 2, 3, 4, 5),
    ("Marcin", "Zieliński", "Legionowo", "", "ul. Sowińskiego 15", 52.4050, 20.9200, ["Sędzia IV liga"], True, 2, 3, 4, 5),
    ("Łukasz", "Szymański", "Pruszków", "", "ul. Kraszewskiego 20", 52.1700, 20.8000, ["Sędzia klasa A"], True, 2, 3, 4, 5),
    ("Adam", "Woźniak", "Marki", "", "al. Piłsudskiego 90", 52.3260, 21.1000, ["Sędzia klasa B"], True, 2, 2, 3, 4),
    ("Grzegorz", "Dąbrowski", "Ząbki", "", "ul. Wojska Polskiego 12", 52.2920, 21.1050, ["Sędzia klasa okręgowa"], True, 2, 3, 4, 5),
    ("Rafał", "Kozłowski", "Otwock", "", "ul. Andriollego 50", 52.1050, 21.2610, ["Sędzia klasa A"], True, 2, 3, 4, 5),
    ("Sebastian", "Jankowski", "Warszawa", "Mokotów", "ul. Puławska 100", 52.1950, 21.0200, ["Sędzia III liga (TopAmator C)", "Asystent III/IV/V liga (w tym asystenci mazowieccy)"], False, 2, 3, 4, 5),
]

# nazwisko → {dzień: None (cały dzień) | (od, do) | False (niedostępny)}; brak dnia = brak zgłoszenia
AVAILABILITY = {
    "Kowalski": {FRIDAY: ("16:00", "22:00"), SATURDAY: ("08:00", "18:00"), SUNDAY: ("12:00", "20:00"), MONDAY: False},
    "Nowak": {FRIDAY: None, SATURDAY: None, SUNDAY: ("12:00", "20:00")},
    "Wiśniewski": {SATURDAY: ("09:00", "15:00"), SUNDAY: False},
    "Wójcik": {FRIDAY: ("17:00", "22:00"), SATURDAY: None, SUNDAY: ("13:00", "19:00")},
    "Kamiński": {SATURDAY: ("10:00", "20:00"), SUNDAY: ("08:00", "14:00"), MONDAY: None},
    "Lewandowski": {FRIDAY: False, SATURDAY: None, SUNDAY: ("08:00", "16:00"), MONDAY: ("16:00", "22:00")},
    "Zieliński": {SATURDAY: None, SUNDAY: ("09:00", "13:00"), MONDAY: ("17:00", "22:00")},
    "Szymański": {FRIDAY: None, SATURDAY: False, SUNDAY: ("08:00", "17:00")},
    "Woźniak": {SATURDAY: ("12:00", "19:00"), SUNDAY: None},
    "Dąbrowski": {SATURDAY: None},
    "Kozłowski": {SATURDAY: ("08:00", "13:00"), SUNDAY: False},
    "Jankowski": {SATURDAY: None, SUNDAY: None},
}

# (external_id, dzień, start, koniec, liga, gospodarz, gość, indeks obiektu, przyjazd przed)
MATCHES = [
    ("WZPN-021", FRIDAY, "18:00", "19:45", "U19", "Polonia Warszawa", "Hutnik Warszawa", 1, 45),
    ("WZPN-022", FRIDAY, "19:00", "20:50", "Klasa A", "KS Ursus II", "Znicz III", 0, 60),
    ("WZPN-001", SATURDAY, "09:00", "10:30", "U13", "Escola Varsovia", "Polonia Warszawa", 2, 30),
    ("WZPN-002", SATURDAY, "10:00", "11:45", "U17", "Ursus Warszawa", "Znicz Pruszków", 0, 45),
    ("WZPN-003", SATURDAY, "10:30", "12:15", "U17", "Legionovia", "Hutnik Warszawa", 4, 45),
    ("WZPN-004", SATURDAY, "11:00", "12:45", "U19", "Start Otwock", "Marcovia Marki", 7, 45),
    ("WZPN-005", SATURDAY, "12:00", "13:30", "U15", "Polonia Warszawa", "Ząbkovia", 1, 30),
    ("WZPN-006", SATURDAY, "13:00", "14:45", "U17", "KS Piaseczno", "Escola Varsovia", 5, 45),
    ("WZPN-007", SATURDAY, "14:00", "15:45", "U17", "Escola Varsovia", "Ursus Warszawa", 2, 45),
    ("WZPN-008", SATURDAY, "15:00", "16:50", "Klasa A", "Hutnik II", "Marcovia II", 3, 60),
    ("WZPN-009", SATURDAY, "16:00", "17:50", "Klasa okręgowa", "Dolcan Ząbki", "Legionovia II", 9, 60),
    ("WZPN-010", SATURDAY, "17:00", "18:50", "IV liga", "Znicz II Pruszków", "KS Ursus", 6, 60),
    ("WZPN-011", SUNDAY, "08:30", "10:00", "U13", "Start Otwock", "KS Piaseczno", 7, 30),
    ("WZPN-012", SUNDAY, "10:00", "11:45", "U19", "Marcovia Marki", "Polonia Warszawa", 8, 45),
    ("WZPN-013", SUNDAY, "11:00", "12:45", "U17", "Hutnik Warszawa", "Legionovia", 3, 45),
    ("WZPN-014", SUNDAY, "12:00", "13:45", "U17", "Znicz Pruszków", "Escola Varsovia", 6, 45),
    ("WZPN-015", SUNDAY, "13:00", "14:30", "U15", "KS Piaseczno", "Ursus Warszawa", 5, 30),
    ("WZPN-016", SUNDAY, "14:00", "15:50", "Klasa A", "Polonia II", "Dolcan II", 1, 60),
    ("WZPN-017", SUNDAY, "15:00", "16:50", "Klasa okręgowa", "Ząbkovia", "Start Otwock", 9, 60),
    ("WZPN-018", SUNDAY, "16:30", "18:20", "IV liga", "Legionovia", "Znicz Pruszków", 4, 60),
    ("WZPN-019", SUNDAY, "19:00", "20:50", "Klasa B", "Start II Otwock", "Dolcan III", 7, 45),
    ("WZPN-020", SUNDAY, "19:00", "20:50", "Klasa B", "Marcovia II", "Polonia III", 8, 45),
    ("WZPN-023", MONDAY, "18:00", "19:45", "U17", "KS Piaseczno", "Ząbkovia", 5, 45),
    ("WZPN-024", MONDAY, "19:00", "20:50", "Klasa okręgowa", "Legionovia II", "Dolcan Ząbki", 4, 60),
]
