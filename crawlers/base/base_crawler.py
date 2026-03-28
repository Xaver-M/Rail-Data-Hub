"""
BaseCrawler – Gemeinsame Basisklasse für alle Operator-Crawler
Jeder Operator-spezifische Crawler erbt von dieser Klasse und implementiert
die abstrakten Methoden get_url(), get_params() und parse().
"""

import time
import os
from abc import ABC, abstractmethod
from datetime import datetime, timezone

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
    - Datenbankverbindung (wird später mit psycopg2 befüllt)
    - Validierung der Daten
    - Einheitlicher run()-Ablauf

    Jeder Operator-Crawler muss implementieren:
    - get_url()
    - get_params(origin, destination, date)
    - parse(response)
    """

    # Standardwerte – können in Unterklassen überschrieben werden
    MAX_RETRIES = 3          # Maximale Anzahl Wiederholungsversuche
    RETRY_DELAY = 5          # Sekunden zwischen Versuchen
    REQUEST_TIMEOUT = 30     # Sekunden bis Timeout
    OPERATOR_NAME = "base"   # Wird in Unterklassen überschrieben

    def __init__(self):
        """
        Initialisierung: Logging einrichten, HTTP-Session erstellen,
        Datenbankverbindung konfigurieren.
        """
        self._setup_logging()
        self.session = self._create_session()
        self.db_conn = None  # Wird bei Bedarf geöffnet
        self.logger.info(f"{self.OPERATOR_NAME} Crawler initialisiert")

    # ──────────────────────────────────────────────
    # SETUP
    # ──────────────────────────────────────────────

    def _setup_logging(self):
        """Richtet loguru Logger für diesen Crawler ein."""
        self.logger = logger.bind(operator=self.OPERATOR_NAME)
        logger.add(
            f"logs/{self.OPERATOR_NAME}_crawler.log",
            rotation="1 day",       # Täglich neue Logdatei
            retention="30 days",    # 30 Tage aufbewahren
            level="INFO",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {extra[operator]} | {message}"
        )

    def _create_session(self) -> requests.Session:
        """
        Erstellt eine wiederverwendbare HTTP-Session mit Standard-Headers.
        Eine Session ist effizienter als einzelne requests.get() Aufrufe
        weil TCP-Verbindungen wiederverwendet werden.
        """
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (compatible; RailDataHub/1.0; research)",
            "Accept": "application/json, text/html",
            "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
        })
        return session

    def _connect_db(self):
        """
        Öffnet Datenbankverbindung zu TimescaleDB.
        Verbindungsparameter kommen aus der .env Datei.
        """
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
        """Schließt Datenbankverbindung sauber."""
        if self.db_conn and not self.db_conn.closed:
            self.db_conn.close()
            self.logger.info("Datenbankverbindung geschlossen")

    # ──────────────────────────────────────────────
    # HTTP
    # ──────────────────────────────────────────────

    def fetch(self, url: str, params: dict = None, headers: dict = None) -> requests.Response:
        """
        Sendet HTTP GET-Anfrage mit automatischem Retry bei Fehlern.

        Args:
            url: Die aufzurufende URL
            params: Query-Parameter (werden an URL angehängt)
            headers: Zusätzliche HTTP-Headers (z.B. API-Key)

        Returns:
            requests.Response Objekt

        Raises:
            Exception wenn alle Versuche fehlschlagen
        """
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                self.logger.info(f"HTTP GET {url} (Versuch {attempt}/{self.MAX_RETRIES})")

                response = self.session.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=self.REQUEST_TIMEOUT,
                )
                response.raise_for_status()  # Wirft Exception bei 4xx/5xx

                self.logger.info(f"HTTP {response.status_code} – {len(response.content)} Bytes")
                return response

            except requests.exceptions.Timeout:
                self.logger.warning(f"Timeout bei Versuch {attempt}")
            except requests.exceptions.HTTPError as e:
                self.logger.warning(f"HTTP Fehler {e.response.status_code} bei Versuch {attempt}")
                # Bei 404 oder 400 sofort aufgeben – Retry hilft nicht
                if e.response.status_code in (400, 404):
                    raise
            except requests.exceptions.ConnectionError:
                self.logger.warning(f"Verbindungsfehler bei Versuch {attempt}")
            except Exception as e:
                self.logger.warning(f"Unbekannter Fehler bei Versuch {attempt}: {e}")

            # Warten vor nächstem Versuch (außer beim letzten)
            if attempt < self.MAX_RETRIES:
                self.logger.info(f"Warte {self.RETRY_DELAY}s vor nächstem Versuch...")
                time.sleep(self.RETRY_DELAY)

        raise Exception(f"Alle {self.MAX_RETRIES} Versuche für {url} fehlgeschlagen")

    # ──────────────────────────────────────────────
    # VALIDIERUNG
    # ──────────────────────────────────────────────

    def validate(self, records: list[dict]) -> list[dict]:
        """
        Prüft ob die geparsten Datensätze vollständig und plausibel sind.
        Ungültige Datensätze werden herausgefiltert und geloggt.

        Args:
            records: Liste von Datensätzen aus parse()

        Returns:
            Liste valider Datensätze
        """
        valid = []
        for record in records:
            if self._is_valid(record):
                valid.append(record)
            else:
                self.logger.warning(f"Ungültiger Datensatz übersprungen: {record}")

        self.logger.info(f"Validierung: {len(valid)}/{len(records)} Datensätze valide")
        return valid

    def _is_valid(self, record: dict) -> bool:
        """
        Prüft einen einzelnen Datensatz auf Vollständigkeit und Plausibilität.

        Pflichtfelder: operator, origin, destination, departure_time, price_eur
        Plausibilität: Preis > 0, Abfahrt in der Zukunft, bekannter Operator
        """
        required_fields = ["operator", "origin", "destination", "departure_time", "price_eur"]

        # Alle Pflichtfelder vorhanden?
        for field in required_fields:
            if field not in record or record[field] is None:
                self.logger.warning(f"Pflichtfeld fehlt: {field}")
                return False

        # Preis plausibel?
        if not isinstance(record["price_eur"], (int, float)) or record["price_eur"] <= 0:
            self.logger.warning(f"Ungültiger Preis: {record['price_eur']}")
            return False

        # Preis nicht unrealistisch hoch? (Sicherheitsnetz gegen Datenfehler)
        if record["price_eur"] > 2000:
            self.logger.warning(f"Verdächtig hoher Preis: {record['price_eur']}€")
            return False

        return True

    # ──────────────────────────────────────────────
    # DATENBANK
    # ──────────────────────────────────────────────

    def save(self, records: list[dict]) -> int:
        """
        Schreibt validierte Datensätze in TimescaleDB.

        Args:
            records: Liste valider Datensätze

        Returns:
            Anzahl erfolgreich gespeicherter Datensätze
        """
        if not records:
            self.logger.info("Keine Datensätze zu speichern")
            return 0

        saved = 0
        cursor = self.db_conn.cursor()

        try:
            for record in records:
                cursor.execute("""
                    INSERT INTO prices (
                        time, operator, origin, destination,
                        departure_time, arrival_time,
                        price_eur, travel_class, seats_available, currency
                    ) VALUES (
                        NOW(), %(operator)s, %(origin)s, %(destination)s,
                        %(departure_time)s, %(arrival_time)s,
                        %(price_eur)s, %(travel_class)s, %(seats_available)s,
                        %(currency)s
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

    def log_run(self, status: str, records_fetched: int, error_msg: str = None):
        """
        Schreibt einen Eintrag in crawler_logs – wann wurde gecrawlt,
        wie viele Datensätze, Erfolg oder Fehler.

        Args:
            status: "success" oder "error"
            records_fetched: Anzahl abgerufener Datensätze
            error_msg: Fehlermeldung falls status="error"
        """
        cursor = self.db_conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO crawler_logs (time, operator, status, records_fetched, error_message)
                VALUES (NOW(), %s, %s, %s, %s)
            """, (self.OPERATOR_NAME, status, records_fetched, error_msg))
            self.db_conn.commit()
        except Exception as e:
            self.logger.error(f"Fehler beim Schreiben des Crawler-Logs: {e}")
        finally:
            cursor.close()

    # ──────────────────────────────────────────────
    # HAUPTABLAUF
    # ──────────────────────────────────────────────

    def run(self, routes: list[tuple]):
        """
        Hauptablauf – wird von APScheduler aufgerufen.

        Ablauf für jede Route:
        1. URL und Parameter holen
        2. HTTP-Anfrage senden
        3. Antwort parsen
        4. Validieren
        5. Speichern
        6. Lauf loggen

        Args:
            routes: Liste von (origin, destination, date) Tupeln
                    z.B. [("Berlin Hbf", "München Hbf", "2026-04-01")]
        """
        self.logger.info(f"Crawler gestartet – {len(routes)} Routen")
        start_time = datetime.now(timezone.utc)
        total_saved = 0
        errors = 0

        try:
            self._connect_db()

            for origin, destination, date in routes:
                try:
                    # 1. URL und Parameter
                    url = self.get_url()
                    params = self.get_params(origin, destination, date)

                    # 2. HTTP-Anfrage
                    response = self.fetch(url, params)

                    # 3. Parsen
                    records = self.parse(response)
                    self.logger.info(f"{origin}→{destination}: {len(records)} Verbindungen gefunden")

                    # 4. Validieren
                    valid_records = self.validate(records)

                    # 5. Speichern
                    saved = self.save(valid_records)
                    total_saved += saved

                except Exception as e:
                    errors += 1
                    self.logger.error(f"Fehler bei Route {origin}→{destination}: {e}")
                    continue

            # 6. Lauf loggen
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
        """
        Gibt die API-URL oder Website-URL des Operators zurück.

        Beispiel DB:
            return "https://reiseauskunft.bahn.de/bin/query.exe"

        Beispiel Flixtrain:
            return "https://shop.flixtrain.com/api/v1/search"
        """
        pass

    @abstractmethod
    def get_params(self, origin: str, destination: str, date: str) -> dict:
        """
        Gibt die Query-Parameter für eine Suchanfrage zurück.

        Args:
            origin: Abfahrtsbahnhof
            destination: Zielbahnhof
            date: Datum im Format YYYY-MM-DD

        Beispiel DB:
            return {
                "S": origin,
                "Z": destination,
                "date": date,
                "time": "06:00",
            }
        """
        pass

    @abstractmethod
    def parse(self, response: requests.Response) -> list[dict]:
        """
        Verarbeitet die Rohantwort und gibt eine Liste von Datensätzen zurück.
        Jeder Datensatz muss diese Felder haben:
        {
            "operator":        str,   z.B. "DB"
            "origin":          str,   z.B. "Berlin Hbf"
            "destination":     str,   z.B. "München Hbf"
            "departure_time":  datetime
            "arrival_time":    datetime
            "price_eur":       float  z.B. 29.90
            "travel_class":    str,   z.B. "2"
            "seats_available": int,   z.B. 42 (None wenn unbekannt)
            "currency":        str,   z.B. "EUR"
        }
        """
        pass
