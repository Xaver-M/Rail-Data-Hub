"""
BaseCrawler – Gemeinsame Basisklasse für alle Operator-Crawler
Jeder Operator-spezifische Crawler erbt von dieser Klasse und implementiert
die abstrakten Methoden get_url(), get_params() und parse().
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
    Abstrakte Basisklasse für alle Operator-Crawler.

    Gemeinsame Logik:
    - HTTP-Anfragen mit Timeout, Headers und automatischem Retry
    - Logging jeder Aktion via loguru
    - Datenbankverbindung via psycopg2
    - Validierung der Daten
    - Einheitlicher run()-Ablauf

    Jeder Operator-Crawler muss implementieren:
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
        self.logger.info(f"{self.OPERATOR_NAME} Crawler initialisiert")

    # ──────────────────────────────────────────────
    # SETUP
    # ──────────────────────────────────────────────

    def _setup_logging(self):
        self.logger = logger.bind(operator=self.OPERATOR_NAME)
        # Standard-Console-Handler entfernen (kennt {extra[operator]} nicht)
        logger.remove()
        # Console ohne operator-Feld
        logger.add(
            lambda msg: print(msg, end=""),
            level="INFO",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {message}",
            colorize=True,
        )
        # Datei-Handler mit operator-Feld
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
            self.logger.info("Datenbankverbindung hergestellt")
        except Exception as e:
            self.logger.error(f"Datenbankverbindung fehlgeschlagen: {e}")
            raise

    def _close_db(self):
        if self.db_conn and not self.db_conn.closed:
            self.db_conn.close()
            self.logger.info("Datenbankverbindung geschlossen")

    # ──────────────────────────────────────────────
    # HTTP
    # ──────────────────────────────────────────────

    def fetch(self, url: str, params: dict = None, headers: dict = None) -> requests.Response:
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                self.logger.info(f"HTTP GET {url} (Versuch {attempt}/{self.MAX_RETRIES})")

                response = self.session.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=self.REQUEST_TIMEOUT,
                )
                response.raise_for_status()

                self.logger.info(f"HTTP {response.status_code} – {len(response.content)} Bytes")
                return response

            except requests.exceptions.Timeout:
                self.logger.warning(f"Timeout bei Versuch {attempt}")
            except requests.exceptions.HTTPError as e:
                self.logger.warning(f"HTTP Fehler {e.response.status_code} bei Versuch {attempt}")
                if e.response.status_code in (400, 404):
                    raise
            except requests.exceptions.ConnectionError:
                self.logger.warning(f"Verbindungsfehler bei Versuch {attempt}")
            except Exception as e:
                self.logger.warning(f"Unbekannter Fehler bei Versuch {attempt}: {e}")

            if attempt < self.MAX_RETRIES:
                self.logger.info(f"Warte {self.RETRY_DELAY}s vor nächstem Versuch...")
                time.sleep(self.RETRY_DELAY)

        raise Exception(f"Alle {self.MAX_RETRIES} Versuche für {url} fehlgeschlagen")

    # ──────────────────────────────────────────────
    # VALIDIERUNG
    # ──────────────────────────────────────────────

    def validate(self, records: list[dict]) -> list[dict]:
        valid = []
        for record in records:
            if self._is_valid(record):
                valid.append(record)
            else:
                self.logger.warning(f"Ungültiger Datensatz übersprungen: {record}")

        self.logger.info(f"Validierung: {len(valid)}/{len(records)} Datensätze valide")
        return valid

    def _is_valid(self, record: dict) -> bool:
        required_fields = ["operator", "origin", "destination", "departure_time", "price_eur"]

        for field in required_fields:
            if field not in record or record[field] is None:
                self.logger.warning(f"Pflichtfeld fehlt: {field}")
                return False

        if not isinstance(record["price_eur"], (int, float)) or record["price_eur"] <= 0:
            self.logger.warning(f"Ungültiger Preis: {record['price_eur']}")
            return False

        if record["price_eur"] > 2000:
            self.logger.warning(f"Verdächtig hoher Preis: {record['price_eur']}€")
            return False

        return True

    # ──────────────────────────────────────────────
    # DATENBANK
    # ──────────────────────────────────────────────

    def save(self, records: list[dict]) -> int:
        if not records:
            self.logger.info("Keine Datensätze zu speichern")
            return 0

        saved = 0
        cursor = self.db_conn.cursor()

        try:
            for record in records:
                # Felder die nicht alle Crawler liefern auf None defaulten
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
            self.logger.info(f"{saved} Datensätze in Datenbank gespeichert")

        except Exception as e:
            self.db_conn.rollback()
            self.logger.error(f"Fehler beim Speichern: {e}")
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
            self.logger.error(f"Fehler beim Schreiben des Crawler-Logs: {e}")
        finally:
            cursor.close()

    # ──────────────────────────────────────────────
    # HAUPTABLAUF
    # ──────────────────────────────────────────────

    def run(self, routes: list, horizons: list[int]):
        """
        Hauptablauf – wird von APScheduler aufgerufen.

        Ablauf für jede Route × Horizont:
        1. Parameter erstellen
        2. HTTP-Anfrage senden
        3. Antwort parsen
        4. Validieren
        5. Speichern
        6. Lauf loggen

        Args:
            routes:   Liste von Route-Objekten aus config/routes.py
            horizons: Liste von Buchungshorizonten in Tagen
                      z.B. [1, 2, 3, 7, 14, 30, 90]
        """
        self.logger.info(
            f"Crawler gestartet – {len(routes)} Routen, {len(horizons)} Horizonte"
        )
        start_time = datetime.now(timezone.utc)
        total_saved = 0
        errors = 0

        try:
            self._connect_db()

            for route in routes:
                # Nur Routen die dieser Operator bedient
                if self.OPERATOR_NAME not in route.operators:
                    continue

                for horizon in horizons:
                    date = (datetime.now() + timedelta(days=horizon)).strftime("%Y-%m-%d")
                    try:
                        # 1. URL und Parameter
                        url = self.get_url()
                        params = self.get_params(route, date)

                        # 2. HTTP-Anfrage
                        response = self.fetch(url, params)

                        # 3. Parsen
                        records = self.parse(response, route)

                        # 4. Buchungshorizont zu jedem Record hinzufügen
                        for r in records:
                            r["booking_horizon_days"] = horizon
                            r["route_id"] = route.route_id

                        # 5. Validieren
                        valid_records = self.validate(records)

                        # 6. Speichern
                        saved = self.save(valid_records)
                        total_saved += saved

                        self.logger.info(
                            f"{route.description} +{horizon}d: {saved} gespeichert"
                        )

                    except Exception as e:
                        errors += 1
                        self.logger.error(
                            f"Fehler bei {route.description} +{horizon}d: {e}"
                        )
                        continue

            status = "success" if errors == 0 else "partial_error"
            self.log_run(status, total_saved)

        except Exception as e:
            self.logger.error(f"Kritischer Fehler im Crawler: {e}")
            self.log_run("error", total_saved, str(e))
            raise

        finally:
            self._close_db()

        duration = (datetime.now(timezone.utc) - start_time).seconds
        self.logger.info(
            f"Crawler beendet – {total_saved} Datensätze gespeichert, "
            f"{errors} Fehler, {duration}s Laufzeit"
        )

    # ──────────────────────────────────────────────
    # ABSTRAKTE METHODEN – müssen implementiert werden
    # ──────────────────────────────────────────────

    @abstractmethod
    def get_url(self) -> str:
        """Gibt die API-URL des Operators zurück."""
        pass

    @abstractmethod
    def get_params(self, route, date: str) -> dict:
        """
        Gibt die Query-Parameter für eine Suchanfrage zurück.

        Args:
            route: Route-Objekt aus config/routes.py
            date:  Datum im Format YYYY-MM-DD
        """
        pass

    @abstractmethod
    def parse(self, response: requests.Response, route=None) -> list[dict]:
        """
        Verarbeitet die Rohantwort und gibt eine Liste von Datensätzen zurück.

        Pflichtfelder pro Datensatz:
            operator        str      z.B. "flixtrain"
            origin          str      z.B. "Stuttgart Hbf"
            destination     str      z.B. "Berlin Hbf"
            departure_time  datetime
            arrival_time    datetime
            price_eur       float    z.B. 24.49
            origin_id       str      operator-spez. ID (optional)
            destination_id  str      operator-spez. ID (optional)
            seats_available int      None wenn unbekannt
        """
        pass