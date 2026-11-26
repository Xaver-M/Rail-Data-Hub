"""
PKP Intercity Crawler - prices from the normal ebilet.intercity.pl search (Berlin-Warsaw).

A real (headed) Chromium opens the public booking page and fills the search form like
a visitor (station autocomplete, date picker, time 00:00, "Dalej", "Szukaj połączenia").
The page itself loads the connection list (endpoint/Pociagi, metoda wyszukajPolaczenia)
and, per visible connection, its prices (endpoint/Sprzedaz, metoda sprawdzCene); the
crawler scrolls through the list and only reads those responses (no own API calls).
On the VM the browser runs under xvfb-run, like Italo, Eurostar and SJ.

- Only direct trains (one train in the connection): EC "Berlin-Warszawa Express" and
  the EC "Ursa"; connections with changes are skipped
- One record per train x class (1 / 2) with the cheapest fare (Super Promo International,
  Oferta Polska-Niemcy, ...). The page delivers the EUR price itself (cenaEuro);
  only if it is missing the PLN price is converted with a fixed rate (like CD/SJ)
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import json
import random
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from playwright.sync_api import sync_playwright

from crawlers.base.base_crawler import BaseCrawler
from config.routes import Route


BOOKING_URL = "https://ebilet.intercity.pl/"
API_HOST = "api-gateway.intercity.pl/server/public/endpoint/"

# Fallback PLN -> EUR conversion rate (Poland not in Eurozone)
PLN_TO_EUR = 1 / 4.25

TZ = ZoneInfo("Europe/Warsaw")              # Berlin and Warsaw: same zone rules

# Station name in config/routes.py -> (text typed into the autocomplete, suggestion to pick)
PKP_STATIONS = {
    "Berlin Hbf":         ("Berlin Hau", "Berlin Hauptbahnhof"),
    "Warszawa Centralna": ("Warszawa Cen", "Warszawa Centr."),
}

PL_MONTHS = ["stycznia", "lutego", "marca", "kwietnia", "maja", "czerwca", "lipca",
             "sierpnia", "września", "października", "listopada", "grudnia"]


def _api_call(resp, endpoint: str, method: str) -> dict | None:
    """Request body of a page API call to endpoint/<endpoint> with metoda <method>, else None."""
    if API_HOST + endpoint not in resp.url or resp.request.method != "POST":
        return None
    try:
        body = json.loads(resp.request.post_data or "{}")
    except Exception:
        return None
    return body if body.get("metoda") == method else None


class PKPIntercityCrawler(BaseCrawler):

    OPERATOR_NAME = "pkp_intercity"
    RESPONSE_TIMEOUT_MS = 45000
    PAGE_ROUNDS = 8                  # max. "Później" clicks (3 connections per page)
    PRICE_WAIT_S = 15                # max. wait for the prices of the visible connections
    MIN_SLEEP = 3.0                  # seconds between searches
    MAX_SLEEP = 6.0

    def __init__(self):
        super().__init__()
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=False)
        self.context = self.browser.new_context(locale="pl-PL", viewport={"width": 1400, "height": 1000})
        self.page = self.context.new_page()
        self.prices: dict[tuple[int, str], dict] = {}
        self.page.on("response", self._on_response)
        self.cookies_handled = False
        self.logger.info("PKP Intercity crawler ready (Playwright)")

    def _on_response(self, resp):
        req = _api_call(resp, "Sprzedaz", "sprawdzCene")
        if req is None or resp.status != 200:
            return
        try:
            odcinki = req.get("odcinki") or []
            if len(odcinki) != 1:
                return
            key = (int(odcinki[0]["pociagNr"]), odcinki[0]["wyjazdData"])
            self.prices[key] = resp.json()
        except Exception:
            pass

    def get_url(self) -> str:
        return BOOKING_URL

    def get_params(self, route: Route, date: str) -> dict:
        for st in (route.origin, route.destination):
            if st.name not in PKP_STATIONS:
                raise ValueError(f"No PKP station mapping for {st.name}")
        return {"origin": PKP_STATIONS[route.origin.name],
                "destination": PKP_STATIONS[route.destination.name],
                "date": date}

    # ── browser flow ───────────────────────────────────────────

    def fetch(self, url: str, params: dict = None, headers: dict = None) -> dict:
        """Search like a visitor; returns {"connections": [...], "prices": {(train, dep): body}}."""
        last_error = None
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                self.prices = {}
                connections = self._search(url, params)
                wanted = {(t["nrPociagu"], t["dataWyjazdu"])
                          for c in connections if len(c.get("pociagi") or []) == 1
                          for t in c["pociagi"]}
                # The list shows 3 connections at a time; their prices load one by one.
                # Wait for the visible prices, then click "Później" (later) like a visitor.
                later = self.page.get_by_role("button", name="Później", exact=True)
                for _ in range(self.PAGE_ROUNDS):
                    for _ in range(self.PRICE_WAIT_S * 2):
                        if wanted <= set(self.prices) or self._visible_prices_loaded():
                            break
                        self.page.wait_for_timeout(500)
                    if wanted <= set(self.prices):
                        break
                    if not later.count() or later.first.is_disabled():
                        break
                    later.first.scroll_into_view_if_needed()
                    later.first.click()
                    self.page.wait_for_timeout(1500)
                missing = wanted - set(self.prices)
                if missing:
                    self.logger.warning(f"{len(missing)}/{len(wanted)} direct trains without prices")
                return {"connections": connections, "prices": dict(self.prices)}
            except Exception as e:
                last_error = e
                self.logger.warning(f"Attempt {attempt}/{self.MAX_RETRIES} failed: {e}")
                self.page.wait_for_timeout(self.RETRY_DELAY * 1000 * attempt)
            finally:
                self.page.wait_for_timeout(random.uniform(self.MIN_SLEEP, self.MAX_SLEEP) * 1000)

        raise Exception(f"All {self.MAX_RETRIES} attempts failed: {last_error}")

    def _search(self, url: str, params: dict) -> list[dict]:
        page = self.page
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        self._handle_cookies()

        for field, (typed, pick) in (("#stationFrom", params["origin"]),
                                     ("#stationTo", params["destination"])):
            box = page.locator(field)
            box.wait_for(timeout=20000)
            box.click()
            box.press_sequentially(typed, delay=100)
            page.locator("[role=option]", has_text=pick).first.click(timeout=15000)
            page.wait_for_timeout(500)

        self._pick_date(params["date"])
        time_box = page.locator("input[type=time]")
        time_box.click()
        time_box.fill("00:00")
        page.locator("[data-testid=ConfirmButton]").click()

        search_btn = page.get_by_role("button", name="SZUKAJ POŁĄCZENIA")
        search_btn.wait_for(timeout=20000)
        with page.expect_response(lambda r: _api_call(r, "Pociagi", "wyszukajPolaczenia") is not None,
                                  timeout=self.RESPONSE_TIMEOUT_MS) as info:
            search_btn.click()
        resp = info.value
        req = json.loads(resp.request.post_data or "{}")
        if not str(req.get("dataWyjazdu", "")).startswith(params["date"]):
            raise Exception(f"connection search for wrong date: {req.get('dataWyjazdu')}")
        if resp.status != 200:
            raise Exception(f"HTTP {resp.status}")
        body = resp.json()
        if body.get("bledy") and not body.get("polaczenia"):
            raise Exception(f"search errors: {body['bledy']}")
        return [c for c in body.get("polaczenia") or []
                if str(c.get("dataWyjazdu", "")).startswith(params["date"])]

    def _visible_prices_loaded(self) -> bool:
        # "Ładowanie ceny" = price of a visible connection still loading
        return self.page.get_by_text("Ładowanie ceny").count() == 0

    def _pick_date(self, date: str):
        page = self.page
        d = datetime.strptime(date, "%Y-%m-%d")
        page.locator("[data-testid=SearchPanel-calendar]").click()
        label = f", {d.day} {PL_MONTHS[d.month - 1]} {d.year}"
        day = page.locator(f'.react-datepicker__day[aria-label$="{label}"]'
                           ':not(.react-datepicker__day--outside-month)')
        next_btn = page.get_by_role("button", name="następny miesiąc")
        next_btn.wait_for(timeout=10000)
        for _ in range(14):
            if day.count() and day.first.is_visible():
                break
            next_btn.click()
            page.wait_for_timeout(300)
        if not day.count():
            raise Exception(f"date {date} not in calendar")
        if day.first.get_attribute("aria-disabled") == "true":
            raise Exception(f"date {date} not bookable (disabled in calendar)")
        day.first.click()
        page.get_by_role("button", name="WYBIERZ").click()
        page.wait_for_timeout(400)

    def _handle_cookies(self):
        # Only strictly necessary cookies, once per browser context
        if self.cookies_handled:
            return
        try:
            btn = self.page.locator("#CybotCookiebotDialogBodyButtonDecline")
            btn.wait_for(timeout=10000)
            btn.click()
            self.page.wait_for_timeout(500)
        except Exception:
            pass
        self.cookies_handled = True

    # ── parsing ────────────────────────────────────────────────

    @staticmethod
    def _cheapest_per_class(body: dict) -> dict[int, tuple[float, str]]:
        """class -> (price EUR, offer name) of the cheapest seat offer."""
        out = {}
        for p in body.get("ceny") or []:
            if p.get("blad") or p.get("rodzajMiejscaKod") != 1:     # 1 = seat
                continue
            if p.get("cenaEuro"):
                eur = p["cenaEuro"] / 100
            elif p.get("cena"):
                eur = round(p["cena"] / 100 * PLN_TO_EUR, 2)
            else:
                continue
            offer = ", ".join(o.get("nazwaOferty", "") for o in p.get("opisyOfert") or [])
            cls = p.get("klasa")
            if cls in (1, 2) and (cls not in out or eur < out[cls][0]):
                out[cls] = (eur, offer)
        return out

    def parse(self, response: dict, route: Route = None) -> list[dict]:
        records = []
        for conn in response.get("connections") or []:
            trains = conn.get("pociagi") or []
            if len(trains) != 1:
                continue                     # connection with changes
            t = trains[0]
            body = response["prices"].get((t["nrPociagu"], t["dataWyjazdu"]))
            if not body:
                continue
            try:
                dep = datetime.strptime(t["dataWyjazdu"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=TZ)
                arr = datetime.strptime(t["dataPrzyjazdu"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=TZ)
            except Exception as e:
                self.logger.warning(f"Unparseable times skipped: {e}")
                continue

            for cls, (eur, _offer) in sorted(self._cheapest_per_class(body).items()):
                records.append({
                    "operator":        self.OPERATOR_NAME,
                    "origin":          route.origin.name if route else str(t["stacjaWyjazdu"]),
                    "destination":     route.destination.name if route else str(t["stacjaPrzyjazdu"]),
                    "origin_id":       str(t["stacjaWyjazdu"]),
                    "destination_id":  str(t["stacjaPrzyjazdu"]),
                    "departure_time":  dep,
                    "arrival_time":    arr,
                    "price_eur":       float(eur),
                    "seats_available": None,
                    "travel_class":    str(cls),
                    "train_number":    f"{t.get('kategoriaPociagu', '')} {t['nrPociagu']}".strip(),
                    "is_direct":       True,
                })

        self.logger.info(f"{len(records)} PKP Intercity fares found")
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
    import time
    from config.routes import BERLIN, WARSAW

    sys.stdout.reconfigure(encoding="utf-8")
    print("PKP Intercity Crawler Test")
    print("=" * 50)

    routes = [
        Route(origin=BERLIN, destination=WARSAW, operators=["pkp_intercity"],
              description="Berlin-Warsaw", route_id="berlin-warsaw"),
        Route(origin=WARSAW, destination=BERLIN, operators=["pkp_intercity"],
              description="Warsaw-Berlin", route_id="warsaw-berlin"),
    ]
    horizons = [int(h) for h in sys.argv[1:]] or [7, 30]

    crawler = PKPIntercityCrawler()
    try:
        for route in routes:
            for horizon in horizons:
                date = (datetime.now() + timedelta(days=horizon)).strftime("%Y-%m-%d")
                t0 = time.time()
                try:
                    body = crawler.fetch(crawler.get_url(), crawler.get_params(route, date))
                    records = crawler.parse(body, route)
                    for r in records:
                        r["booking_horizon_days"] = horizon
                        r["route_id"] = route.route_id
                    valid = crawler.validate(records)
                    n_conn = len(body["connections"])
                    n_direct = sum(1 for c in body["connections"] if len(c.get("pociagi") or []) == 1)
                    print(f"── {route.route_id:<14} {date} (+{horizon}d): {n_conn} connections, "
                          f"{n_direct} direct, {len(valid)} fares, {time.time() - t0:.0f}s")
                    for r in valid:
                        print(f"   {r['train_number']:<8} {r['departure_time']:%Y-%m-%d %H:%M} -> "
                              f"{r['arrival_time']:%H:%M}  class {r['travel_class']}  "
                              f"{r['price_eur']:>7.2f} EUR  {r['origin_id']}->{r['destination_id']}")
                except Exception as e:
                    print(f"── {route.route_id:<14} {date}: ERROR {e}")
    finally:
        crawler.close()
