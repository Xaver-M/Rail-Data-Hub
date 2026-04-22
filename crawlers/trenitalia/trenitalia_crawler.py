"""
Trenitalia Crawler - Preisdaten über die lefrecce.it BFF API

Kein API-Key erforderlich, kein Request-Limit.
Gibt Preise und Sitzverfügbarkeit für Frecciarossa/Frecciargento zurück.
Preis, Sitzzahl und Tarifinfo stammen immer aus demselben günstigsten Tarif.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import time
from datetime import datetime
import requests

from crawlers.base.base_crawler import BaseCrawler
from config.routes import Route


class TrenitaliaCrawler(BaseCrawler):

    OPERATOR_NAME = "trenitalia"
    BASE_URL = "https://www.lefrecce.it/Channels.Website.BFF.WEB/website/ticket/solutions"

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    def __init__(self):
        super().__init__()
        self.logger.info("Trenitalia Crawler (lefrecce.it BFF) bereit")

    def get_url(self) -> str:
        return self.BASE_URL

    def get_params(self, route: Route, date: str) -> dict:
        origin_id = route.origin.trenitalia_id
        destination_id = route.destination.trenitalia_id

        if not origin_id:
            raise ValueError(f"Keine trenitalia_id für {route.origin.name}")
        if not destination_id:
            raise ValueError(f"Keine trenitalia_id für {route.destination.name}")

        date_obj = datetime.strptime(date, "%Y-%m-%d")
        departure_time = date_obj.strftime("%Y-%m-%dT06:00:00.000+01:00")

        return {
            "departureLocationId": origin_id,
            "arrivalLocationId": destination_id,
            "departureTime": departure_time,
            "adults": 1,
            "children": 0,
            "criteria": {
                "frecceOnly": False,
                "regionalOnly": False,
                "noChanges": True,
                "order": "DEPARTURE_DATE",
                "limit": 10,
                "offset": 0
            },
            "advancedSearchRequest": {
                "bestFare": False
            }
        }

    def fetch(self, url: str, params: dict = None, headers: dict = None) -> requests.Response:
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                self.logger.info(f"HTTP POST {url} (Versuch {attempt}/{self.MAX_RETRIES})")
                response = self.session.post(
                    url,
                    json=params,
                    headers=self.HEADERS,
                    timeout=self.REQUEST_TIMEOUT,
                )
                response.raise_for_status()
                self.logger.info(f"HTTP {response.status_code} – {len(response.content)} Bytes")
                return response

            except requests.exceptions.Timeout:
                self.logger.warning(f"Timeout bei Versuch {attempt}")
            except requests.exceptions.HTTPError as e:
                self.logger.warning(f"HTTP Fehler {e.response.status_code} bei Versuch {attempt}")
                if e.response.status_code in (400, 404):
                    raise
            except requests.exceptions.ConnectionError:
                self.logger.warning(f"Verbindungsfehler bei Versuch {attempt}")
            except Exception as e:
                self.logger.warning(f"Unbekannter Fehler bei Versuch {attempt}: {e}")

            if attempt < self.MAX_RETRIES:
                time.sleep(self.RETRY_DELAY)

        raise Exception(f"Alle {self.MAX_RETRIES} Versuche für {url} fehlgeschlagen")

    def parse(self, response: requests.Response, route: Route = None) -> list[dict]:
        records = []
        try:
            data = response.json()
        except Exception as e:
            self.logger.error(f"JSON Parse Fehler: {e}")
            return records

        solutions = data.get("solutions", [])
        self.logger.info(f"{len(solutions)} Verbindungen in API-Antwort")

        for item in solutions:
            try:
                record = self._parse_solution(item, route)
                if record:
                    records.append(record)
            except Exception as e:
                self.logger.warning(f"Fehler beim Parsen: {e}")
                continue

        self.logger.info(f"{len(records)} Trenitalia-Verbindungen geparst")
        return records

    def _parse_solution(self, item: dict, route: Route = None) -> dict | None:
        sol = item.get("solution")
        if sol is None:
            return None

        if sol.get("status", "") == "SOLD_OUT":
            return None

        dep_str = sol.get("departureTime", "")
        arr_str = sol.get("arrivalTime", "")
        if not dep_str or not arr_str:
            return None

        departure_time = datetime.fromisoformat(dep_str)
        arrival_time = datetime.fromisoformat(arr_str)

        # Zugnummer
        nodes = sol.get("nodes", [])
        train_number = None
        if nodes:
            train = nodes[0].get("train", {})
            category = train.get("trainCategory", "")
            name = train.get("name", "")
            train_number = f"{category} {name}".strip() if category or name else None

        # Günstigsten Tarif finden — Preis, Sitzzahl und Tarifinfo aus derselben Quelle
        cheapest_price = None
        cheapest_seats = None
        cheapest_fare_class = None
        cheapest_service_name = None

        for grid in item.get("grids", []):
            for service in grid.get("services", []):
                for offer in service.get("offers", []):
                    avail = offer.get("availableAmount")
                    price_data = offer.get("price")
                    if price_data is None:
                        continue
                    price = price_data.get("amount")
                    if price is not None and avail is not None and avail != 32767:
                        if cheapest_price is None or price < cheapest_price:
                            cheapest_price = price
                            cheapest_seats = avail
                            cheapest_fare_class = offer.get("name")
                            cheapest_service_name = offer.get("serviceName")

        # Fallback: Preis aus solution-Ebene falls grids leer
        if cheapest_price is None:
            price_obj = sol.get("price", {})
            cheapest_price = price_obj.get("amount") if price_obj else None

        return {
            "operator":         self.OPERATOR_NAME,
            "origin":           route.origin.name if route else "unknown",
            "destination":      route.destination.name if route else "unknown",
            "origin_id":        str(route.origin.trenitalia_id) if route else None,
            "destination_id":   str(route.destination.trenitalia_id) if route else None,
            "departure_time":   departure_time,
            "arrival_time":     arrival_time,
            "price_eur":        float(cheapest_price) if cheapest_price else None,
            "seats_available":  cheapest_seats,
            "fare_class":       cheapest_fare_class,
            "offer_type":       cheapest_service_name,
            "train_number":     train_number,
        }


# ──────────────────────────────────────────────
# DIREKTER TEST
# ──────────────────────────────────────────────

if __name__ == "__main__":
    from datetime import timedelta
    from dotenv import load_dotenv
    from config.routes import get_routes_for_operator, BOOKING_HORIZONS

    load_dotenv()

    print("Trenitalia Crawler Test")
    print("=" * 50)

    crawler = TrenitaliaCrawler()
    routes = get_routes_for_operator("trenitalia")

    print(f"{len(routes)} Trenitalia-Routen, {len(BOOKING_HORIZONS)} Horizonte\n")

    for route in routes[:1]:
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
                    print(f"   {len(valid)} Züge gefunden:")
                    for r in valid[:3]:
                        seats = r.get("seats_available")
                        seats_str = str(seats) if seats is not None else "-"
                        train = r.get("train_number") or "-"
                        fare = r.get("fare_class") or "-"
                        offer = r.get("offer_type") or "-"
                        print(
                            f"   {r['departure_time'].strftime('%H:%M')} -> "
                            f"{r['arrival_time'].strftime('%H:%M')} | "
                            f"{r['price_eur']:.2f} EUR | "
                            f"{seats_str} Plaetze | "
                            f"{fare} / {offer} | "
                            f"{train}"
                        )
                    if len(valid) > 3:
                        print(f"   ... und {len(valid) - 3} weitere")
                else:
                    print(f"   Keine Verbindungen gefunden")

            except Exception as e:
                print(f"   FEHLER: {e}")

            print()