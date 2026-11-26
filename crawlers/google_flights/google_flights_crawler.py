"""
GoogleFlightsCrawler – collects nonstop one-way economy fares from Google Flights
for selected intermodal corridors.

Location in repo: crawlers/google_flights/google_flights_crawler.py

Design notes:
- Fetches the Google Flights HTML itself (primp client with EU consent cookies),
  then uses fast-flights for query encoding and its data models. The default
  fast-flights fetcher sends no consent cookies and ends up on the
  consent.google.com page when run from the EU.
- The embedded result payload is parsed here (_parse_result_page), not with
  fast_flights.parser.parse: that parser (v3.1.0) only reads the "other flights"
  section (payload[3]) and drops "best flights" (payload[2], usually the cheapest
  ones), and it crashes on the whole page as soon as one itinerary has no price
  (e.g. SAS on Stockholm-Oslo shows "price unavailable").
- Reuses BaseCrawler for logging, DB connection, validation, save() and log_run().
- operator = airline slug (e.g. "ita_airways"); the transport mode comes from
  the operator_meta table (see database/migrations/2026_10_intermodal.sql).
- route_id matches the rail route_id -> join air and rail on route_id.
- fare_class encodes the bag variant ("economy_nobag" / "economy_cabinbag").

Test without DB writes (from repo root):
    py -m crawlers.google_flights.google_flights_crawler            # all FLIGHT_ROUTES
    # ad-hoc pairs (--tz only needed for airports not yet in AIRPORT_TZ):
    py -m crawlers.google_flights.google_flights_crawler \
        --pairs stockholm-oslo:ARN-OSL,oslo-stockholm:OSL-ARN \
        --tz ARN=Europe/Stockholm,OSL=Europe/Oslo --horizons 7,30
"""

import json
import os
import random
import re
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from primp import Client
from fast_flights import FlightQuery, Passengers, create_query
from fast_flights.model import Airport, CarbonEmission, Flights, SimpleDatetime, SingleFlight
from selectolax.lexbor import LexborHTMLParser
try:
    from fast_flights.exceptions import FlightsNotFound
except ImportError:  # other library layouts
    class FlightsNotFound(Exception):
        pass

from crawlers.base.base_crawler import BaseCrawler
from config.flight_routes import (
    AIRPORT_NAMES,
    AIRPORT_TZ,
    BAG_VARIANTS,
    FLIGHT_HORIZONS,
    FLIGHT_ROUTES,
)


GOOGLE_FLIGHTS_URL = "https://www.google.com/travel/flights"

# Pre-accepted consent cookies -> skip the EU "Before you continue" page
CONSENT_COOKIES = "SOCS=CAI; CONSENT=YES+"

# Real consent interstitial = a form posting to consent.google.*/save.
# A plain "consent.google" link also appears on normal result pages -> not a signal.
CONSENT_FORM_RE = re.compile(r'action="https://consent\.google\.[a-z.]+/save')

DEBUG_HTML_PATH = os.path.join("logs", "google_flights_last_error.html")

# Google Flights airline display names -> stable operator identifiers.
# Unknown names fall back to an automatic slug (see _airline_slug).
AIRLINE_SLUGS = {
    "ITA": "ita_airways",
    "ITA Airways": "ita_airways",
    "Aeroitalia": "aeroitalia",
    "Iberia": "iberia",
    "Iberia Express": "iberia",
    "Vueling": "vueling",
    "Air Europa": "air_europa",
    "Air France": "air_france",
    "Transavia": "transavia",
    "Transavia France": "transavia",
    "easyJet": "easyjet",
    "Ryanair": "ryanair",
    "Volotea": "volotea",
    "Austrian": "austrian",
    "Austrian Airlines": "austrian",
    "British Airways": "british_airways",
    "Brussels Airlines": "brussels_airlines",
    "KLM": "klm",
    "LOT": "lot",
    "LOT Polish Airlines": "lot",
    "TAROM": "tarom",
    "Wizz Air": "wizz_air",
    "SAS": "sas",
    "Scandinavian Airlines": "sas",
    "Norwegian": "norwegian",
    "Norwegian Air Shuttle": "norwegian",
    "Norwegian Air Sweden": "norwegian",
    "Ethiopian": "ethiopian",          # ET714/715 ARN-OSL (fifth-freedom leg to/from ADD)
}


