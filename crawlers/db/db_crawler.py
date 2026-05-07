"""
DB Crawler — Price data via local db-vendo-client microservice.

Prerequisite: Node.js microservice must be running:
    cd crawlers/db/microservice
    node server.mjs

No API key required. Uses the DB Navigator API (dbnav profile).
Saves direct and connecting journeys as separate records.
Load factor data (loadFactor) not available — API limitation of DB.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from datetime import datetime
import requests

from crawlers.base.base_crawler import BaseCrawler
from config.routes import Route


class DBCrawler(BaseCrawler):

    OPERATOR_NAME = "db"
    MICROSERVICE_URL = "http://localhost:3123"

    def __init__(self):
        super().__init__()
        self.logger.info("DB Crawler (db-vendo-client microservice) ready")

    def get_url(self) -> str:
        return f"{self.MICROSERVICE_URL}/journeys"

    def get_params(self, route: Route, date: str) -> dict:
        from_id = route.origin.db_id
        to_id   = route.destination.db_id

        if not from_id:
            raise ValueError(f"No db_id for {route.origin.name}")
        if not to_id:
            raise ValueError(f"No db_id for {route.destination.name}")

        date_obj  = datetime.strptime(date, "%Y-%m-%d")
        departure = date_obj.replace(hour=10, minute=0).isoformat()

        return {
            "from":            from_id,
            "to":              to_id,
            "departure":       departure,
            "results":         10,
            "tickets":         "true",
            "nationalExpress": "true",
            "national":        "true",
            "regionalExpress": "false",
            "regional":        "false",
            "suburban":        "false",
            "bus":             "false",
            "ferry":           "false",
            "subway":          "false",
            "tram":            "false",
            "taxi":            "false",
        }

    def parse(self, response: requests.Response, route: Route = None) -> list[dict]:
        records = []
        try:
            data = response.json()
        except Exception as e:
            self.logger.error(f"JSON parse error: {e}")
            return records

        journeys = data.get("journeys", [])

        for journey in journeys:
            legs = journey.get("legs", [])
            if not legs:
                continue

            dep_str = legs[0].get("departure")
            arr_str = legs[-1].get("arrival")

            try:
                departure_time = datetime.fromisoformat(dep_str) if dep_str else None
                arrival_time   = datetime.fromisoformat(arr_str) if arr_str else None
            except (ValueError, TypeError):
                continue

            train_number = self._extract_train_name(legs)
            is_direct    = len(legs) == 1
            prices       = self._extract_prices(journey)

            if not prices:
                continue

            for pr in prices:
                records.append({
                    "operator":        self.OPERATOR_NAME,
                    "origin":          route.origin.name if route else "",
                    "destination":     route.destination.name if route else "",
                    "origin_id":       route.origin.db_id if route else None,
                    "destination_id":  route.destination.db_id if route else None,
                    "departure_time":  departure_time,
                    "arrival_time":    arrival_time,
                    "price_eur":       pr["price_eur"],
                    "travel_class":    pr["travel_class"],
                    "seats_available": pr["seats_available"],
                    "train_number":    train_number,
                    "is_direct":       is_direct,
                })

        self.logger.info(f"{len(journeys)} journeys, {len(records)} records")
        return records

    def _extract_train_name(self, legs: list) -> str:
        names = []
        for leg in legs:
            name = (leg.get("line") or {}).get("name")
            if name:
                names.append(name)
        return " + ".join(names) if names else "?"

    def _extract_prices(self, journey: dict) -> list[dict]:
        """
        Extracts prices. Note for dbnav API:
        priceObj.amount is in cents (6999 → 69.99 EUR)
        """
        tickets    = journey.get("tickets", [])
        agg        = (journey.get("price") or {})
        agg_amount = agg.get("amount")
        results    = []

        if tickets:
            for ticket in tickets:
                price_obj = ticket.get("priceObj") or ticket.get("price") or {}
                raw       = price_obj.get("amount")
                if raw is not None:
                    price_eur = round(raw / 100, 2) if (isinstance(raw, int) and raw > 500) else float(raw)
                else:
                    price_eur = float(agg_amount) if agg_amount is not None else None

                if price_eur is None:
                    continue

                results.append({
                    "price_eur":       price_eur,
                    "travel_class":    self._infer_class(ticket.get("name", "")),
                    "seats_available": ticket.get("seatsAvailable"),
                })

        elif agg_amount is not None:
            results.append({
                "price_eur":       float(agg_amount),
                "travel_class":    "2",
                "seats_available": None,
            })

        return results

    def _infer_class(self, name: str) -> str:
        n = (name or "").lower()
        return "1" if any(x in n for x in ["1st class", "first", "class 1", "1st", "1. klasse", "klasse 1"]) else "2"

    def fetch(self, url: str, params: dict = None, headers: dict = None) -> requests.Response:
        headers = {**(headers or {}), "Origin": self.MICROSERVICE_URL}
        return super().fetch(url, params, headers)


# ──────────────────────────────────────────────
# DIRECT TEST
# ──────────────────────────────────────────────

if __name__ == "__main__":
    from datetime import timedelta
    from dotenv import load_dotenv
    from config.routes import get_routes_for_operator, BOOKING_HORIZONS

    load_dotenv()

    print("DB Crawler Test (db-vendo-client microservice)")
    print("=" * 50)

    try:
        requests.get("http://localhost:3123/", timeout=3)
    except requests.exceptions.ConnectionError:
        print("❌ Microservice not reachable!")
        print("   cd crawlers/db/microservice && node server.mjs")
        sys.exit(1)

    crawler = DBCrawler()
    routes  = get_routes_for_operator("db")

    print(f"{len(routes)} DB routes, {len(BOOKING_HORIZONS)} horizons\n")

    for route in routes[:2]:
        for horizon in BOOKING_HORIZONS[:3]:
            date = (datetime.now() + timedelta(days=horizon)).strftime("%Y-%m-%d")
            print(f"── {route.description} | +{horizon} days ({date})")

            try:
                url      = crawler.get_url()
                params   = crawler.get_params(route, date)
                response = crawler.fetch(url, params)
                records  = crawler.parse(response, route)
                valid    = crawler.validate(records)

                if valid:
                    direct = sum(1 for r in valid if r.get("is_direct"))
                    print(f"   {len(valid)} records ({direct} direct, {len(valid)-direct} with transfer):")
                    for r in valid[:3]:
                        print(
                            f"   {r['departure_time'].strftime('%H:%M')} → "
                            f"{r['arrival_time'].strftime('%H:%M')} | "
                            f"{r['price_eur']:.2f} EUR | "
                            f"{r['train_number']} | "
                            f"{'direct' if r['is_direct'] else 'transfer'}"
                        )
                    if len(valid) > 3:
                        print(f"   ... and {len(valid) - 3} more")
                else:
                    print("   No connections found")

            except Exception as e:
                print(f"   ERROR: {e}")

            print()