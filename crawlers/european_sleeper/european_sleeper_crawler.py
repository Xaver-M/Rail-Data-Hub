"""
European Sleeper Crawler - night train prices from booking.europeansleeper.eu.

A real (headed) Chromium opens the normal result page for each route x date and,
if a train runs that day, clicks "Next" like a visitor. The crawler only reads the
responses the page itself loads (search/trains, search/availability); no own API
calls. On the VM the browser runs under xvfb-run, like Italo and Eurostar.

- The train runs ~3x/week per direction -> dates without a train give 0 records
- One record per place type (seat, couchette, berth, ...) with its cheapest
  fare type ("easy-night"); place types that are sold out/not offered are skipped
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import random
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from playwright.sync_api import sync_playwright

from crawlers.base.base_crawler import BaseCrawler
from config.routes import Route


BOOKING_URL = "https://booking.europeansleeper.eu/en"
ADULT = 72                                  # passenger type "Adult"
TZ = ZoneInfo("Europe/Brussels")            # Brussels, Prague: same zone rules


def _is_api(resp, endpoint: str) -> bool:
    return f"/api/search/{endpoint}" in resp.url and resp.request.method == "POST"


class EuropeanSleeperCrawler(BaseCrawler):

    OPERATOR_NAME = "european_sleeper"
    RESPONSE_TIMEOUT_MS = 45000
    MIN_SLEEP = 2.0                  # seconds between searches
    MAX_SLEEP = 5.0

    def __init__(self):
        super().__init__()
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=False)
        self.context = self.browser.new_context(locale="en-GB", viewport={"width": 1400, "height": 1000})
        self.page = self.context.new_page()
        self.cookies_handled = False
        self.logger.info("European Sleeper crawler ready (Playwright)")

    def get_url(self) -> str:
        return BOOKING_URL

    def get_params(self, route: Route, date: str) -> dict:
        if not route.origin.europeansleeper_id:
            raise ValueError(f"No europeansleeper_id for {route.origin.name}")
        if not route.destination.europeansleeper_id:
            raise ValueError(f"No europeansleeper_id for {route.destination.name}")
        return {
            "departureStation": route.origin.europeansleeper_id,
            "arrivalStation": route.destination.europeansleeper_id,
            "departureDate": date,
            "passengerTypes": ADULT,
            "bicycleCount": 0,
            "petsCount": 0,
        }

    def fetch(self, url: str, params: dict = None, headers: dict = None) -> dict | None:
        """Load the result page; if a train runs on the date, click 'Next' and return
        the page's own availability response. None = no train on this date."""
        query = "&".join(f"{k}={v}" for k, v in params.items())
        date = params["departureDate"]
        last_error = None

        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                with self.page.expect_response(lambda r: _is_api(r, "trains"),
                                               timeout=self.RESPONSE_TIMEOUT_MS) as info:
                    self.page.goto(f"{url}?{query}", wait_until="domcontentloaded", timeout=60000)
                trains = info.value.json()
                self._handle_cookies()

                if not self._runs_on(trains, date):
                    return None

                with self.page.expect_response(lambda r: _is_api(r, "availability"),
                                               timeout=self.RESPONSE_TIMEOUT_MS) as info:
                    self.page.get_by_text("Next", exact=False).last.click()
                resp = info.value
                req = resp.request.post_data_json or {}
                if req.get("travelDate") != date:
                    raise Exception(f"availability for wrong date: {req}")
                if resp.status != 200:
                    raise Exception(f"HTTP {resp.status}")
                body = resp.json()
                body["trainNumber"] = req.get("trainNumber")
                return body
            except Exception as e:
                last_error = e
                self.logger.warning(f"Attempt {attempt}/{self.MAX_RETRIES} failed: {e}")
                self.page.wait_for_timeout(self.RETRY_DELAY * 1000 * attempt)
            finally:
                self.page.wait_for_timeout(random.uniform(self.MIN_SLEEP, self.MAX_SLEEP) * 1000)

        raise Exception(f"All {self.MAX_RETRIES} attempts failed: {last_error}")

    def _handle_cookies(self):
        # Decline the consent banner once (only strictly necessary cookies)
        if self.cookies_handled:
            return
        btn = self.page.get_by_role("button", name="Decline")
        try:
            btn.first.wait_for(timeout=5000)
            btn.first.click()
            self.page.wait_for_timeout(500)
        except Exception:
            pass
        self.cookies_handled = True

    @staticmethod
    def _runs_on(trains: dict, date: str) -> bool:
        for result in trains.get("routeSearchResults") or []:
            for item in result.get("searchResultOutward") or []:
                trip = item.get("trip")
                if trip and trip.get("travelDate") == date and trip.get("bookable"):
                    return True
        return False

    def parse(self, response: dict | None, route: Route = None) -> list[dict]:
        if not response:
            self.logger.info("No train on this date")
            return []
        avail = (response.get("availabilityResult") or {}).get("availability") or {}
        try:
            dep = datetime.fromisoformat(avail["departureTime"]).replace(tzinfo=TZ)
            arr = datetime.fromisoformat(avail["arrivalTime"]).replace(tzinfo=TZ)
        except Exception as e:
            self.logger.warning(f"Unparseable times: {e}")
            return []

        records = []
        for pc in avail.get("priceClasses") or []:
            fares = [f for f in pc.get("fareTypes") or []
                     if f.get("bookable") and (f.get("prices") or {}).get("eur")]
            if not pc.get("bookable") or not fares:
                continue
            cheapest = min(fares, key=lambda f: f["prices"]["eur"])
            records.append({
                "operator":        self.OPERATOR_NAME,
                "origin":          route.origin.name if route else avail.get("departureStationName"),
                "destination":     route.destination.name if route else avail.get("arrivalStationName"),
                "origin_id":       avail.get("departureStationId"),
                "destination_id":  avail.get("arrivalStationId"),
                "departure_time":  dep,
                "arrival_time":    arr,
                "price_eur":       float(cheapest["prices"]["eur"]),
                "seats_available": pc.get("freeSeatsCount"),
                "travel_class":    pc.get("placeTypeKey"),
                "train_number":    response.get("trainNumber"),
                "is_direct":       True,
            })

        self.logger.info(f"{len(records)} European Sleeper place types found")
        return records

    def close(self):
        for closer in (self.browser.close, self.playwright.stop):
            try:
                closer()
            except Exception:
                pass


