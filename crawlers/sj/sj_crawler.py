"""
SJ Crawler - prices from the normal sj.se result page (Stockholm-Oslo).

A real (headed) Chromium opens the public result URL for each route x date, like a
visitor. The page itself loads the departures and, per visible departure, its offers;
the crawler scrolls through the list and only reads those responses (no own API
calls). On the VM the browser runs under xvfb-run, like Italo and Eurostar.

- Only direct SJ trains (no changes): connections with Vy buses are not comparable
- One record per train x class (SECOND, SECOND_CALM, FIRST, ...) with its cheapest
  available flexibility; prices in SEK, converted with a fixed rate (like CD/CZK)
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import random
from datetime import datetime, timedelta
from urllib.parse import quote

from playwright.sync_api import sync_playwright

from crawlers.base.base_crawler import BaseCrawler
from config.routes import Route


RESULT_URL = "https://www.sj.se/en/search-journey/choose-journey/{origin}/{destination}/{date}"
DEPARTURES_PATH = "/sales/booking/v3/departures/search/"
OFFERS_PATH = "/offers?passengerListId="

# Approximate SEK -> EUR conversion rate (Sweden not in Eurozone)
SEK_TO_EUR = 1 / 11.0


class SJCrawler(BaseCrawler):

    OPERATOR_NAME = "sj"
    RESPONSE_TIMEOUT_MS = 45000
    SCROLL_ROUNDS = 12               # max. scroll steps until all offers are loaded
    MIN_SLEEP = 2.0                  # seconds between searches
    MAX_SLEEP = 5.0

    def __init__(self):
        super().__init__()
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=False)
        self.context = self.browser.new_context(locale="en-GB", viewport={"width": 1400, "height": 1000})
        self.page = self.context.new_page()
        self.offers: dict[str, dict] = {}
        self.page.on("response", self._on_response)
        self.cookies_handled = False
        self.logger.info("SJ crawler ready (Playwright)")

    def _on_response(self, resp):
        if OFFERS_PATH in resp.url and resp.status == 200:
            try:
                body = resp.json()
                self.offers[body["departureId"]] = body
            except Exception:
                pass

    def get_url(self) -> str:
        return RESULT_URL

    def get_params(self, route: Route, date: str) -> dict:
        if not route.origin.sj_name or not route.destination.sj_name:
            raise ValueError(f"No sj_name for {route.origin.name} / {route.destination.name}")
        return {"origin": route.origin.sj_name, "destination": route.destination.sj_name, "date": date}

    def fetch(self, url: str, params: dict = None, headers: dict = None) -> dict:
        """Load the result page, scroll until the offers of all direct trains are loaded.
        Returns {"departures": [...], "offers": {departureId: offers}}."""
        target = url.format(origin=quote(params["origin"]), destination=quote(params["destination"]),
                            date=params["date"])
        last_error = None

        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                self.offers = {}
                with self.page.expect_response(lambda r: DEPARTURES_PATH in r.url,
                                               timeout=self.RESPONSE_TIMEOUT_MS) as info:
                    self.page.goto(target, wait_until="domcontentloaded", timeout=60000)
                travels = info.value.json().get("travels") or []
                departures = [d for t in travels for d in t.get("departures") or []
                              if t.get("departureDate") == params["date"]]
                self._handle_cookies()

                wanted = {d["departureId"] for d in departures if d.get("numberOfChanges") == 0}
                for _ in range(self.SCROLL_ROUNDS):
                    if wanted <= set(self.offers):
                        break
                    self.page.mouse.wheel(0, 1200)
                    self.page.wait_for_timeout(1200)
                missing = wanted - set(self.offers)
                if missing:
                    self.logger.warning(f"{len(missing)}/{len(wanted)} direct trains without offers")
                return {"departures": departures, "offers": dict(self.offers)}
            except Exception as e:
                last_error = e
                self.logger.warning(f"Attempt {attempt}/{self.MAX_RETRIES} failed: {e}")
                self.page.wait_for_timeout(self.RETRY_DELAY * 1000 * attempt)
            finally:
                self.page.wait_for_timeout(random.uniform(self.MIN_SLEEP, self.MAX_SLEEP) * 1000)

        raise Exception(f"All {self.MAX_RETRIES} attempts failed: {last_error}")

    def _handle_cookies(self):
        # Only required cookies, once per browser context
        if self.cookies_handled:
            return
        btn = self.page.get_by_role("button", name="Only required cookies")
        try:
            btn.first.wait_for(timeout=5000)
            btn.first.click()
            self.page.wait_for_timeout(500)
        except Exception:
            pass
        self.cookies_handled = True

    @staticmethod
    def _cheapest_per_class(offer: dict) -> dict[str, tuple[float, str]]:
        """class -> (price SEK, flexibility) for all available seat offers."""
        out = {}
        for cls, data in ((offer.get("seatOffers") or {}).get("offers") or {}).items():
            for flex, o in (data.get("flexibilities") or {}).items():
                if not o.get("available"):
                    continue
                try:
                    amount = float(o["journeyPrices"]["price"]["amount"])
                except Exception:
                    continue
                if cls not in out or amount < out[cls][0]:
                    out[cls] = (amount, flex)
        return out

    def parse(self, response: dict, route: Route = None) -> list[dict]:
        records = []
        for dep in response.get("departures") or []:
            if dep.get("numberOfChanges") != 0:
                continue
            offer = response["offers"].get(dep["departureId"])
            if not offer:
                continue
            legs = dep.get("legs") or []
            try:
                dep_time = datetime.fromisoformat(dep["departureDateTime"])
                arr_time = datetime.fromisoformat(dep["arrivalDateTime"])
            except Exception as e:
                self.logger.warning(f"Unparseable times skipped: {e}")
                continue

            for cls, (sek, _flex) in self._cheapest_per_class(offer).items():
                records.append({
                    "operator":        self.OPERATOR_NAME,
                    "origin":          route.origin.name if route else dep["origin"]["name"],
                    "destination":     route.destination.name if route else dep["destination"]["name"],
                    "origin_id":       dep["origin"]["uicStationCode"],
                    "destination_id":  dep["destination"]["uicStationCode"],
                    "departure_time":  dep_time,
                    "arrival_time":    arr_time,
                    "price_eur":       round(sek * SEK_TO_EUR, 2),
                    "seats_available": None,
                    "travel_class":    cls,
                    "train_number":    "/".join(l.get("publicServiceName") or "?" for l in legs),
                    "is_direct":       True,
                })

        self.logger.info(f"{len(records)} SJ fares found")
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

    print("SJ Crawler Test")
    print("=" * 50)

    crawler = SJCrawler()
    routes = get_routes_for_operator("sj")
    print(f"{len(routes)} SJ routes\n")

    try:
        for route in routes:
            for horizon in [3, 30]:
                date = (datetime.now() + timedelta(days=horizon)).strftime("%Y-%m-%d")
                try:
                    body = crawler.fetch(crawler.get_url(), crawler.get_params(route, date))
                    valid = crawler.validate(crawler.parse(body, route))
                    direct = sum(1 for d in body["departures"] if d.get("numberOfChanges") == 0)
                    trains = {r["train_number"] for r in valid}
                    classes = sorted({r["travel_class"] for r in valid})
                    prices = sorted(r["price_eur"] for r in valid if r["travel_class"] == "SECOND")
                    print(f"── {route.route_id:<16} {date}: {len(trains)}/{direct} direct trains priced, "
                          f"{len(valid)} fares, classes {classes}, "
                          f"2nd {prices[0] if prices else '-'}-{prices[-1] if prices else '-'} EUR")
                except Exception as e:
                    print(f"── {route.route_id:<16} {date}: ERROR {e}")
    finally:
        crawler.close()