def _airline_slug(name: str) -> str:
    if name in AIRLINE_SLUGS:
        return AIRLINE_SLUGS[name]
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_") or "unknown_airline"


class BlockedError(Exception):
    """Consent page or bot block – retrying the same request is pointless."""


# ─────────────────────────────────────────────────────────────
# RESULT PAGE PARSER
# ─────────────────────────────────────────────────────────────
# The result page embeds its data as JSON in <script class="ds:1">.
# payload[2][0] = "best flights", payload[3][0] = "other flights"; both are
# lists of itineraries k with k[0] = flight data, k[1][0] = [None, price]
# (k[1][0] == [] when Google shows "price unavailable").

PAYLOAD_SECTIONS = (2, 3)


def _parse_time(value) -> tuple[int, int]:
    # Google drops zero components: [8] = 08:00, [None, 31] = 00:31
    padded = [*(value or []), None, None]
    return (padded[0] or 0, padded[1] or 0)


def _parse_itinerary(k) -> Flights | None:
    """One payload itinerary -> fast-flights Flights; None if it has no price."""
    flight = k[0]
    price_block = k[1][0] if k[1] else None
    if not price_block or len(price_block) < 2 or price_block[1] is None:
        return None

    legs = []
    for sf in flight[2]:
        legs.append(SingleFlight(
            from_airport=Airport(code=sf[3], name=sf[4]),
            to_airport=Airport(code=sf[6], name=sf[5]),
            departure=SimpleDatetime(date=tuple(sf[20]), time=_parse_time(sf[8])),
            arrival=SimpleDatetime(date=tuple(sf[21]), time=_parse_time(sf[10])),
            duration=sf[11],
            plane_type=sf[17],
        ))

    extras = flight[22] if len(flight) > 22 and flight[22] else []
    return Flights(
        type=flight[0],
        price=price_block[1],
        airlines=flight[1],
        flights=legs,
        carbon=CarbonEmission(
            typical_on_route=extras[8] if len(extras) > 8 else None,
            emission=extras[7] if len(extras) > 7 else None,
        ),
    )


def _parse_result_page(html: str) -> tuple[list[Flights], int, int]:
    """
    Returns (priced itineraries, n_unpriced, n_malformed).
    Raises FlightsNotFound for Google's "no results" payload and AttributeError
    if the data script is missing (unknown page layout).
    """
    script = LexborHTMLParser(html).css_first(r"script.ds\:1")
    js = script.text()   # AttributeError if missing -> handled by caller
    data = js.split("data:", 1)[1].rsplit(",", 1)[0]
    if data.endswith("errorHasStatus: true"):
        raise FlightsNotFound("no flights found; received error")
    payload = json.loads(data)

    results, unpriced, malformed = [], 0, 0
    for idx in PAYLOAD_SECTIONS:
        section = payload[idx] if len(payload) > idx else None
        rows = (section[0] if section else None) or []
        for k in rows:
            try:
                it = _parse_itinerary(k)
            except (TypeError, IndexError, KeyError):
                malformed += 1
                continue
            if it is None:
                unpriced += 1
            else:
                results.append(it)
    return results, unpriced, malformed


