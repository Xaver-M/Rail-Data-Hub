"""
Flixbus Crawler - Price data via the public Flixbus/Flix API.

Same endpoint as the Flixtrain crawler; bus journeys are identified by
filtering out any result where all legs have operator_id == "train".
City-level IDs (flixtrain_city_id) are shared across the Flix platform
and work for bus searches too.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from datetime import datetime
import requests

from crawlers.base.base_crawler import BaseCrawler
from config.routes import Route


class FlixbusCrawler(BaseCrawler):

    OPERATOR_NAME = "flixbus"
    BASE_URL = "https://global.api.flixbus.com/search/service/v4/search"

    def __init__(self):
        super().__init__()
        self.logger.info("Flixbus Crawler (direct API, no key) ready")

    def get_url(self) -> str:
        return self.BASE_URL

    def get_params(self, route: Route, date: str) -> dict:
        origin_id = route.origin.flixtrain_city_id
        destination_id = route.destination.flixtrain_city_id

        if not origin_id:
            raise ValueError(f"No flixtrain_city_id for {route.origin.name}")
        if not destination_id:
            raise ValueError(f"No flixtrain_city_id for {route.destination.name}")

        date_obj = datetime.strptime(date, "%Y-%m-%d")
        date_formatted = date_obj.strftime("%d.%m.%Y")

        return {
            "from_city_id":   origin_id,
            "to_city_id":     destination_id,
            "departure_date": date_formatted,
            "adult":          1,
            "currency":       "EUR",
            "locale":         "de_DE",
            "search_by":      "cities",
            "products":       '{"adult":1}',
        }

    def parse(self, response: requests.Response, route: Route = None) -> list[dict]:
        records = []
        try:
            data = response.json()
        except Exception as e:
            self.logger.error(f"JSON parse error: {e}")
            return records

        trips = data.get("trips", [])
        total = 0

        for trip in trips:
            results = trip.get("results", {})
            total += len(results)
            for _, journey in results.items():
                try:
                    record = self._parse_journey(journey, route)
                    if record:
                        records.append(record)
                except Exception as e:
                    self.logger.warning(f"Parse error: {e}")
                    continue

        # Deduplicate: keep cheapest per departure time
        seen = {}
        for r in records:
            key = r["departure_time"]
            if key not in seen or (r["price_eur"] or 9999) < (seen[key]["price_eur"] or 9999):
                seen[key] = r
        records = list(seen.values())

        self.logger.info(f"{total} total connections, {len(records)} Flixbus connections")
        return records

    def _parse_journey(self, journey: dict, route: Route = None) -> dict | None:
        legs = journey.get("legs", [])

        # Exclude any journey that contains a train leg (pure train or bus+train mix)
        if any(leg.get("operator_id") == "train" for leg in legs):
            return None

        # Only direct bus connections (no transfers)
        transfer_type = journey.get("transfer_type_key", "")
        is_direct = transfer_type == "direct" or len(legs) <= 1
        if not is_direct:
            return None

        dep_str = journey.get("departure", {}).get("date")
        arr_str = journey.get("arrival", {}).get("date")
        if not dep_str or not arr_str:
            return None

        departure_time = datetime.fromisoformat(dep_str)
        arrival_time = datetime.fromisoformat(arr_str)

        price_eur = journey.get("price", {}).get("total")
        seats_available = journey.get("available", {}).get("seats")
        capacity = journey.get("remaining", {}).get("capacity")

        # Collect vehicle types across all legs
        vehicle_types = list({leg.get("means_of_transport", "bus") for leg in legs})

        return {
            "operator":        self.OPERATOR_NAME,
            "origin":          route.origin.name if route else "unknown",
            "destination":     route.destination.name if route else "unknown",
            "origin_id":       route.origin.flixtrain_city_id if route else None,
            "destination_id":  route.destination.flixtrain_city_id if route else None,
            "departure_time":  departure_time,
            "arrival_time":    arrival_time,
            "price_eur":       float(price_eur) if price_eur else None,
            "seats_available": seats_available,
            "capacity_level":  capacity,
            "transfer_type":   transfer_type,
            "is_direct":       is_direct,
            "vehicle_types":   ",".join(vehicle_types),
        }

    def fetch(self, url: str, params: dict = None, headers: dict = None) -> requests.Response:
        default_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36"
        }
        if headers:
            default_headers.update(headers)
        return super().fetch(url, params, default_headers)


# ──────────────────────────────────────────────
# DIRECT TEST
# ──────────────────────────────────────────────

if __name__ == "__main__":
    from datetime import timedelta
    from dotenv import load_dotenv
    from config.routes import get_routes_for_operator, BOOKING_HORIZONS

    load_dotenv()

    print("Flixbus Crawler Test (direct API)")
    print("=" * 50)

    crawler = FlixbusCrawler()
    routes = get_routes_for_operator("flixbus")

    print(f"{len(routes)} Flixbus routes, {len(BOOKING_HORIZONS)} horizons\n")

    for route in routes[:3]:
        for horizon in BOOKING_HORIZONS[:3]:
            date = (datetime.now() + timedelta(days=horizon)).strftime("%Y-%m-%d")
            print(f"── {route.description} | +{horizon} days ({date})")

            try:
                url = crawler.get_url()
                params = crawler.get_params(route, date)
                response = crawler.fetch(url, params)
                records = crawler.parse(response, route)
                valid = crawler.validate(records)

                if valid:
                    print(f"   {len(valid)} connections:")
                    for r in valid[:3]:
                        seats = r.get("seats_available")
                        seats_str = str(seats) if seats is not None else "-"
                        direct = "direct" if r.get("is_direct") else r.get("transfer_type", "?")
                        print(
                            f"   {r['departure_time'].strftime('%H:%M')} → "
                            f"{r['arrival_time'].strftime('%H:%M')} | "
                            f"{r['price_eur']:.2f} EUR | "
                            f"{seats_str} seats | "
                            f"{direct} | "
                            f"vehicles: {r.get('vehicle_types', '?')}"
                        )
                    if len(valid) > 3:
                        print(f"   ... and {len(valid) - 3} more")
                else:
                    print("   No Flixbus connections found")

            except Exception as e:
                print(f"   ERROR: {e}")

            print()
