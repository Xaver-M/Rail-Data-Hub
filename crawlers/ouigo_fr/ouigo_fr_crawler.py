"""
Ouigo España Crawler - Price data via the mdw02.api-es.ouigo.com API.

Token login with app credentials from .env.
Returns the cheapest daily price per route (Calendar/prices endpoint).
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import time
from datetime import datetime
import requests

from crawlers.base.base_crawler import BaseCrawler
from config.routes import Route


class OuigoFrCrawler(BaseCrawler):

    OPERATOR_NAME = "ouigo_fr"
    BASE_URL = "https://mdw.api-fr.ouigo.com/api/Token/login"
    TOKEN_URL = "https://mdw02.api-es.ouigo.com/api/Token/login"

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Content-Type": "application/json",
        "Origin": "https://ventas.ouigo.com",
        "Referer": "https://ventas.ouigo.com/"
    }

    def __init__(self): #
        super().__init__()
        self._token = None
        self._token_expiry = None
        username = os.getenv("OUIGO_FR_USERNAME")
        password = os.getenv("OUIGO_FR_PASSWORD")
        if not username or not password:
            raise ValueError("OUIGO_FR_USERNAME and OUIGO_FR_PASSWORD must be set in .env")
        self._username = username
        self._password = password
        self.logger.info("Ouigo France Crawler ready")

    def _get_token(self) -> str:
        """Fetch or renew the token if expired."""
        now = datetime.now()
        if self._token and self._token_expiry and now < self._token_expiry:
            return self._token

        self.logger.info("Fetching Ouigo France token...")
        r = self.session.post(
            self.TOKEN_URL,
            json={"username": self._username, "password": self._password},
            headers=self.HEADERS,
            timeout=self.REQUEST_TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
        self._token = data["token"]
        # Token expiry with 5-minute buffer
        expiry_str = data.get("expirationDate", "")
        if expiry_str:
            from datetime import timezone
            expiry = datetime.fromisoformat(expiry_str)
            if expiry.tzinfo:
                expiry = expiry.replace(tzinfo=None)
            self._token_expiry = expiry - __import__("datetime").timedelta(minutes=5)
        self.logger.info(f"Token received, expires: {data.get('expirationDate')}")
        return self._token

    def get_url(self) -> str:
        return self.BASE_URL

    def get_params(self, route: Route, date: str) -> dict:
        origin_id = route.origin.ouigo_fr_id
        destination_id = route.destination.ouigo_fr_id

        if not origin_id:
            raise ValueError(f"No ouigo_fr_id for {route.origin.name}")
        if not destination_id:
            raise ValueError(f"No ouigo_fr_id for {route.destination.name}")

        return {
            "origin": origin_id,
            "destination": destination_id,
            "outbound_date": date,
            "passengers": [{"discount_cards": [], "disability_type": "NH", "type": "A"}],
            "with_ttt": False
        }

    def fetch(self, url: str, params: dict = None, headers: dict = None) -> requests.Response:
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                token = self._get_token()
                auth_headers = {
                    **self.HEADERS,
                    "Authorization": f"Bearer {token}"
                }
                self.logger.info(f"HTTP POST {url} (attempt {attempt}/{self.MAX_RETRIES})")
                response = self.session.post(
                    url,
                    json=params,
                    headers=auth_headers,
                    timeout=self.REQUEST_TIMEOUT,
                )
                response.raise_for_status()
                self.logger.info(f"HTTP {response.status_code} – {len(response.content)} bytes")
                return response

            except requests.exceptions.Timeout:
                self.logger.warning(f"Timeout on attempt {attempt}")
            except requests.exceptions.HTTPError as e:
                self.logger.warning(f"HTTP error {e.response.status_code} on attempt {attempt}")
                if e.response.status_code == 401:
                    self._token = None  # reset token
                if e.response.status_code in (400, 404):
                    raise
            except requests.exceptions.ConnectionError:
                self.logger.warning(f"Connection error on attempt {attempt}")
            except Exception as e:
                self.logger.warning(f"Unknown error on attempt {attempt}: {e}")

            if attempt < self.MAX_RETRIES:
                time.sleep(self.RETRY_DELAY)

        raise Exception(f"All {self.MAX_RETRIES} attempts failed for {url}")

    def parse(self, response: requests.Response, route: Route = None) -> list[dict]:
        records = []
        try:
            data = response.json()
        except Exception as e:
            self.logger.error(f"JSON parse error: {e}")
            return records

        journeys = data.get("outbound", [])
        self.logger.info(f"{len(journeys)} connections in API response")

        for j in journeys:
            try:
                record = self._parse_journey(j, route)
                if record:
                    records.append(record)
            except Exception as e:
                self.logger.warning(f"Parse error: {e}")
                continue

        self.logger.info(f"{len(records)} Ouigo connections parsed")
        return records

    def _parse_journey(self, j: dict, route: Route = None) -> dict | None:
        if j.get("full"):
            return None

        dep_str = j.get("departure_station", {}).get("departure_timestamp", "")
        arr_str = j.get("arrival_station", {}).get("arrival_timestamp", "")
        if not dep_str or not arr_str:
            return None

        departure_time = datetime.fromisoformat(dep_str).replace(tzinfo=None)
        arrival_time = datetime.fromisoformat(arr_str).replace(tzinfo=None)

        price = j.get("price")
        train_number = j.get("service_name")
        is_promo = j.get("is_promo", False)

        return {
            "operator":        self.OPERATOR_NAME,
            "origin":          route.origin.name if route else "unknown",
            "destination":     route.destination.name if route else "unknown",
            "origin_id":       str(route.origin.ouigo_fr_id) if route else None,
            "destination_id":  str(route.destination.ouigo_fr_id) if route else None,
            "departure_time":  departure_time,
            "arrival_time":    arrival_time,
            "price_eur":       float(price) if price is not None else None,
            "seats_available": j.get("remaining_seats"),
            "fare_class":      "OUIGO_FULL" if is_promo else "OUIGO_BASE",
            "offer_type":      "promo" if is_promo else "standard",
            "train_number":    train_number,
        }


# ──────────────────────────────────────────────
# DIRECT TEST
# ──────────────────────────────────────────────

if __name__ == "__main__":
    from datetime import timedelta
    from dotenv import load_dotenv
    from config.routes import get_routes_for_operator, BOOKING_HORIZONS

    load_dotenv()

    print("Ouigo France Crawler Test")
    print("=" * 50)

    crawler = OuigoFrCrawler()
    routes = get_routes_for_operator("ouigo_fr")

    print(f"{len(routes)} Ouigo routes, {len(BOOKING_HORIZONS)} horizons\n")

    for route in routes[:1]:
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
                    print(f"   {len(valid)} trains found:")
                    for r in valid[:3]:
                        seats = r.get("seats_available")
                        seats_str = str(seats) if seats is not None else "-"
                        print(
                            f"   {r['departure_time'].strftime('%H:%M')} -> "
                            f"{r['arrival_time'].strftime('%H:%M')} | "
                            f"{r['price_eur']:.2f} EUR | "
                            f"{r.get('fare_class', '-')} | "
                            f"train: {r.get('train_number', '-')}"
                        )
                    if len(valid) > 3:
                        print(f"   ... and {len(valid) - 3} more")
                else:
                    print(f"   No connections found")

            except Exception as e:
                print(f"   ERROR: {e}")

            print()