"""
Renfe Crawler - prices from the normal renfe.com ticket search (Madrid-Barcelona).

A real (headed) Chromium opens the public search URL of renfe.com for each
route x date, like a visitor: accept cookies, choose "Solo ida", click
"Buscar billetes". The page then navigates to venta.renfe.com and itself loads
the train list (DWR call trainEnlacesManager.getTrainsList); the crawler only
reads that response (no own API calls). On the VM the browser runs under
xvfb-run, like Italo / Eurostar / SJ.

- The DWR response is a JavaScript callback with an object literal (unquoted
  keys); parse_dwr() converts it to JSON.
- One record per train x tariff (Básico / Elige / Elige Confort / Prémium, AVLO
  ...), fare_class = the tariff title shown on the page; adult fare in EUR.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import json
import random
from collections import Counter
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from playwright.sync_api import sync_playwright

from crawlers.base.base_crawler import BaseCrawler
from config.routes import Route


SEARCH_URL = "https://www.renfe.com/es/es/buscador-billetes"
TRAINS_DWR = "trainEnlacesManager.getTrainsList.dwr"
TZ_ES = ZoneInfo("Europe/Madrid")

# renfe.com search codes, keyed by the Station.name used in config/routes.py.
# Station.renfe_id ("0071,MADRI,null") is used first; this is the fallback.
RENFE_CODES = {
    "Madrid - Todas las estaciones": "MADRI",
    "Barcelona - Sants": "BARCE",
    # Codes from the page's own station list (estacionesEstaticas.js); city codes
    # like VALEN / ZARAG also exist but include regional stations, Sevilla has none.
    "Valencia - Joaquín Sorolla": "03216",
    "Sevilla - Santa Justa": "51003",
    "Zaragoza - Delicias": "04040",
}


# ──────────────────────────────────────────────
# DWR PARSING
# ──────────────────────────────────────────────

_IDENT = re.compile(r"[A-Za-z_$][\w$]*")


def _js_string_to_json(s: str) -> str:
    """Re-encode the body of a JS string literal as a JSON string body."""
    out, i = [], 0
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            n = s[i + 1]
            if n == "'":
                out.append("'"); i += 2; continue
            if n == "x" and i + 3 < len(s):
                out.append("\\u00" + s[i + 2:i + 4]); i += 4; continue
            if n in '"\\/bfnrtu':
                out.append(c + n); i += 2; continue
            out.append(n); i += 2; continue          # unknown escape: keep char
        if c == '"':
            out.append('\\"')
        else:
            out.append(c)
        i += 1
    return "".join(out)


def parse_dwr(text: str, marker: str = "r.handleCallback(") -> dict:
    """Extract the object literal passed to r.handleCallback(...) and return it as dict.

    Walks the literal once: strings are re-encoded, bare identifiers in key
    position are quoted, `new Date(n)` becomes n. Stops at the matching brace.
    """
    start = text.find(marker)
    if start < 0:
        raise ValueError("No DWR callback in response")
    start = text.find("{", start)
    if start < 0:
        raise ValueError("No object in DWR callback")

    out, depth, i, n = [], 0, start, len(text)
    while i < n:
        c = text[i]
        if c in "\"'":
            j = i + 1
            while j < n and text[j] != c:
                j += 2 if text[j] == "\\" else 1
            out.append('"' + _js_string_to_json(text[i + 1:j]) + '"')
            i = j + 1
            continue
        if c in "{[":
            depth += 1
        elif c in "}]":
            depth -= 1
            if depth == 0:
                out.append(c)
                break
        elif c.isalpha() or c in "_$":
            m = _IDENT.match(text, i)
            word = m.group(0)
            i = m.end()
            k = i
            while k < n and text[k] in " \t\r\n":
                k += 1
            if k < n and text[k] == ":":
                out.append(json.dumps(word))                     # key
            elif word == "new" and text.startswith("Date(", k):
                close = text.index(")", k)
                out.append(text[k + 5:close].strip() or "null")
                i = close + 1
            elif word in ("true", "false", "null"):
                out.append(word)
            elif word == "undefined":
                out.append("null")
            else:
                raise ValueError(f"Unexpected identifier in DWR at {i}: {word}")
            continue
        out.append(c)
        i += 1
    else:
        raise ValueError("Unterminated DWR object")

    return json.loads("".join(out), strict=False)


def _price(value) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(str(value).replace(".", "").replace(",", ".")) if "," in str(value) else float(value)
    except ValueError:
        return None


# ──────────────────────────────────────────────
# CRAWLER
# ──────────────────────────────────────────────

class RenfeCrawler(BaseCrawler):

    OPERATOR_NAME = "renfe"
    RESPONSE_TIMEOUT_MS = 60000
    MIN_SLEEP = 3.0                  # seconds between searches
    MAX_SLEEP = 6.0

    def __init__(self):
        super().__init__()
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=False)
        self.context = self.browser.new_context(locale="es-ES", timezone_id="Europe/Madrid",
                                                viewport={"width": 1400, "height": 1000})
        self.page = self.context.new_page()
        self.cookies_handled = False
        self.logger.info("Renfe crawler ready (Playwright)")

    def get_url(self) -> str:
        return SEARCH_URL

    @staticmethod
    def _code(station) -> str:
        if station.renfe_id:
            parts = station.renfe_id.split(",")
            if len(parts) >= 2 and parts[1]:
                return parts[1]
        code = RENFE_CODES.get(station.name)
        if not code:
            raise ValueError(f"No Renfe code for {station.name}")
        return code

    def get_params(self, route: Route, date: str) -> dict:
        return {
            "origin": self._code(route.origin),
            "destination": self._code(route.destination),
            "departure-date": date,
        }

    def fetch(self, url: str, params: dict = None, headers: dict = None) -> dict:
        """Run the public search like a visitor; return the page's own train list (as dict)."""
        query = "&".join(f"{k}={v}" for k, v in params.items())
        last_error = None

        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                self.page.goto(f"{url}?{query}", wait_until="domcontentloaded", timeout=60000)
                self._handle_cookies()
                self._check_blocked()
                self._choose_one_way()
                with self.page.expect_response(lambda r: TRAINS_DWR in r.url,
                                               timeout=self.RESPONSE_TIMEOUT_MS) as info:
                    self.page.get_by_role("button", name="Buscar billetes").click(timeout=10000)
                resp = info.value
                if resp.status != 200:
                    raise Exception(f"HTTP {resp.status}")
                body = parse_dwr(resp.text())
                body["_requested_date"] = params["departure-date"]
                return body
            except Exception as e:
                last_error = e
                self.logger.warning(f"Attempt {attempt}/{self.MAX_RETRIES} failed: {e}")
                self.page.wait_for_timeout(self.RETRY_DELAY * 1000 * attempt)
            finally:
                self.page.wait_for_timeout(random.uniform(self.MIN_SLEEP, self.MAX_SLEEP) * 1000)

        raise Exception(f"All {self.MAX_RETRIES} attempts failed: {last_error}")

    def _handle_cookies(self):
        if self.cookies_handled:
            return
        btn = self.page.get_by_role("button", name="Aceptar todas las cookies")
        try:
            btn.first.click(timeout=8000)
            self.page.wait_for_timeout(500)
        except Exception:
            pass
        self.cookies_handled = True

    def _choose_one_way(self):
        """Select "Solo ida". Sometimes the form ignores a selection made before its
        script is ready (search button stays disabled); then select again like a
        visitor would (round trip, then one way)."""
        one_way = self.page.get_by_role("radio", name="Solo ida")
        button = self.page.get_by_role("button", name="Buscar billetes")
        one_way.check(force=True, timeout=20000)
        for attempt in range(3):
            for _ in range(10):
                if button.is_enabled():
                    return
                self.page.wait_for_timeout(500)
            self.logger.info("Search button disabled, selecting 'Solo ida' again")
            self.page.get_by_role("radio", name="Ida y vuelta").check(force=True)
            self.page.wait_for_timeout(700)
            one_way.check(force=True)
        raise Exception("Search button stays disabled")

    def _check_blocked(self):
        # Visible challenge -> stop, never work around it
        html = self.page.content().lower()
        if "challenges.cloudflare.com" in html or "verify you are human" in html:
            raise Exception("blocked: bot challenge shown")

    def parse(self, response: dict, route: Route = None) -> list[dict]:
        records = []
        wanted = response.get("_requested_date")
        no_fares = Counter()

        for block in response.get("listadoTrenes") or []:
            for trip in block.get("listviajeViewEnlaceBean") or []:
                if wanted and trip.get("fecha") and trip["fecha"] != wanted:
                    continue
                legs = trip.get("trayectos") or []
                try:
                    dep = datetime.strptime(f"{trip['fecha']} {trip['horaSalida']}",
                                            "%Y-%m-%d %H:%M").replace(tzinfo=TZ_ES)
                    minutes = trip.get("duracionViajeTotalEnMinutos")
                    if minutes:
                        arr = dep + timedelta(minutes=int(minutes))
                    else:
                        arr = datetime.strptime(f"{trip['fecha']} {trip['horaLlegada']}",
                                                "%Y-%m-%d %H:%M").replace(tzinfo=TZ_ES)
                        if arr < dep:
                            arr += timedelta(days=1)
                except Exception as e:
                    self.logger.warning(f"Unparseable times skipped: {e}")
                    continue

                train_no = "/".join(l.get("cdgoTren") or "?" for l in legs) or None
                train_type = "/".join(t for t in (trip.get("tipoTrenUno"), trip.get("tipoTrenDos")) if t)
                is_direct = bool(trip.get("directo")) if trip.get("directo") is not None else len(legs) <= 1

                if not any(_price(t.get("precioTarifa")) for t in trip.get("tarifasDisponibles") or []):
                    no_fares[f"{train_type} completo={trip.get('completo')} "
                             f"razon={trip.get('razonNoDisponible')}"] += 1
                for tariff in trip.get("tarifasDisponibles") or []:
                    price = _price(tariff.get("precioTarifa"))
                    if not price:
                        continue
                    title = tariff.get("titulo") or tariff.get("codigoTarifa")
                    seats = tariff.get("plazasLibresTren")
                    records.append({
                        "operator":        self.OPERATOR_NAME,
                        "origin":          route.origin.name if route else trip.get("descripcionEstacionOrigen"),
                        "destination":     route.destination.name if route else trip.get("descripcionEstacionDestino"),
                        "origin_id":       trip.get("codigoEstacionOrigen"),
                        "destination_id":  trip.get("codigoEstacionDestino"),
                        "departure_time":  dep,
                        "arrival_time":    arr,
                        "price_eur":       price,
                        "seats_available": seats if isinstance(seats, int) else None,
                        "travel_class":    title,
                        "train_number":    f"{train_type} {train_no}".strip() if train_no else train_type or None,
                        "is_direct":       is_direct,
                    })

        if no_fares:
            self.logger.info(f"Trains listed without bookable fare (sold out etc.): {dict(no_fares)}")
        self.logger.info(f"{len(records)} Renfe fares found")
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
    from collections import Counter
    from config.routes import get_routes_for_operator

    sys.stdout.reconfigure(encoding="utf-8")
    print("Renfe Crawler Test")
    print("=" * 50)

    route_ids = sys.argv[1:] or ["madrid-barcelona", "barcelona-madrid"]
    routes = [r for r in get_routes_for_operator("renfe") if r.route_id in route_ids]
    crawler = RenfeCrawler()

    try:
        for route in routes:
            for horizon in [7, 30]:
                date = (datetime.now() + timedelta(days=horizon)).strftime("%Y-%m-%d")
                t0 = time.time()
                try:
                    body = crawler.fetch(crawler.get_url(), crawler.get_params(route, date))
                    records = crawler.parse(body, route)
                    for r in records:
                        r["booking_horizon_days"] = horizon
                        r["route_id"] = route.route_id
                    valid = crawler.validate(records)
                    trains = {r["train_number"] for r in valid}
                    types = Counter(r["train_number"].split()[0] for r in valid)
                    classes = Counter(r["travel_class"] for r in valid)
                    print(f"── {route.route_id:<20} +{horizon}d ({date}): {len(valid)} fares, "
                          f"{len(trains)} trains, {time.time() - t0:.0f}s")
                    print(f"   train types: {dict(types)}")
                    print(f"   fare classes: {dict(classes)}")
                    for r in valid[:6]:
                        print("   ", {k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in r.items()})
                except Exception as e:
                    print(f"── {route.route_id:<20} +{horizon}d: ERROR {e}")
    finally:
        crawler.close()