class GoogleFlightsCrawler(BaseCrawler):

    OPERATOR_NAME = "google_flights"
    CURRENCY = "EUR"
    LANGUAGE = "en"
    MIN_SLEEP = 3.0                  # seconds between queries
    MAX_SLEEP = 7.0
    MAX_CONSECUTIVE_FAILURES = 6     # abort run if Google fails systematically

    def __init__(self):
        super().__init__()
        self.gf_client = self._create_gf_client()
        # (route_id, origin, destination) -> "ok" / "error"; used by the test summary
        self.pair_status: dict[tuple, str] = {}

    # ──────────────────────────────────────────────
    # Abstract methods (not used – requests go through _fetch_html)
    # ──────────────────────────────────────────────

    def get_url(self) -> str:
        return GOOGLE_FLIGHTS_URL

    def get_params(self, route, date: str) -> dict:
        return {}

    def parse(self, response, route=None) -> list[dict]:
        return []

    # ──────────────────────────────────────────────
    # HTTP
    # ──────────────────────────────────────────────

    @staticmethod
    def _create_gf_client() -> Client:
        # Same browser impersonation as fast-flights' default fetcher,
        # but one persistent client for the whole run (cookies survive).
        return Client(
            impersonate="chrome_145",
            impersonate_os="macos",
            referer=True,
            cookie_store=True,
        )

    def _fetch_html(self, query) -> str:
        res = self.gf_client.get(
            GOOGLE_FLIGHTS_URL,
            params=query.params(),
            headers={
                "Cookie": CONSENT_COOKIES,
                "Accept-Language": "en-US,en;q=0.9,de;q=0.8",
            },
        )
        html = res.text
        final_url = str(getattr(res, "url", ""))

        if "consent.google" in final_url or CONSENT_FORM_RE.search(html):
            self._dump_debug_html(html)
            raise BlockedError(
                f"Google consent page returned (url={final_url}) – "
                f"consent cookies not accepted, see {DEBUG_HTML_PATH}"
            )
        if "unusual traffic" in html or "/sorry/" in final_url:
            self._dump_debug_html(html)
            raise BlockedError(
                f"Google 'unusual traffic' block (url={final_url}) – "
                f"IP is rate-limited/blocked, see {DEBUG_HTML_PATH}"
            )
        return html

    def _dump_debug_html(self, html: str):
        try:
            os.makedirs("logs", exist_ok=True)
            with open(DEBUG_HTML_PATH, "w", encoding="utf-8") as f:
                f.write(html)
        except Exception as e:
            self.logger.warning(f"Could not write debug HTML: {e}")

    # ──────────────────────────────────────────────
    # QUERY
    # ──────────────────────────────────────────────

    def _build_query(self, origin: str, destination: str, date: str, carry_on_bags: int):
        return create_query(
            flights=[
                FlightQuery(
                    date=date,
                    from_airport=origin,
                    to_airport=destination,
                    max_stops=0,              # nonstop only
                ),
            ],
            seat="economy",
            trip="one-way",
            passengers=Passengers(adults=1),
            language=self.LANGUAGE,
            currency=self.CURRENCY,
            carry_on_bags=carry_on_bags,
        )

    def _query(self, origin: str, destination: str, date: str, carry_on_bags: int) -> list:
        query = self._build_query(origin, destination, date, carry_on_bags)

        last_error = None
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                html = self._fetch_html(query)
                try:
                    flights, unpriced, malformed = _parse_result_page(html)
                except FlightsNotFound:
                    # Valid page, but no (nonstop) flights for this pair/date -> 0 records, no retry
                    return []
                except (TypeError, IndexError, ValueError) as e:
                    # Result page without flight data (empty payload sections) -> 0 records
                    self.logger.info(
                        f"{origin}-{destination} {date} bags={carry_on_bags}: "
                        f"no flights in result payload ({type(e).__name__}: {e})"
                    )
                    return []
                except AttributeError as e:
                    # Data script missing -> page layout unknown; keep HTML for inspection
                    self._dump_debug_html(html)
                    raise Exception(
                        f"Flight data not found in HTML ({len(html)} bytes) – "
                        f"see {DEBUG_HTML_PATH}: {e}"
                    )
                if unpriced or malformed:
                    self.logger.info(
                        f"{origin}-{destination} {date} bags={carry_on_bags}: skipped "
                        f"{unpriced} itineraries without price, {malformed} malformed"
                    )
                return flights

            except BlockedError:
                raise  # no retry – would fail identically
            except Exception as e:
                last_error = e
                self.logger.warning(
                    f"{origin}-{destination} {date} bags={carry_on_bags}: "
                    f"attempt {attempt}/{self.MAX_RETRIES} failed: {e}"
                )
                if attempt < self.MAX_RETRIES:
                    time.sleep(self.RETRY_DELAY * attempt)

        raise Exception(f"All {self.MAX_RETRIES} attempts failed: {last_error}")

    # ──────────────────────────────────────────────
    # PARSING
    # ──────────────────────────────────────────────

    @staticmethod
    def _to_datetime(simple_dt, tz_name: str) -> datetime:
        year, month, day = simple_dt.date
        # time can come back as (h,) or (h, m) – pad defensively
        t = tuple(simple_dt.time) + (0, 0)
        return datetime(year, month, day, t[0], t[1], tzinfo=ZoneInfo(tz_name))

    def _parse_flights(self, results: list, origin: str, destination: str,
                       fare_class: str) -> list[dict]:
        by_key: dict[tuple, dict] = {}

        for itinerary in results:
            if itinerary.price is None or not itinerary.flights:
                continue

            legs = itinerary.flights
            first, last = legs[0], legs[-1]

            if origin not in AIRPORT_TZ or destination not in AIRPORT_TZ:
                self.logger.error(
                    f"{origin}-{destination}: airport missing in AIRPORT_TZ "
                    f"(config/flight_routes.py) – all flights skipped"
                )
                return []
            try:
                dep = self._to_datetime(first.departure, AIRPORT_TZ[origin])
                arr = self._to_datetime(last.arrival, AIRPORT_TZ[destination])
            except Exception as e:
                self.logger.warning(f"Unparseable times skipped: {e}")
                continue

            airlines = list(itinerary.airlines or ["unknown"])
            record = {
                "operator": _airline_slug(airlines[0]),
                "origin": AIRPORT_NAMES.get(origin, origin),
                "destination": AIRPORT_NAMES.get(destination, destination),
                "origin_id": origin,
                "destination_id": destination,
                "departure_time": dep,
                "arrival_time": arr,
                "price_eur": float(itinerary.price),
                "travel_class": fare_class,
                "seats_available": None,
                # fast-flights v3 exposes no flight number -> carrier(s) + dep time
                "train_number": f"{'/'.join(airlines)} {dep:%H%M}",
                "is_direct": len(legs) == 1,
            }

            # Codeshares: same physical flight may appear more than once -> keep cheapest
            key = (origin, destination, dep, arr, fare_class)
            if key not in by_key or record["price_eur"] < by_key[key]["price_eur"]:
                by_key[key] = record

        return list(by_key.values())

    # ──────────────────────────────────────────────
    # MAIN FLOW
    # ──────────────────────────────────────────────

    def run(self, routes: list = None, horizons: list[int] = None, write_db: bool = True):
        routes = routes or FLIGHT_ROUTES
        horizons = horizons or FLIGHT_HORIZONS

        n_queries = sum(len(r.airport_pairs) for r in routes) * len(horizons) * len(BAG_VARIANTS)
        self.logger.info(
            f"Crawler started – {len(routes)} routes, {len(horizons)} horizons, "
            f"{len(BAG_VARIANTS)} bag variants, ~{n_queries} queries"
        )
        start_time = datetime.now(timezone.utc)
        total_saved = 0
        errors = 0
        consecutive_failures = 0
        aborted_reason = None
        all_records = []

        try:
            if write_db:
                self._connect_db()

            for route in routes:
                for origin, destination in route.airport_pairs:
                    for horizon in horizons:
                        date = (datetime.now() + timedelta(days=horizon)).strftime("%Y-%m-%d")

                        for carry_on_bags, fare_class in BAG_VARIANTS.items():
                            try:
                                results = self._query(origin, destination, date, carry_on_bags)
                                records = self._parse_flights(results, origin, destination, fare_class)

                                for r in records:
                                    r["booking_horizon_days"] = horizon
                                    r["route_id"] = route.route_id

                                valid = self.validate(records)

                                if write_db:
                                    saved = self.save(valid)
                                    total_saved += saved
                                else:
                                    all_records.extend(valid)
                                    saved = len(valid)

                                consecutive_failures = 0
                                self.pair_status.setdefault((route.route_id, origin, destination), "ok")
                                self.logger.info(
                                    f"{route.route_id} {origin}-{destination} +{horizon}d "
                                    f"{fare_class}: {saved} records"
                                )

                            except Exception as e:
                                errors += 1
                                consecutive_failures += 1
                                if self.pair_status.get((route.route_id, origin, destination)) != "ok":
                                    self.pair_status[(route.route_id, origin, destination)] = "error"
                                self.logger.error(
                                    f"Error on {route.route_id} {origin}-{destination} "
                                    f"+{horizon}d {fare_class}: {e}"
                                )
                                if isinstance(e, BlockedError) or \
                                        consecutive_failures >= self.MAX_CONSECUTIVE_FAILURES:
                                    aborted_reason = str(e)
                                    break

                            time.sleep(random.uniform(self.MIN_SLEEP, self.MAX_SLEEP))

                        if aborted_reason:
                            break
                    if aborted_reason:
                        break
                if aborted_reason:
                    break

            total = total_saved if write_db else len(all_records)
            if not aborted_reason and total == 0:
                # Empty result pages are treated as "no flights" (see _query). If the WHOLE
                # run is empty, Google most likely changed its page format -> fail loudly.
                aborted_reason = (
                    "0 records in the whole run - Google Flights page format may have "
                    "changed or results are blocked; check logs/google_flights_last_error.html"
                )

            if aborted_reason:
                self.logger.error(f"Run aborted/failed: {aborted_reason}")
                status = "error"
            else:
                status = "success" if errors == 0 else "partial_error"

            if write_db:
                self.log_run(status, total_saved, aborted_reason)

        except Exception as e:
            self.logger.error(f"Critical error in crawler: {e}")
            if write_db and self.db_conn:
                self.log_run("error", total_saved, str(e))
            raise

        finally:
            if write_db:
                self._close_db()

        duration = (datetime.now(timezone.utc) - start_time).seconds
        self.logger.info(
            f"Crawler finished – {total_saved if write_db else len(all_records)} records, "
            f"{errors} errors, {duration}s runtime"
        )

        # Production run: surface failures to run_crawlers.py / systemd (exit code 1)
        if write_db and aborted_reason:
            raise RuntimeError(aborted_reason)
        return all_records


