"""
Eurostar Crawler - prices from the normal eurostar.com search page.

A real (headed) Chromium opens the public search page for each route x date,
exactly like a visitor would. The page itself requests its journey search from
site-api.eurostar.com; the crawler only reads that response (no own API calls).
On the VM the browser runs under xvfb-run, like the Italo crawler.

- Locale be-en -> prices in EUR
- One record per train x class of service (Standard / Plus / Premier),
  adult public fare; sold-out classes are skipped
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import random
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from playwright.sync_api import sync_playwright

from crawlers.base.base_crawler import BaseCrawler
from config.routes import Route


SEARCH_URL = "https://www.eurostar.com/search/be-en"
GATEWAY_URL = "site-api.eurostar.com/gateway"
SEARCH_OPERATION = "NewBookingSearch"

# Eurostar returns local times without offset; UK stations have UIC prefix 70
TZ_UK = ZoneInfo("Europe/London")
TZ_CONTINENT = ZoneInfo("Europe/Paris")   # Paris, Brussels, Amsterdam: same zone


def _station_tz(uic: str) -> ZoneInfo:
    return TZ_UK if uic.startswith("70") else TZ_CONTINENT


class EurostarCrawler(BaseCrawler):

    OPERATOR_NAME = "eurostar"
    RESPONSE_TIMEOUT_MS = 45000
    MIN_SLEEP = 2.0                  # seconds between searches
    MAX_SLEEP = 5.0

    def __init__(self):
        super().__init__()
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=False)
        self.context = self.browser.new_context(locale="en-GB")
        self.page = self.context.new_page()
        self.logger.info("Eurostar crawler ready (Playwright)")

    def get_url(self) -> str:
        return SEARCH_URL

    def get_params(self, route: Route, date: str) -> dict:
        if not route.origin.eurostar_id:
            raise ValueError(f"No eurostar_id for {route.origin.name}")
        if not route.destination.eurostar_id:
            raise ValueError(f"No eurostar_id for {route.destination.name}")
        return {
            "adult": 1,
            "origin": route.origin.eurostar_id,
            "destination": route.destination.eurostar_id,
            "outbound": date,
        }

    def fetch(self, url: str, params: dict = None, headers: dict = None) -> dict:
        """Load the search page and return the page's own journeySearch response (JSON)."""
        query = "&".join(f"{k}={v}" for k, v in params.items())
        last_error = None

        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                with self.page.expect_response(self._is_search_response,
                                               timeout=self.RESPONSE_TIMEOUT_MS) as info:
                    self.page.goto(f"{url}?{query}", wait_until="domcontentloaded", timeout=60000)
                resp = info.value
                if resp.status != 200:
                    raise Exception(f"HTTP {resp.status}")
                body = resp.json()
                if body.get("errors") and not body.get("data"):
                    raise Exception(f"GraphQL errors: {body['errors']}")
                return body
            except Exception as e:
                last_error = e
                self.logger.warning(f"Attempt {attempt}/{self.MAX_RETRIES} failed: {e}")
                self.page.wait_for_timeout(self.RETRY_DELAY * 1000 * attempt)
            finally:
                self.page.wait_for_timeout(random.uniform(self.MIN_SLEEP, self.MAX_SLEEP) * 1000)

        raise Exception(f"All {self.MAX_RETRIES} attempts failed: {last_error}")

    @staticmethod
    def _is_search_response(resp) -> bool:
        if GATEWAY_URL not in resp.url or resp.request.method != "POST":
            return False
        try:
            return (resp.request.post_data_json or {}).get("operationName") == SEARCH_OPERATION
        except Exception:
            return False

    @staticmethod
    def _to_datetime(date: str, time: str, tz: ZoneInfo) -> datetime:
        return datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M").replace(tzinfo=tz)

    def parse(self, response: dict, route: Route = None) -> list[dict]:
        records = []
        search = ((response.get("data") or {}).get("journeySearch") or {}).get("outbound") or {}

        for journey in search.get("journeys") or []:
            for fare in journey.get("fares") or []:
                price = (fare.get("prices") or {}).get("displayPrice")
                legs = fare.get("legs") or []
                if not price or not legs:
                    continue     # class sold out / not offered on this train

                first, last = legs[0], legs[-1]
                try:
                    dep = self._to_datetime(first["timing"]["departureDate"], first["timing"]["departureTime"],
                                            _station_tz(first["origin"]["uic"]))
                    arr = self._to_datetime(last["timing"]["arrivalDate"], last["timing"]["arrivalTime"],
                                            _station_tz(last["destination"]["uic"]))
                except Exception as e:
                    self.logger.warning(f"Unparseable times skipped: {e}")
                    continue

                records.append({
                    "operator":        self.OPERATOR_NAME,
                    "origin":          route.origin.name if route else first["origin"]["name"],
                    "destination":     route.destination.name if route else last["destination"]["name"],
                    "origin_id":       first["origin"]["uic"],
                    "destination_id":  last["destination"]["uic"],
                    "departure_time":  dep,
                    "arrival_time":    arr,
                    "price_eur":       float(price),
                    "seats_available": fare.get("seats"),
                    "travel_class":    (fare.get("classOfService") or {}).get("code"),
                    "train_number":    "/".join(leg.get("serviceName") or "?" for leg in legs),
                    "is_direct":       len(legs) == 1,
                })

        self.logger.info(f"{len(records)} Eurostar fares found")
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

    print("Eurostar Crawler Test")
    print("=" * 50)

    crawler = EurostarCrawler()
    routes = get_routes_for_operator("eurostar")
    print(f"{len(routes)} Eurostar routes\n")

    try:
        for route in routes:
            for horizon in [14]:
                date = (datetime.now() + timedelta(days=horizon)).strftime("%Y-%m-%d")
                try:
                    body = crawler.fetch(crawler.get_url(), crawler.get_params(route, date))
                    valid = crawler.validate(crawler.parse(body, route))
                    std = [r for r in valid if r["travel_class"] == "STANDARD"]
                    direct = sum(1 for r in std if r["is_direct"])
                    if std:
                        prices = sorted(r["price_eur"] for r in std)
                        print(f"── {route.route_id:<20} +{horizon}d: {len(valid):>3} fares, {len(std)} trains "
                              f"({direct} direct), Standard {prices[0]:.0f}-{prices[-1]:.0f} EUR")
                    else:
                        print(f"── {route.route_id:<20} +{horizon}d: no Standard fares ({len(valid)} fares)")
                except Exception as e:
                    print(f"── {route.route_id:<20} +{horizon}d: ERROR {e}")
    finally:
        crawler.close()
