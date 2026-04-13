"""
Flixtrain Crawler - Preisdaten über die FlixBus RapidAPI


Setzt folgende .env Variablen voraus:
    RAPIDAPI_KEY=_derKeyHier <- Platzhalter
    RAPIDAPI_HOST=flixbus2.p.rapidapi.com

Wichtig: Basic Plan = 100 Requests/Monat kostenlos.
Nur für relevante Routen crawlen!
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import os
import re
from datetime import datetime
import requests

from crawlers.base.base_crawler import BaseCrawler


class FlixtrainCrawler(BaseCrawler):
    """
    Crawler für Flixtrain (FlixMobility) über die RapidAPI.

    Gibt sowohl Bus- als auch Zugverbindungen zurück.
    Der Crawler filtert automatisch nur Zugverbindungen heraus
    (product_type == "train").

    Bekannte Flixtrain-Strecken in Deutschland:
    - Berlin - Hamburg
    - Berlin - Köln
    - Berlin - Stuttgart
    - Hamburg - Köln
    - Hamburg - Stuttgart

    Beispielaufruf:
        crawler = FlixtrainCrawler()
        crawler.run([
            ("Berlin", "Hamburg", "2026-04-20"),
            ("Berlin", "Köln", "2026-04-20"),
        ])
    """

    OPERATOR_NAME = "Flixtrain"

    # RapidAPI Endpunkt
    BASE_URL = "https://flixbus2.p.rapidapi.com/trips"
    AUTOCOMPLETE_URL = "https://flixbus2.p.rapidapi.com/v1/cities/autocomplete"

    # Stadt-IDs (aus der Autocomplete API – city.id Feld)
    # Format: UUID von der FlixBus API
    CITY_IDS = {
        "Berlin":       "40d8f682-8646-11e6-9066-549f350fcb0c",
        "Hamburg":      "40d91e53-8646-11e6-9066-549f350fcb0c",
        "München":      "40d8ea30-8646-11e6-9066-549f350fcb0c",
        "Köln":         "40d8f4f4-8646-11e6-9066-549f350fcb0c",
        "Stuttgart":    "40d8ff46-8646-11e6-9066-549f350fcb0c",
        "Frankfurt":    "40d8f1ca-8646-11e6-9066-549f350fcb0c",
        "Düsseldorf":   "40d8f3ac-8646-11e6-9066-549f350fcb0c",
        "Hannover":     "40d90408-8646-11e6-9066-549f350fcb0c",
        "Bremen":       "40d8f8c4-8646-11e6-9066-549f350fcb0c",
        "Leipzig":      "40d8f682-8646-11e6-9066-549f350fcb0c",
    }

    def __init__(self):
        super().__init__()
        self.api_key = os.getenv("RAPIDAPI_KEY")
        self.api_host = os.getenv("RAPIDAPI_HOST", "flixbus2.p.rapidapi.com")

        if not self.api_key:
            raise ValueError(
                "Kein RAPIDAPI_KEY in .env gefunden!\n"
                "Bitte auf https://rapidapi.com/flixbus registrieren "
                "und RAPIDAPI_KEY in .env eintragen."
            )

        self.logger.info("Flixtrain Crawler (RapidAPI) bereit")

    # ──────────────────────────────────────────────
    # ABSTRAKTE METHODEN – Implementierung
    # ──────────────────────────────────────────────

    def get_url(self) -> str:
        return self.BASE_URL

    def get_params(self, origin: str, destination: str, date: str) -> dict:
        """
        Erstellt Query-Parameter für die RapidAPI FlixBus Suche.

        Args:
            origin: Abfahrtsstadt (z.B. "Berlin")
            destination: Zielstadt (z.B. "Hamburg")
            date: Datum im Format YYYY-MM-DD

        Returns:
            Dict mit API-Parametern
        """
        origin_id = self.CITY_IDS.get(origin)
        destination_id = self.CITY_IDS.get(destination)

        if not origin_id:
            raise ValueError(
                f"Unbekannte Stadt: {origin}. "
                f"Bekannte Städte: {list(self.CITY_IDS.keys())}"
            )
        if not destination_id:
            raise ValueError(
                f"Unbekannte Stadt: {destination}. "
                f"Bekannte Städte: {list(self.CITY_IDS.keys())}"
            )

        # Datum umwandeln: YYYY-MM-DD → DD.MM.YYYY
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        date_formatted = date_obj.strftime("%d.%m.%Y")

        return {
            "from_id":    origin_id,
            "to_id":      destination_id,
            "date":       date_formatted,
            "adult":      1,
            "children":   0,
            "bikes":      0,
            "currency":   "EUR",
            "locale":     "de_DE",
            "search_by":  "cities",
        }

    def parse(self, response: requests.Response) -> list[dict]:
        """
        Verarbeitet die RapidAPI Antwort und extrahiert nur Zugverbindungen.

        Die API gibt eine Liste von journeys zurück.
        Jede Journey hat segments mit product_type ("bus" oder "train").
        Wir filtern nur Verbindungen mit product_type == "train" heraus.

        Args:
            response: HTTP Response von der RapidAPI

        Returns:
            Liste von Datensätzen im einheitlichen Format
        """
        records = []

        try:
            data = response.json()
        except Exception as e:
            self.logger.error(f"JSON Parse Fehler: {e}")
            return records

        journeys = data.get("journeys", [])
        self.logger.info(f"{len(journeys)} Verbindungen in API-Antwort (Bus + Zug)")

        for journey in journeys:
            try:
                record = self._parse_journey(journey)
                if record:
                    records.append(record)
            except Exception as e:
                self.logger.warning(f"Fehler beim Parsen einer Verbindung: {e}")
                continue

        self.logger.info(f"{len(records)} Zugverbindungen nach Filterung")
        return records

    def _parse_journey(self, journey: dict) -> dict | None:
        """
        Parst eine einzelne Verbindung - gibt None zurück wenn es ein Bus ist.

        Args:
            journey: Ein einzelnes Journey-Objekt aus der API

        Returns:
            Datensatz im einheitlichen Format oder None

        Hinweis zur Sitzverfügbarkeit:
            Die RapidAPI liefert Sitzinformationen nur über das Textfeld
            additional_info in den fares (z.B. "1 seat left at this price").
            Dieses Feld ist nur befüllt wenn wenige Plätze verbleiben (~1-9).
            Bei normaler Verfügbarkeit ist es leer → seats_available bleibt None.
            Eine exakte Sitzanzahl wie bei Trenitalia (availableAmount) ist
            über diese API nicht verfügbar. Dies ist in der Analyse entsprechend
            als Limitation zu dokumentieren.
        """
        # Nur Züge – Busse herausfiltern
        segments = journey.get("segments", [])
        is_train = any(
            seg.get("product_type") == "train"
            for seg in segments
        )

        if not is_train:
            return None

        # Abfahrts- und Ankunftszeit
        departure_str = journey.get("dep_offset")
        arrival_str = journey.get("arr_offset")

        if not departure_str or not arrival_str:
            return None

        departure_time = datetime.fromisoformat(departure_str)
        arrival_time = datetime.fromisoformat(arrival_str)

        # Preis + Sitzverfügbarkeit aus fares
        fares = journey.get("fares", [])
        price_eur = None
        seats_available = None
        availability_level = None  # "low" | "normal" | "sold_out" | None

        if fares:
            first_fare = fares[0]
            price_eur = first_fare.get("price")

            additional_info = first_fare.get("additional_info", "") or ""

            if additional_info:
                info_lower = additional_info.lower()

                if "sold out" in info_lower:
                    seats_available = 0
                    availability_level = "sold_out"

                else:
                    # Muster: "1 seat left at this price" / "3 seats left"
                    match = re.search(r"(\d+)\s+seat", info_lower)
                    if match:
                        seats_available = int(match.group(1))
                        # Unter 5 Sitze = knappes Angebot
                        availability_level = "low" if seats_available <= 5 else "normal"
            else:
                # Kein additional_info = normale Verfügbarkeit
                availability_level = "normal"

        return {
            "operator":           self.OPERATOR_NAME,
            "origin":             journey.get("dep_name"),
            "destination":        journey.get("arr_name"),
            "departure_time":     departure_time,
            "arrival_time":       arrival_time,
            "price_eur":          float(price_eur) if price_eur else None,
            "travel_class":       "2",
            "seats_available":    seats_available,    # int oder None
            "availability_level": availability_level, # "low"/"normal"/"sold_out"/None
            "currency":           "EUR",
        }

    # ──────────────────────────────────────────────
    # HTTP OVERRIDE – RapidAPI Headers
    # ──────────────────────────────────────────────

    def fetch(self, url: str, params: dict = None, headers: dict = None) -> requests.Response:
        """
        Überschreibt fetch() um RapidAPI-spezifische Headers hinzuzufügen.
        """
        rapidapi_headers = {
            "x-rapidapi-key":  self.api_key,
            "x-rapidapi-host": self.api_host,
        }

        if headers:
            rapidapi_headers.update(headers)

        return super().fetch(url, params, rapidapi_headers)


# ──────────────────────────────────────────────
# DIREKTER TEST
# ──────────────────────────────────────────────

if __name__ == "__main__":
    """
    Schnelltest ohne Datenbankverbindung.

    Aufruf: py -m crawlers.flixtrain.flixtrain_crawler
    Voraussetzung: RAPIDAPI_KEY in .env eingetragen
    """
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

    from dotenv import load_dotenv
    load_dotenv()

    print("Flixtrain Crawler Test (RapidAPI)")
    print("=" * 40)

    try:
        crawler = FlixtrainCrawler()
    except ValueError as e:
        print(f"FEHLER: {e}")
        sys.exit(1)

    url = crawler.get_url()
    params = crawler.get_params("Berlin", "Hamburg", "2026-04-20")

    print(f"URL: {url}")
    print(f"Von: Berlin -> Hamburg | Datum: 20.04.2026")
    print()

    try:
        response = crawler.fetch(url, params)
        records = crawler.parse(response)
        valid = crawler.validate(records)

        if valid:
            print(f"OK – {len(valid)} Flixtrain-Verbindungen gefunden:")
            print()
            print(f"  {'Abfahrt':<8} {'Ankunft':<8} {'Preis':<10} {'Verfuegb.':<14} {'Plaetze':<8} Route")
            print("  " + "-" * 74)

            for r in valid:
                avail = r.get("availability_level") or "unknown"
                seats = r.get("seats_available")
                seats_str = str(seats) if seats is not None else "-"
                avail_label = {
                    "low":      "[LOW]",
                    "normal":   "[OK]",
                    "sold_out": "[AUSVERKAUFT]",
                }.get(avail, "[?]")

                print(
                    f"  {r['departure_time'].strftime('%H:%M'):<8}"
                    f"{r['arrival_time'].strftime('%H:%M'):<8}"
                    f"{r['price_eur']:.2f} EUR  "
                    f"{avail_label:<14}"
                    f"{seats_str:<8}  "
                    f"{r['origin']} -> {r['destination']}"
                )
        else:
            print("WARNUNG: Keine Flixtrain-Zugverbindungen gefunden.")
            print("Moeglicherweise faehrt Flixtrain an diesem Tag nicht.")

    except Exception as e:
        print(f"FEHLER: {e}")
