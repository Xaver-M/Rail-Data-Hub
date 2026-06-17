"""
DB ParseBot Crawler – Deutsche Bahn prices via Parse.bot bahn.de scraper API.

Auth:    X-API-Key header (env: PARSE_API_KEY)
Rate:    Developer plan → capped at 4 req/min for safety.
Credits: 5,000/month ≈ 167/day → use DB_PARSEBOT_HORIZONS, not BOOKING_HORIZONS.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import json
import time
from collections import deque
from datetime import datetime, timedelta

import requests
from requests.models import Response
from dotenv import load_dotenv

from crawlers.base.base_crawler import BaseCrawler
from crawlers.db_parsebot.cache import FileCache
from config.routes import Route, get_routes_for_operator

load_dotenv()


class DBParseBotCrawler(BaseCrawler):

    OPERATOR_NAME = "db_parsebot"
    BASE_URL      = "https://api.parse.bot/scraper/49ba8b8c-c4c8-4861-a1e8-3e46e71c6656"
    TICKET_CLASS  = "2"
    _RATE_LIMIT   = 4  # max requests per 60 s

    # 9 time slots × 2 routes = 18 routes distributed across the day
    _TIME_SLOTS = ["06:00", "08:00", "10:00", "12:00", "14:00", "16:00", "18:00", "20:00", "22:00"]

    # Cache TTL by booking horizon
    _TTL_SHORT  = 120    # ≤2 days:  2 h  (near-term prices volatile)
    _TTL_MEDIUM = 1440   # 3-14 days: 24 h
    _TTL_LONG   = 2880   # >14 days: 48 h (far-future prices stable)

    def __init__(self):
        super().__init__()
        self.api_key = os.getenv("PARSE_API_KEY", "")
        if not self.api_key:
            raise ValueError("PARSE_API_KEY environment variable not set")
        self._request_times: deque = deque()

        # Precompute departure time per route (stable for lifetime of crawler)
        routes = get_routes_for_operator(self.OPERATOR_NAME)
        self._route_time: dict[str, str] = {
            r.route_id: self._TIME_SLOTS[min(i // 2, len(self._TIME_SLOTS) - 1)]
            for i, r in enumerate(routes)
        }
        self.logger.info(f"DB ParseBot Crawler ready ({len(routes)} routes)")

    # ──────────────────────────────────────────────
    # BaseCrawler interface
    # ──────────────────────────────────────────────

    def get_url(self) -> str:
        return f"{self.BASE_URL}/search_connections"

    def get_params(self, route: Route, date: str) -> dict:
        return {
            "origin":      route.origin.name,
            "destination": route.destination.name,
            "date":        date,
            "time":        self._route_time.get(route.route_id, "09:00"),
            "class":       self.TICKET_CLASS,
        }

    def parse(self, response: requests.Response, route: Route = None) -> list[dict]:
        records = []
        try:
            raw = response.json()
        except Exception as e:
            self.logger.error(f"JSON parse error: {e}")
            return records

        inner = raw.get("data", raw)
        if isinstance(inner, dict):
            items = inner.get("connections", [])
        elif isinstance(inner, list):
            items = inner
        else:
            items = []

        for item in items:
            try:
                record = self._parse_connection(item, route)
                if record:
                    records.append(record)
            except Exception as e:
                self.logger.warning(f"Parse error: {e}")

        self.logger.info(f"{len(items)} connections received, {len(records)} records parsed")
        return records

    # ──────────────────────────────────────────────
    # fetch() – cache layer + API key injection
    # ──────────────────────────────────────────────

    def fetch(self, url: str, params: dict = None, headers: dict = None) -> requests.Response:
        p = params or {}
        days_ahead = self._days_ahead(p.get("date", ""))
        cache = FileCache(ttl_minutes=self._ttl_for(days_ahead))
        key   = cache.make_key(url, p)

        hit = cache.get(key)
        if hit is not None:
            self.logger.info(f"Cache HIT  – {p.get('origin')} → {p.get('destination')} {p.get('date')}")
            return self._make_response(hit)

        self.logger.info(f"Cache MISS – {p.get('origin')} → {p.get('destination')} {p.get('date')}")
        self._rate_limit_wait()

        api_headers = {"X-API-Key": self.api_key, **(headers or {})}
        response = super().fetch(url, params, api_headers)
        cache.set(key, response.json())
        return response

    # ──────────────────────────────────────────────
    # Private helpers
    # ──────────────────────────────────────────────

    def _parse_connection(self, item: dict, route: Route = None) -> dict | None:
        # Price
        price_raw = item.get("totalPrice") or item.get("price")
        if price_raw is None:
            return None
        price_eur = float(price_raw["amount"]) if isinstance(price_raw, dict) else float(price_raw)
        if price_eur <= 0:
            return None

        # Times
        try:
            departure_time = datetime.fromisoformat(item["departure"])
            arrival_time   = datetime.fromisoformat(item["arrival"])
        except (KeyError, ValueError, TypeError):
            return None

        # Train info
        legs         = item.get("legs", [])
        transfers    = item.get("transfers", max(0, len(legs) - 1))
        train_number = " + ".join(
            n for leg in legs
            if (n := leg.get("train") or leg.get("category") or leg.get("name"))
        ) or "?"

        return {
            "operator":        self.OPERATOR_NAME,
            "origin":          route.origin.name if route else "",
            "destination":     route.destination.name if route else "",
            "origin_id":       None,
            "destination_id":  None,
            "departure_time":  departure_time,
            "arrival_time":    arrival_time,
            "price_eur":       price_eur,
            "travel_class":    self.TICKET_CLASS,
            "seats_available": None,
            "is_direct":       transfers == 0,
            "train_number":    train_number,
        }

    def _rate_limit_wait(self) -> None:
        now = time.time()
        while self._request_times and self._request_times[0] < now - 60.0:
            self._request_times.popleft()
        if len(self._request_times) >= self._RATE_LIMIT:
            sleep_for = 60.0 - (now - self._request_times[0]) + 0.1
            if sleep_for > 0:
                self.logger.info(f"Rate limiter: sleeping {sleep_for:.1f}s")
                time.sleep(sleep_for)
        self._request_times.append(time.time())

    @staticmethod
    def _days_ahead(date_str: str) -> int:
        try:
            return max(0, (datetime.strptime(date_str, "%Y-%m-%d").date() - datetime.now().date()).days)
        except (ValueError, TypeError):
            return 7

    @classmethod
    def _ttl_for(cls, days_ahead: int) -> int:
        if days_ahead <= 2:
            return cls._TTL_SHORT
        if days_ahead <= 14:
            return cls._TTL_MEDIUM
        return cls._TTL_LONG

    @staticmethod
    def _make_response(data: dict) -> Response:
        r = Response()
        r.status_code = 200
        r.encoding    = "utf-8"
        r._content    = json.dumps(data).encode("utf-8")
        return r


# ──────────────────────────────────────────────
# DIRECT TEST
# ──────────────────────────────────────────────

if __name__ == "__main__":
    from config.routes import get_routes_for_operator, DB_PARSEBOT_HORIZONS

    print("DB ParseBot Crawler Test")
    print("=" * 50)

    if not os.getenv("PARSE_API_KEY"):
        print("ERROR: PARSE_API_KEY not set")
        sys.exit(1)

    crawler = DBParseBotCrawler()
    routes  = get_routes_for_operator("db_parsebot")
    print(f"{len(routes)} routes, {len(DB_PARSEBOT_HORIZONS)} horizons {DB_PARSEBOT_HORIZONS}\n")

    for route in routes[:2]:
        for horizon in DB_PARSEBOT_HORIZONS[:3]:
            date = (datetime.now() + timedelta(days=horizon)).strftime("%Y-%m-%d")
            print(f"── {route.description} | +{horizon}d ({date})")
            try:
                response = crawler.fetch(crawler.get_url(), crawler.get_params(route, date))
                valid    = crawler.validate(crawler.parse(response, route))
                if valid:
                    direct = sum(1 for r in valid if r["is_direct"])
                    print(f"   {len(valid)} records ({direct} direkt, {len(valid)-direct} Umstieg)")
                    for r in valid[:3]:
                        tag = "direkt" if r["is_direct"] else "Umstieg"
                        print(f"   {r['departure_time'].strftime('%H:%M')} → "
                              f"{r['arrival_time'].strftime('%H:%M')} | "
                              f"{r['price_eur']:.2f} EUR | {r['train_number']} | {tag}")
                    if len(valid) > 3:
                        print(f"   ... und {len(valid) - 3} weitere")
                else:
                    print("   Keine Verbindungen gefunden")
            except Exception as e:
                print(f"   FEHLER: {e}")
            print()
