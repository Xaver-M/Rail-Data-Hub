"""
České dráhy Crawler – Price data via the internal CDIS mobile API.

No API key required; uses the same endpoint as the official CD mobile app.
API base: https://ipws.cdis.cz/IP.svc

Flow per route × horizon:
  1. CreateSession       → session token
  2. SearchConnectionInfo1 → connection list + handle
  3. GetConnectionsPrice  → CZK prices per connection
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import re
import time
from datetime import datetime, timedelta, timezone

import requests
from dotenv import load_dotenv

from crawlers.base.base_crawler import BaseCrawler
from config.routes import Route

load_dotenv()

# Approximate CZK → EUR conversion rate (Czech Republic not in Eurozone)
CZK_TO_EUR = 1 / 25.0


class CeskeDrahyCrawler(BaseCrawler):
    """
    Crawler for České dráhy (Czech Railways).

    Uses the CDIS mobile API (same as the official CD app).
    All requests are POST with JSON bodies; responses are wrapped in a 'd' field.
    Prices are returned in hundredths of CZK (e.g. 30500 = 305.00 CZK).
    """

    OPERATOR_NAME = "ceske-drahy"
    BASE_URL = "https://ipws.cdis.cz/IP.svc"
    APP_ID = "{A6AB5B3E-8A7E-4E84-9DC8-801561CE886F}"
    USER_DESC = "294|34|MCP-Client|^|mcp-cd-server|en|US|440|1080|2154|1.0.0"
    CD_HEADERS = {
        "Content-Type": "application/json",
        "User-Agent": "okhttp/4.9.3",
    }

    def __init__(self):
        super().__init__()
        self.logger.info("České dráhy Crawler (CDIS mobile API) ready")

    # ──────────────────────────────────────────────
    # ABSTRACT METHOD STUBS (not used – run() is overridden)
    # ──────────────────────────────────────────────

    def get_url(self) -> str:
        return self.BASE_URL

    def get_params(self, route, date: str) -> dict:
        return {}

    def parse(self, response: requests.Response, route=None) -> list[dict]:
        return []

    # ──────────────────────────────────────────────
    # CD API HELPERS
    # ──────────────────────────────────────────────

    def _post(self, endpoint: str, body: dict) -> dict:
        url = f"{self.BASE_URL}/{endpoint}"
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                r = self.session.post(
                    url, json=body, headers=self.CD_HEADERS,
                    timeout=self.REQUEST_TIMEOUT
                )
                r.raise_for_status()
                data = r.json()
                if "Message" in data and "Unautorisierter" in data.get("Message", ""):
                    raise Exception(f"CD API auth error: {data['Message']}")
                return data.get("d")
            except Exception as e:
                self.logger.warning(f"CD API {endpoint} attempt {attempt}: {e}")
                if attempt < self.MAX_RETRIES:
                    time.sleep(self.RETRY_DELAY)
        raise Exception(f"CD API {endpoint} failed after {self.MAX_RETRIES} attempts")

    def _new_cd_session(self) -> str:
        result = self._post("CreateSession", {
            "iLang": 1,
            "sAppID": self.APP_ID,
            "sUserDesc": self.USER_DESC,
            "sUser": "",
            "sPwd": "",
            "iTokenType": 1,
            "oRegisterNotificationsSettings": {
                "iNotificationMask": 2047,
                "iInitialAdvance": 30,
                "iDelayLimit": 5,
                "iChangeAdvance": 5,
                "iGetOffAdvance": 5,
            },
        })
        return result["sSessionID"]

    def _search_connections(
        self, session_id: str, from_name: str, to_name: str, dep_dt: datetime
    ) -> dict:
        dep_ms = int(dep_dt.timestamp() * 1000)
        return self._post("SearchConnectionInfo1", {
            "iLang": 1,
            "sSessionID": session_id,
            "oFrom": {"iListID": 100003, "sName": from_name},
            "oTo": {"iListID": 100003, "sName": to_name},
            "aoVia": [],
            "aoChange": [],
            "dtDateTime": f"/Date({dep_ms})/",
            "bIsDep": True,
            "oConnParms": {"iSearchConnectionFlags": 0, "iCarrier": 2},
            "iMaxObjectsCount": 0,
            "iMaxCount": 50,
            "oPriceRequestClass": {"iClass": 2, "bBusiness": False},
            "aoPassengers": [
                {"oPassenger": {"iPassengerId": 5}, "iCount": 1, "iAge": -1}
            ],
        })

    def _get_prices(
        self, session_id: str, handle: int, conn_ids: list[int]
    ) -> list[dict]:
        try:
            return self._post("GetConnectionsPrice", {
                "iLang": 1,
                "sSessionID": session_id,
                "iHandle": handle,
                "aiConnID": conn_ids,
                "oPriceRequest": {
                    "aoPassengers": [
                        {"oPassenger": {"iPassengerId": 5}, "iCount": 1, "iAge": -1}
                    ],
                    "iConnHandleThere": 0,
                    "iConnIDThere": 0,
                    "oClass": {"iClass": 2, "bBusiness": False},
                    "iDocType": 1,
                },
                "bStopIfAgeError": True,
            }) or []
        except Exception as e:
            self.logger.warning(f"Price fetch failed: {e}")
            return []

    def _parse_cd_date(self, raw: str) -> datetime:
        """Convert /Date(ms)/ to UTC datetime."""
        m = re.match(r"/Date\((-?\d+)\)/", raw)
        if m:
            return datetime.fromtimestamp(int(m.group(1)) / 1000, tz=timezone.utc)
        return datetime.fromisoformat(raw)

    def _parse_connections(
        self, result: dict, prices: list[dict], route: Route
    ) -> list[dict]:
        records = []
        conns = result.get("oConnInfo", {}).get("aoConnections", [])
        price_map = {
            conn_id: p.get("iPrice", 0)
            for conn_id, p in zip(
                [c["iID"] for c in conns], prices
            )
        } if prices else {}

        for conn in conns:
            try:
                trains = conn.get("aoTrains", [])
                if not trains:
                    continue

                first_leg = trains[0]
                last_leg = trains[-1]
                departure = self._parse_cd_date(first_leg["dtDateTime1"])
                arrival = self._parse_cd_date(last_leg["dtDateTime2"])

                price_hundredths = price_map.get(conn["iID"], 0)
                if price_hundredths <= 0:
                    continue
                price_czk = price_hundredths / 100.0
                price_eur = price_czk * CZK_TO_EUR

                train_type = first_leg.get("sType", "")
                train_number = " ".join(
                    filter(None, [
                        first_leg.get("sNum1", ""),
                        first_leg.get("sNum2", ""),
                    ])
                ).strip()

                records.append({
                    "operator":        self.OPERATOR_NAME,
                    "origin":          route.origin.name,
                    "destination":     route.destination.name,
                    "origin_id":       str(first_leg.get("iStationKey1", "")),
                    "destination_id":  str(last_leg.get("iStationKey2", "")),
                    "departure_time":  departure,
                    "arrival_time":    arrival,
                    "price_eur":       round(price_eur, 2),
                    "price_czk":       price_czk,
                    "seats_available": None,
                    "travel_class":    "2nd",
                    "train_number":    train_number,
                    "train_type":      train_type,
                    "is_direct":       len(trains) == 1,
                    "transfers_count": len(trains) - 1,
                })
            except Exception as e:
                self.logger.warning(f"Parse error on connection {conn.get('iID')}: {e}")

        return records

    # ──────────────────────────────────────────────
    # MAIN FLOW  (overrides BaseCrawler.run)
    # ──────────────────────────────────────────────

    def run(self, routes: list, horizons: list[int]):
        self.logger.info(
            f"Crawler started – {len(routes)} routes, {len(horizons)} horizons"
        )
        start_time = datetime.now(timezone.utc)
        total_saved = 0
        errors = 0

        try:
            self._connect_db()

            for route in routes:
                if self.OPERATOR_NAME not in route.operators:
                    continue

                from_name = getattr(route.origin, "cd_station_name", None) or route.origin.name
                to_name   = getattr(route.destination, "cd_station_name", None) or route.destination.name

                for horizon in horizons:
                    dep_dt = (
                        datetime.now(timezone.utc)
                        .replace(hour=6, minute=0, second=0, microsecond=0)
                        + timedelta(days=horizon)
                    )
                    try:
                        session_id = self._new_cd_session()
                        result = self._search_connections(session_id, from_name, to_name, dep_dt)

                        conns = result.get("oConnInfo", {}).get("aoConnections", [])
                        if not conns:
                            self.logger.info(f"{route.description} +{horizon}d: no connections")
                            continue

                        handle = result["iHandle"]
                        conn_ids = [c["iID"] for c in conns]
                        prices = self._get_prices(session_id, handle, conn_ids)

                        records = self._parse_connections(result, prices, route)

                        for r in records:
                            r["booking_horizon_days"] = horizon
                            r["route_id"] = route.route_id

                        valid_records = self.validate(records)
                        saved = self.save(valid_records)
                        total_saved += saved

                        self.logger.info(
                            f"{route.description} +{horizon}d: {saved} saved"
                        )

                    except Exception as e:
                        errors += 1
                        self.logger.error(
                            f"Error on {route.description} +{horizon}d: {e}"
                        )
                        continue

            status = "success" if errors == 0 else "partial_error"
            self.log_run(status, total_saved)

        except Exception as e:
            self.logger.error(f"Critical error: {e}")
            self.log_run("error", total_saved, str(e))
            raise

        finally:
            self._close_db()

        duration = (datetime.now(timezone.utc) - start_time).seconds
        self.logger.info(
            f"Crawler finished – {total_saved} records, {errors} errors, {duration}s"
        )


# ──────────────────────────────────────────────
# DIRECT TEST
# ──────────────────────────────────────────────

if __name__ == "__main__":
    from datetime import timedelta
    from dotenv import load_dotenv
    from config.routes import get_routes_for_operator, BOOKING_HORIZONS

    load_dotenv()

    print("České dráhy Crawler Test")
    print("=" * 50)

    crawler = CeskeDrahyCrawler()
    routes = get_routes_for_operator("ceske-drahy")

    print(f"{len(routes)} CD routes, testing first 2 × first 3 horizons\n")

    for route in routes[:2]:
        for horizon in BOOKING_HORIZONS[:3]:
            from_name = getattr(route.origin, "cd_station_name", None) or route.origin.name
            to_name   = getattr(route.destination, "cd_station_name", None) or route.destination.name
            dep_dt = (
                datetime.now(timezone.utc)
                .replace(hour=6, minute=0, second=0, microsecond=0)
                + timedelta(days=horizon)
            )
            print(f"── {route.description} | +{horizon} days ({dep_dt.strftime('%Y-%m-%d')})")

            try:
                session_id = crawler._new_cd_session()
                result = crawler._search_connections(session_id, from_name, to_name, dep_dt)
                conns = result.get("oConnInfo", {}).get("aoConnections", [])

                if not conns:
                    print("   No connections found")
                    print()
                    continue

                handle = result["iHandle"]
                conn_ids = [c["iID"] for c in conns]
                prices = crawler._get_prices(session_id, handle, conn_ids)
                records = crawler._parse_connections(result, prices, route)
                valid = crawler.validate(records)

                if valid:
                    print(f"   {len(valid)} connections:")
                    for r in valid[:3]:
                        direct = "direct" if r.get("is_direct") else f"{r.get('transfers_count')} transfers"
                        print(
                            f"   {r['departure_time'].strftime('%H:%M')} → "
                            f"{r['arrival_time'].strftime('%H:%M')} | "
                            f"{r['train_type']} {r.get('train_number','')} | "
                            f"{r['price_eur']:.2f} EUR ({r['price_czk']:.0f} CZK) | "
                            f"{direct}"
                        )
                    if len(valid) > 3:
                        print(f"   ... and {len(valid) - 3} more")
                else:
                    print("   No priced connections found")

            except Exception as e:
                print(f"   ERROR: {e}")

            print()
