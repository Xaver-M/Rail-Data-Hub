"""
Italo Crawler - Price and availability data via api-biglietti.italotreno.com.

Uses Playwright to bootstrap a browser session and extract the BIGSessionToken,
which is then used for all subsequent API requests.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import time
import requests
from datetime import datetime, timedelta

from crawlers.base.base_crawler import BaseCrawler
from crawlers.italo.italo_session import ItaloSessionManager
from config.routes import Route


class ItaloCrawler(BaseCrawler):

    OPERATOR_NAME = "italo"
    API_BASE = "https://api-biglietti.italotreno.com/api/v1"

    POLL_MAX_ATTEMPTS = 15
    POLL_DEFAULT_WAIT = 1.0

    def __init__(self):
        super().__init__()
        self.session_manager = ItaloSessionManager()
        self.session_manager.bootstrap()
        self.session = self.session_manager.session
        self.headers = self.session_manager.headers
        self.logger.info("Italo crawler ready")

    def get_url(self) -> str:
        return f"{self.API_BASE}/booking"

    def get_params(self, route: Route, date: str) -> dict:
        if not route.origin.italo_id:
            raise ValueError(f"No italo_id for {route.origin.name}")
        if not route.destination.italo_id:
            raise ValueError(f"No italo_id for {route.destination.name}")

        return {
            "isRoundTrip": False,
            "departureStation": route.origin.italo_id,
            "arrivalStation": route.destination.italo_id,
            "departureDate": date,
            "adultPassengers": 1,
            "childPassengers": 0,
            "seniorPassengers": 0,
            "youngPassengers": 0,
            "culture": "en-US",
            "employeeOffer": None,
            "hasPet": False,
            "passengersAges": None,
            "portalType": "B2C",
            "promoCode": "",
            "showBestPrices": True,
            "showPrivateOffers": False,
        }

    def fetch(self, url: str, params: dict = None, headers: dict = None) -> requests.Response:
        merged_headers = dict(self.headers)
        if headers:
            merged_headers.update(headers)

        response = self.session.post(
            url,
            json=params or {},
            headers=merged_headers,
            timeout=self.REQUEST_TIMEOUT,
        )
        response.raise_for_status()

        booking_data = response.json()
        operation_id = booking_data.get("operationId")

        if not operation_id:
            self.logger.warning("No operationId in booking response")
            return response

        return self._poll(operation_id, merged_headers)

    def _poll(self, operation_id: str, headers: dict) -> requests.Response:
        poll_url = f"{self.API_BASE}/booking/status/{operation_id}"

        for attempt in range(1, self.POLL_MAX_ATTEMPTS + 1):
            poll_response = self.session.get(
                poll_url,
                headers=headers,
                timeout=self.REQUEST_TIMEOUT,
            )

            if poll_response.status_code == 200:
                self.logger.info(f"Polling complete after {attempt} attempt(s)")
                return poll_response

            if poll_response.status_code == 202:
                try:
                    retry_after = poll_response.json().get("retryAfter", 1000)
                except Exception:
                    retry_after = 1000
                time.sleep(retry_after / 1000)
                continue

            self.logger.warning(f"Unexpected poll status {poll_response.status_code}")
            time.sleep(self.POLL_DEFAULT_WAIT)

        self.logger.warning(f"Polling timeout after {self.POLL_MAX_ATTEMPTS} attempts")
        return poll_response

    def parse(self, response: requests.Response, route: Route = None) -> list[dict]:
        records = []

        try:
            result = response.json()
        except Exception as e:
            self.logger.error(f"JSON parse error: {e}")
            return records

        solutions = []
        for trip in result.get("trips", []):
            solutions.extend(trip.get("travelSolutions", []))

        self.logger.info(f"{len(solutions)} solutions found")

        for solution in solutions:
            for journey in solution.get("journeys", []):
                for segment in journey.get("segments", []):
                    fares = segment.get("fares", [])
                    if not fares:
                        continue

                    try:
                        cheapest = min(
                            fares,
                            key=lambda f: f["paxFares"][0]["singlePaxFarePrice"],
                        )
                    except Exception:
                        continue

                    pax_fare = cheapest["paxFares"][0]

                    try:
                        departure_time = datetime.fromisoformat(segment["std"])
                        arrival_time = datetime.fromisoformat(segment["sta"])
                    except Exception:
                        continue

                    records.append({
                        "operator":        self.OPERATOR_NAME,
                        "origin":          route.origin.name if route else "unknown",
                        "destination":     route.destination.name if route else "unknown",
                        "origin_id":       route.origin.italo_id if route else None,
                        "destination_id":  route.destination.italo_id if route else None,
                        "departure_time":  departure_time,
                        "arrival_time":    arrival_time,
                        "price_eur":       float(pax_fare["singlePaxFarePrice"]),
                        "seats_available": cheapest.get("availableCount"),
                        "travel_class":    cheapest.get("productClass"),
                        "train_number":    segment.get("trainNumber"),
                        "is_direct":       solution.get("numberOfChanges", 0) == 0,
                    })

        self.logger.info(f"{len(records)} Italo trains found")
        return records

    def close(self):
        self.session_manager.close()


# ──────────────────────────────────────────────
# DIRECT TEST
# ──────────────────────────────────────────────

if __name__ == "__main__":
    from dotenv import load_dotenv
    from config.routes import get_routes_for_operator, BOOKING_HORIZONS

    load_dotenv()

    print("Italo Crawler Test")
    print("=" * 50)

    crawler = ItaloCrawler()
    routes = get_routes_for_operator("italo")

    print(f"{len(routes)} Italo routes, {len(BOOKING_HORIZONS)} horizons\n")

    for route in routes[:1]:
        for horizon in [1]:
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
                        print(
                            f"   {r['departure_time'].strftime('%H:%M')} → "
                            f"{r['arrival_time'].strftime('%H:%M')} | "
                            f"{r['price_eur']:.2f} EUR | "
                            f"{str(seats) if seats is not None else '-'} seats | "
                            f"class: {r.get('travel_class')} | "
                            f"train: {r.get('train_number')}"
                        )
                    if len(valid) > 3:
                        print(f"   ... and {len(valid) - 3} more")
                else:
                    print("   No trains found")

            except Exception as e:
                print(f"   ERROR: {e}")

            print()

    crawler.close()