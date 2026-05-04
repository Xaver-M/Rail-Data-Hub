"""
RegioJet Crawler – Preis- und Kapazitätsdaten über die öffentliche RegioJet REST-API

Kein API-Key erforderlich.
Endpunkt: https://brn-ybus-pubapi.sa.cz/restapi/routes/search/simple

Jede Route liefert priceFrom/priceTo sowie freeSeatsCount pro Verbindung.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from datetime import datetime
import requests

from crawlers.base.base_crawler import BaseCrawler
from config.routes import Route


class RegioJetCrawler(BaseCrawler):

    OPERATOR_NAME = "regiojet"
    BASE_URL = "https://brn-ybus-pubapi.sa.cz/restapi/routes/search/simple"

    def __init__(self):
        super().__init__()
        self.logger.info("RegioJet Crawler (öffentliche REST-API, kein Key) bereit")

    def get_url(self) -> str:
        return self.BASE_URL

    def get_params(self, route: Route, date: str) -> dict:
        origin = route.origin
        destination = route.destination

        if origin.regiojet_city_id:
            from_id, from_type = origin.regiojet_city_id, "CITY"
        elif origin.regiojet_station_id:
            from_id, from_type = origin.regiojet_station_id, "STATION"
        else:
            raise ValueError(f"Keine RegioJet-ID für {origin.name}")

        if destination.regiojet_city_id:
            to_id, to_type = destination.regiojet_city_id, "CITY"
        elif destination.regiojet_station_id:
            to_id, to_type = destination.regiojet_station_id, "STATION"
        else:
            raise ValueError(f"Keine RegioJet-ID für {destination.name}")

        return {
            "tariffs":         "REGULAR",
            "fromLocationType": from_type,
            "fromLocationId":   from_id,
            "toLocationType":   to_type,
            "toLocationId":     to_id,
            "departureDate":    date,
        }

    def parse(self, response: requests.Response, route: Route = None) -> list[dict]:
        records = []
        try:
            data = response.json()
        except Exception as e:
            self.logger.error(f"JSON Parse Fehler: {e}")
            return records

        routes_raw = data.get("routes", [])
        self.logger.info(f"{len(routes_raw)} Verbindungen empfangen")

        for entry in routes_raw:
            try:
                record = self._parse_route(entry, route)
                if record:
                    records.append(record)
            except Exception as e:
                self.logger.warning(f"Fehler beim Parsen: {e}")
                continue

        return records

    def _parse_route(self, entry: dict, route: Route = None) -> dict | None:
        if not entry.get("bookable", True):
            return None

        dep_str = entry.get("departureTime")
        arr_str = entry.get("arrivalTime")
        if not dep_str or not arr_str:
            return None

        departure_time = datetime.fromisoformat(dep_str)
        arrival_time   = datetime.fromisoformat(arr_str)

        price_from = entry.get("priceFrom")
        if price_from is None:
            return None

        vehicle_types   = entry.get("vehicleTypes", [])
        transfers_count = entry.get("transfersCount", 0)
        free_seats      = entry.get("freeSeatsCount")
        vehicle_class   = entry.get("vehicleStandardKey")  # z.B. "YELLOW", "RED"
        action_price    = entry.get("actionPrice", False)

        # Kapazitätsstufe aus freien Plätzen ableiten
        if free_seats is not None:
            if free_seats == 0:
                capacity_level = "sold_out"
            elif free_seats <= 5:
                capacity_level = "low"
            elif free_seats <= 20:
                capacity_level = "medium"
            else:
                capacity_level = "high"
        else:
            capacity_level = None

        return {
            "operator":        self.OPERATOR_NAME,
            "origin":          route.origin.name if route else "unknown",
            "destination":     route.destination.name if route else "unknown",
            "origin_id":       str(entry.get("departureStationId", "")),
            "destination_id":  str(entry.get("arrivalStationId", "")),
            "departure_time":  departure_time,
            "arrival_time":    arrival_time,
            "price_eur":       float(price_from),
            "price_eur_max":   float(entry.get("priceTo", price_from)),
            "seats_available": free_seats,
            "capacity_level":  capacity_level,
            "travel_class":    vehicle_class,
            "is_direct":       transfers_count == 0,
            "vehicle_types":   ",".join(vehicle_types),
            "action_price":    action_price,
            "transfers_count": transfers_count,
        }

    def fetch(self, url: str, params: dict = None, headers: dict = None) -> requests.Response:
        default_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
        }
        if headers:
            default_headers.update(headers)
        return super().fetch(url, params, default_headers)


# ──────────────────────────────────────────────
# DIREKTER TEST
# ──────────────────────────────────────────────

if __name__ == "__main__":
    from datetime import timedelta
    from dotenv import load_dotenv
    from config.routes import get_routes_for_operator, BOOKING_HORIZONS

    load_dotenv()

    print("RegioJet Crawler Test")
    print("=" * 50)

    crawler = RegioJetCrawler()
    routes = get_routes_for_operator("regiojet")

    print(f"{len(routes)} RegioJet-Routen, {len(BOOKING_HORIZONS)} Horizonte\n")

    for route in routes[:2]:
        for horizon in BOOKING_HORIZONS[:3]:
            date = (datetime.now() + timedelta(days=horizon)).strftime("%Y-%m-%d")
            print(f"── {route.description} | +{horizon} Tage ({date})")

            try:
                url = crawler.get_url()
                params = crawler.get_params(route, date)
                response = crawler.fetch(url, params)
                records = crawler.parse(response, route)
                valid = crawler.validate(records)

                if valid:
                    print(f"   {len(valid)} Verbindungen:")
                    for r in valid[:3]:
                        seats = r.get("seats_available")
                        seats_str = str(seats) if seats is not None else "-"
                        direct = "direkt" if r.get("is_direct") else f"{r.get('transfers_count', '?')} Umstiege"
                        print(
                            f"   {r['departure_time'].strftime('%H:%M')} → "
                            f"{r['arrival_time'].strftime('%H:%M')} | "
                            f"ab {r['price_eur']:.2f} EUR | "
                            f"{seats_str} Plätze | "
                            f"{direct} | "
                            f"Klasse: {r.get('travel_class', '?')}"
                        )
                    if len(valid) > 3:
                        print(f"   ... und {len(valid) - 3} weitere")
                else:
                    print("   Keine buchbaren Verbindungen gefunden")

            except Exception as e:
                print(f"   FEHLER: {e}")

            print()
