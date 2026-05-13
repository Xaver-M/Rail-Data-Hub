# crawlers/italo/italo_session.py

from playwright.sync_api import sync_playwright
import requests
import uuid


class ItaloSessionManager:

    BASE_URL = (
        "https://biglietti.italotreno.com/en"
    )

    API_BASE = (
        "https://api-biglietti.italotreno.com/api/v1"
    )

    def __init__(self):

        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

        self.session = requests.Session()

        self.token = None

        self.headers = {}

    def bootstrap(self):

        self.playwright = (
            sync_playwright().start()
        )

        self.browser = (
            self.playwright.chromium.launch(
                headless=False
            )
        )

        self.context = (
            self.browser.new_context()
        )

        self.page = (
            self.context.new_page()
        )

        self.page.goto(
            self.BASE_URL,
            wait_until="domcontentloaded",
            timeout=60000
        )

        self.page.wait_for_timeout(
            10000
        )

        cookies = (
            self.context.cookies()
        )

        for c in cookies:

            self.session.cookies.set(
                c["name"],
                c["value"]
            )

            if c["name"] == "BIGSessionToken":

                self.token = c["value"]

        if not self.token:

            raise Exception(
                "BIGSessionToken not found"
            )

        self.headers = {

            "Authorization":
                f"Bearer {self.token}",

            "Origin":
                "https://biglietti.italotreno.com",

            "Referer":
                "https://biglietti.italotreno.com/",

            "User-Agent": (
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/136.0.0.0 Safari/537.36"
            ),

            "Accept":
                "application/json, text/plain, */*",

            "Accept-Language":
                "en-US,en;q=0.9",

            "Content-Type":
                "application/json",

            # x-big-working-session-id wird NICHT mehr hier gesetzt.
            # Stattdessen erstellt ItaloCrawler.fetch() fuer jeden
            # Booking-Request eine eigene UUID und registriert sie
            # separat, damit der Server die Operation-IDs nicht
            # session-uebergreifend invalidiert.
        }

    def close(self):

        try:

            if self.browser:

                self.browser.close()

        except Exception:
            pass

        try:

            if self.playwright:

                self.playwright.stop()

        except Exception:
            pass
