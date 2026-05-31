"""
Trenitalia Crawler - Price data via the lefrecce.it BFF API.

No API key required, no rate limit.
Returns prices and seat availability for Frecciarossa/Frecciargento.
Price, seat count and fare info always come from the same cheapest offer.
Paginates through all solutions of a given day (limit=10, offset increments).
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import time
from datetime import datetime, timedelta, timezone
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
        self.logger.info("Trenitalia Crawler (lefrecce.it BFF) ready")

    def get_url(self) -> str:
        return self.BASE_URL

    def get_params(self, route: Route, date: str, offset: int = 0) -> dict:
        origin_id = route.origin.trenitalia_id
        destination_id = route.destination.trenitalia_id
        if not origin_id:
            raise ValueError(f"No trenitalia_id for {route.origin.name}")
        if not destination_id:
            raise ValueError(f"No trenitalia_id for {route.destination.name}")
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        departure_time = date_obj.strftime("%Y-%m-%dT05:00:00.000+01:00")
        return {
            "departureLocationId": origin_id,
            "arrivalLocationId": destination_id,
            "departureTime": departure_time,
            "adults": 1,
            "children": 0,
            "criteria": {
                "frecceOnly": False,
                "regionalOnly": False,
                "intercityOnly": False,
                "tourismOnly": False,
                "noChanges": True,
                "order": "DEPARTURE_DATE",
                "limit": 10,
                "offset": offset,
            },
            "advancedSearchRequest": {"bestFare": False, "bikeFilter": False, "forwardDiscountCodes": []}
        }

    def fetch(self, url: str, params: dict = None, headers: dict = None) -> requests.Response:
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                self.logger.info(f"HTTP POST {url} (attempt {attempt}/{self.MAX_RETRIES})")
                response = self.session.post(
                    url,
                    json=params,
                    headers=self.HEADERS,
                    timeout=self.REQUEST_TIMEOUT,
                )
                response.raise_for_status()
                self.logger.info(f"HTTP {response.status_code} – {len(response.content)} bytes")
                return response
            except requests.exceptions.Timeout:
                self.logger.warning(f"Timeout on attempt {attempt}")
            except requests.exceptions.HTTPError as e:
                self.logger.warning(f"HTTP error {e.response.status_code} on attempt {attempt}")
                if e.response.status_code in (400, 404):
                    raise
            except requests.exceptions.ConnectionError:
                self.logger.warning(f"Connection error on attempt {attempt}")
            except Exception as e:
                self.logger.warning(f"Unknown error on attempt {attempt}: {e}")
            if attempt < self.MAX_RETRIES:
                time.sleep(self.RETRY_DELAY)
        raise Exception(f"All {self.MAX_RETRIES} attempts failed for {url}")

    def _fetch_all_solutions(self, url: str, route: Route, date: str) -> list:
        all_solutions = []
        offset = 0
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
        while True:
            params = self.get_params(route, date, offset=offset)
            response = self.fetch(url, params)
            solutions = response.json().get("solutions", [])
            if not solutions:
                break
            reached_next_day = False
            for s in solutions:
                dep_str = s.get("solution", {}).get("departureTime", "")
                if not dep_str:
                    continue
                dep_date = datetime.fromisoformat(dep_str).date()
                if dep_date == target_date:
                    all_solutions.append(s)
                elif dep_date > target_date:
                    reached_next_day = True
            if reached_next_day:
                break
            offset += 10
        self.logger.info(f"Pagination complete: {len(all_solutions)} solutions for {date}")
        return all_solutions


    def _parse_solutions(self, solutions: list, route: Route) -> list[dict]:
        records = []
        for item in solutions:
            try:
                record = self._parse_solution(item, route)
                if record:
                    records.append(record)
            except Exception as e:
                self.logger.warning(f"Parse error: {e}")
        self.logger.info(f"{len(records)} Trenitalia connections parsed")
        return records

    def parse(self, response: requests.Response, route=None) -> list[dict]:
        try:
            data = response.json()
        except Exception as e:
            self.logger.error(f"JSON parse error: {e}")
            return []
        solutions = data.get("solutions", [])
        self.logger.info(f"{len(solutions)} connections in API response")
        return self._parse_solutions(solutions, route)

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

        nodes = sol.get("nodes", [])
        train_number = None
        if nodes:
            train = nodes[0].get("train", {})
            category = train.get("trainCategory", "")
            name = train.get("name", "")
            train_number = f"{category} {name}".strip() if category or name else None

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

    def run(self, routes: list, horizons: list[int]):
        self.logger.info(f"Crawler started – {len(routes)} routes, {len(horizons)} horizons")
        start_time = datetime.now(timezone.utc)
        total_saved = 0
        errors = 0
        try:
            self._connect_db()
            for route in routes:
                if self.OPERATOR_NAME not in route.operators:
                    continue
                for horizon in horizons:
                    date = (datetime.now() + timedelta(days=horizon)).strftime("%Y-%m-%d")
                    try:
                        url = self.get_url()
                        solutions = self._fetch_all_solutions(url, route, date)
                        records = self._parse_solutions(solutions, route)
                        for r in records:
                            r["booking_horizon_days"] = horizon
                            r["route_id"] = route.route_id
                        valid_records = self.validate(records)
                        saved = self.save(valid_records)
                        total_saved += saved
                        self.logger.info(f"{route.description} +{horizon}d: {saved} saved")
                    except Exception as e:
                        errors += 1
                        self.logger.error(f"Error on {route.description} +{horizon}d: {e}")
                        continue
            self.log_run("success" if errors == 0 else "partial_error", total_saved)
        except Exception as e:
            self.logger.error(f"Critical error: {e}")
            self.log_run("error", total_saved, str(e))
            raise
        finally:
            self._close_db()
        duration = (datetime.now(timezone.utc) - start_time).seconds
        self.logger.info(f"Crawler finished – {total_saved} records saved, {errors} errors, {duration}s")


# ──────────────────────────────────────────────
# DIRECT TEST
# ──────────────────────────────────────────────

if __name__ == "__main__":
    from dotenv import load_dotenv
    from config.routes import get_routes_for_operator, BOOKING_HORIZONS

    load_dotenv()

    print("Trenitalia Crawler Test")
    print("=" * 50)

    crawler = TrenitaliaCrawler()
    routes = get_routes_for_operator("trenitalia")

    print(f"{len(routes)} Trenitalia routes, {len(BOOKING_HORIZONS)} horizons\n")

    for route in routes[:1]:
        for horizon in BOOKING_HORIZONS[:1]:
            date = (datetime.now() + timedelta(days=horizon)).strftime("%Y-%m-%d")
            print(f"── {route.description} | +{horizon} days ({date})")
            try:
                url = crawler.get_url()
                solutions = crawler._fetch_all_solutions(url, route, date)
                records = crawler._parse_solutions(solutions, route)
                valid = crawler.validate(records)
                if valid:
                    print(f"   {len(valid)} trains found:")
                    for r in valid:
                        seats = r.get("seats_available")
                        print(
                            f"   {r['departure_time'].strftime('%H:%M')} -> "
                            f"{r['arrival_time'].strftime('%H:%M')} | "
                            f"{r['price_eur']:.2f} EUR | "
                            f"{str(seats) if seats is not None else '-'} seats | "
                            f"{r.get('fare_class') or '-'} | "
                            f"{r.get('train_number') or '-'}"
                        )
                else:
                    print("   No connections found")
            except Exception as e:
                print(f"   ERROR: {e}")
            print()