# ─────────────────────────────────────────────────────────────
# TEST MODE – no DB writes
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    import sys
    from config.flight_routes import FlightRoute

    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Google Flights test run (no DB writes)")
    ap.add_argument("--pairs", help="route_id:ORIG-DEST[,...]; default: all FLIGHT_ROUTES")
    ap.add_argument("--tz", help="CODE=Zone[,...] for airports not yet in AIRPORT_TZ (test only)")
    ap.add_argument("--horizons", default="7,30")
    args = ap.parse_args()

    if args.tz:
        for item in args.tz.split(","):
            code, zone = item.split("=", 1)
            AIRPORT_TZ.setdefault(code, zone)

    test_routes = FLIGHT_ROUTES
    if args.pairs:
        grouped: dict[str, list[tuple[str, str]]] = {}
        for item in args.pairs.split(","):
            rid, pair = item.split(":", 1)
            o, d = pair.split("-", 1)
            grouped.setdefault(rid, []).append((o, d))
        test_routes = [FlightRoute(route_id=rid, description="test", airport_pairs=pairs)
                       for rid, pairs in grouped.items()]

    crawler = GoogleFlightsCrawler()
    records = crawler.run(routes=test_routes,
                          horizons=[int(h) for h in args.horizons.split(",")],
                          write_db=False)

    configured = [(r.route_id, o, d) for r in test_routes for o, d in r.airport_pairs]

    print("\n=== Results per airport pair (horizons 7 + 30, both bag variants) ===")
    for key in configured:
        rs = [r for r in records if (r["route_id"], r["origin_id"], r["destination_id"]) == key]
        if rs:
            prices = sorted(r["price_eur"] for r in rs)
            airlines = sorted({r["operator"] for r in rs})
            print(f"  {key[0]:<18} {key[1]}-{key[2]}  {len(rs):>4} records  "
                  f"{prices[0]:>7.2f}-{prices[-1]:>7.2f} EUR  {', '.join(airlines)}")
        elif crawler.pair_status.get(key) == "ok":
            print(f"  {key[0]:<18} {key[1]}-{key[2]}     0 records  -> no nonstop flights, prune")
        elif crawler.pair_status.get(key) == "error":
            print(f"  {key[0]:<18} {key[1]}-{key[2]}     ERROR      -> queries failed, check log")
        else:
            print(f"  {key[0]:<18} {key[1]}-{key[2]}     not tested -> run aborted before this pair")

    print(f"\n{len(records)} records total. Sample:")
    for r in records[:10]:
        print(
            f"  {r['route_id']:<18} {r['origin_id']}-{r['destination_id']} "
            f"{r['departure_time']:%Y-%m-%d %H:%M} -> {r['arrival_time']:%H:%M} "
            f"{r['operator']:<12} {r['train_number']:<16} "
            f"{r['travel_class']:<17} {r['price_eur']:>8.2f} EUR  +{r['booking_horizon_days']}d"
        )
