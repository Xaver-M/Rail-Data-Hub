"""
BaseCrawler – Shared base class for all operator crawlers.
Each operator-specific crawler inherits from this class and implements
the abstract methods get_url(), get_params() and parse().
"""

import time
import os
from abc import ABC, abstractmethod
from datetime import datetime, timezone, timedelta

import requests
from loguru import logger
from dotenv import load_dotenv

load_dotenv()


class BaseCrawler(ABC):
    """
    Abstract base class for all operator crawlers.

    Shared logic:
    - HTTP requests with timeout, headers and automatic retry
    - Logging every action via loguru
    - Database connection via psycopg2
    - Data validation
    - Unified run() flow

    Every operator crawler must implement:
    - get_url()
    - get_params(route, date)
    - parse(response, route)
    """

    MAX_RETRIES = 3
    RETRY_DELAY = 5
    REQUEST_TIMEOUT = 30
    OPERATOR_NAME = "base"

    def __init__(self):
        self._setup_logging()
        self.session = self._create_session()
        self.db_conn = None
        self.logger.info(f"{self.OPERATOR_NAME} crawler initialized")

    # ──────────────────────────────────────────────
    # SETUP
    # ──────────────────────────────────────────────


    def _setup_logging(self):
        self.logger = logger.bind(operator=self.OPERATOR_NAME)
        logger.remove()
        # Console handler without operator field
        logger.add(
            lambda msg: print(msg, end=""),
            level="INFO",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {message}",
            colorize=True,
        )
        # File handler with operator field
        os.makedirs("logs", exist_ok=True)
        logger.add(
            f"logs/{self.OPERATOR_NAME}_crawler.log",
            rotation="1 day",
            retention="30 days",
            level="INFO",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {extra[operator]} | {message}",
            filter=lambda record: "operator" in record["extra"],
        )

    def _create_session(self) -> requests.Session:
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (compatible; RailDataHub/1.0; research)",
            "Accept": "application/json, text/html",
            "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
        })
        return session

    def _connect_db(self):
        try:
            import psycopg2
            self.db_conn = psycopg2.connect(
                host=os.getenv("DB_HOST", "localhost"),
                port=os.getenv("DB_PORT", "5432"),
                dbname=os.getenv("DB_NAME", "rail_data"),
                user=os.getenv("DB_USER", "rail_user"),
                password=os.getenv("DB_PASSWORD"),
            )
            self.logger.info("Database connection established")
        except Exception as e:
            self.logger.error(f"Database connection failed: {e}")
            raise

    def _close_db(self):
        if self.db_conn and not self.db_conn.closed:
            self.db_conn.close()
            self.logger.info("Database connection closed")

    # ──────────────────────────────────────────────
    # HTTP
    # ──────────────────────────────────────────────


    def fetch(self, url: str, params: dict = None, headers: dict = None) -> requests.Response:
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                self.logger.info(f"HTTP GET {url} (attempt {attempt}/{self.MAX_RETRIES})")

                response = self.session.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=self.REQUEST_TIMEOUT,
                )
                response.raise_for_status()

                self.logger.info(f"HTTP {response.status_code} – {len(response.content)} bytes")
                return response

            except requests.exceptions.Timeout:
                self.logger.warning(f"Timeout on attempt {attempt}")
            except requests.exceptions.HTTPError as e:
                self.logger.warning(f"HTTP error {e.response.status_code} on attempt {attempt}")
                if e.response.status_code in (400, 404):
                    raise
            except requests.exceptions.ConnectionError:
                self.logger.warning(f"Connection error on attempt {attempt}")
            except Exception as e:
                self.logger.warning(f"Unknown error on attempt {attempt}: {e}")

            if attempt < self.MAX_RETRIES:
                self.logger.info(f"Waiting {self.RETRY_DELAY}s before next attempt...")
                time.sleep(self.RETRY_DELAY)

        raise Exception(f"All {self.MAX_RETRIES} attempts failed for {url}")

    # ──────────────────────────────────────────────
    # VALIDATION
    # ──────────────────────────────────────────────


    def validate(self, records: list[dict]) -> list[dict]:
        valid = []
        for record in records:
            if self._is_valid(record):
                valid.append(record)
            else:
                self.logger.warning(f"Invalid record skipped: {record}")

        self.logger.info(f"Validation: {len(valid)}/{len(records)} records valid")
        return valid

    def _is_valid(self, record: dict) -> bool:
        required_fields = ["operator", "origin", "destination", "departure_time", "price_eur"]

        for field in required_fields:
            if field not in record or record[field] is None:
                self.logger.warning(f"Required field missing: {field}")
                return False

        if not isinstance(record["price_eur"], (int, float)) or record["price_eur"] <= 0:
            self.logger.warning(f"Invalid price: {record['price_eur']}")
            return False

        if record["price_eur"] > 2000:
            self.logger.warning(f"Suspiciously high price: {record['price_eur']}€")
            return False

        return True

    # ──────────────────────────────────────────────
    # DATABASE
    # ──────────────────────────────────────────────


    def save(self, records: list[dict]) -> int:
        if not records:
            self.logger.info("No records to save")
            return 0

        saved = 0
        cursor = self.db_conn.cursor()

        try:
            for record in records:
                # Default fields not provided by all crawlers to None
                record.setdefault("travel_class",  None)
                record.setdefault("train_number",  None)
                record.setdefault("is_direct",     None)

                cursor.execute("""
                    INSERT INTO price_observations (
                        collected_at,
                        operator,
                        origin_name,
                        destination_name,
                        origin_id,
                        destination_id,
                        departure_at,
                        arrival_at,
                        price_eur,
                        fare_class,
                        seats_available,
                        booking_horizon_days,
                        route_id,
                        train_number,
                        is_direct
                    ) VALUES (
                        NOW(),
                        %(operator)s,
                        %(origin)s,
                        %(destination)s,
                        %(origin_id)s,
                        %(destination_id)s,
                        %(departure_time)s,
                        %(arrival_time)s,
                        %(price_eur)s,
                        %(travel_class)s,
                        %(seats_available)s,
                        %(booking_horizon_days)s,
                        %(route_id)s,
                        %(train_number)s,
                        %(is_direct)s
                    )
                    ON CONFLICT DO NOTHING
                """, record)
                saved += 1

            self.db_conn.commit()
            self.logger.info(f"{saved} records saved to database")

        except Exception as e:
            self.db_conn.rollback()
            self.logger.error(f"Error saving records: {e}")
            raise
        finally:
            cursor.close()

        return saved

    def log_run(self, status: str, records_written: int, error_msg: str = None):
        cursor = self.db_conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO crawler_logs (run_at, operator, status, records_written, error_msg)
                VALUES (NOW(), %s, %s, %s, %s)
            """, (self.OPERATOR_NAME, status, records_written, error_msg))
            self.db_conn.commit()
        except Exception as e:
            self.logger.error(f"Error writing crawler log: {e}")
        finally:
            cursor.close()

    # ──────────────────────────────────────────────
    # MAIN FLOW
    # ──────────────────────────────────────────────

    def run(self, routes: list, horizons: list[int]):
        """
        Main flow – called by APScheduler.

        For each route × horizon:
        1. Build parameters
        2. Send HTTP request
        3. Parse response
        4. Validate
        5. Save
        6. Log run

        Args:
            routes:   List of Route objects from config/routes.py
            horizons: List of booking horizons in days, e.g. [1, 2, 3, 7, 14, 30, 90]
        """
        self.logger.info(
            f"Crawler started – {len(routes)} routes, {len(horizons)} horizons"
        )
        start_time = datetime.now(timezone.utc)
        total_saved = 0
        errors = 0

        try:
            self._connect_db()

            for route in routes:
                # Skip routes not served by this operator
                if self.OPERATOR_NAME not in route.operators:
                    continue

                for horizon in horizons:
                    date = (datetime.now() + timedelta(days=horizon)).strftime("%Y-%m-%d")
                    try:
                        # 1. URL and parameters
                        url = self.get_url()
                        params = self.get_params(route, date)

                        # 2. HTTP request
                        response = self.fetch(url, params)

                        # 3. Parse
                        records = self.parse(response, route)

                        # 4. Add booking horizon to each record
                        for r in records:
                            r["booking_horizon_days"] = horizon
                            r["route_id"] = route.route_id

                        # 5. Validate
                        valid_records = self.validate(records)

                        # 6. Save
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
            self.logger.error(f"Critical error in crawler: {e}")
            self.log_run("error", total_saved, str(e))
            raise

        finally:
            self._close_db()

        duration = (datetime.now(timezone.utc) - start_time).seconds
        self.logger.info(
            f"Crawler finished – {total_saved} records saved, "
            f"{errors} errors, {duration}s runtime"
        )

    # ──────────────────────────────────────────────
    # ABSTRACT METHODS – must be implemented
    # ──────────────────────────────────────────────

    @abstractmethod
    def get_url(self) -> str:
        """Returns the operator's API URL."""
        pass

    @abstractmethod
    def get_params(self, route, date: str) -> dict:
        """
        Returns query parameters for a search request.

        Args:
            route: Route object from config/routes.py
            date:  Date in YYYY-MM-DD format
        """
        pass

    @abstractmethod
    def parse(self, response: requests.Response, route=None) -> list[dict]:
        """
        Processes the raw response and returns a list of records.

        Required fields per record:
            operator        str      e.g. "flixtrain"
            origin          str      e.g. "Stuttgart Hbf"
            destination     str      e.g. "Berlin Hbf"
            departure_time  datetime
            arrival_time    datetime
            price_eur       float    e.g. 24.49
            origin_id       str      operator-specific ID (optional)
            destination_id  str      operator-specific ID (optional)
            seats_available int      None if unknown
        """
        pass