# ──────────────────────────────────────────────
# DIRECT TEST – no DB writes
# ──────────────────────────────────────────────

if __name__ == "__main__":
    from dotenv import load_dotenv
    from config.routes import get_routes_for_operator

    load_dotenv()

    print("European Sleeper Crawler Test")
    print("=" * 50)

    crawler = EuropeanSleeperCrawler()
    routes = get_routes_for_operator("european_sleeper")
    print(f"{len(routes)} European Sleeper routes\n")

    try:
        for route in routes:
            for horizon in [2, 3, 4, 14]:
                date = (datetime.now() + timedelta(days=horizon)).strftime("%Y-%m-%d")
                try:
                    body = crawler.fetch(crawler.get_url(), crawler.get_params(route, date))
                    valid = crawler.validate(crawler.parse(body, route))
                    if not valid:
                        print(f"── {route.route_id:<16} {date}: no train / no fares")
                        continue
                    cheapest = min(valid, key=lambda r: r["price_eur"])
                    print(f"── {route.route_id:<16} {date}: {len(valid)} place types, "
                          f"dep {valid[0]['departure_time']:%H:%M}, cheapest {cheapest['price_eur']:.2f} EUR "
                          f"({cheapest['travel_class']}), "
                          + ", ".join(f"{r['travel_class']}={r['price_eur']:.0f}" for r in valid))
                except Exception as e:
                    print(f"── {route.route_id:<16} {date}: ERROR {e}")
    finally:
        crawler.close()
