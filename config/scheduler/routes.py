# config/routes.py
# Zentrale Routen-Konfiguration für Rail Data Hub
# Nur Routen mit mindestens 2 Anbietern (Wettbewerbsrouten)

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Station:
    name: str
    flixtrain_id: Optional[str] = None      # UUID für Flixtrain API
    trenitalia_id: Optional[int] = None     # Integer-ID für lefrecce.it
    italo_id: Optional[int] = None          # Integer-ID für Italo API
    db_id: Optional[str] = None             # HAFAS-ID für DB
    oebb_id: Optional[str] = None           # HAFAS-ID für ÖBB


@dataclass
class Route:
    origin: Station
    destination: Station
    operators: list[str]                    # Welche Anbieter diese Strecke bedienen
    description: str = ""                   # Kurzbeschreibung für Logs


# ─────────────────────────────────────────────────────────────
# STATIONEN
# ─────────────────────────────────────────────────────────────

BERLIN = Station(
    name="Berlin Hbf",
    flixtrain_id="40d8f682-8646-11e6-9066-549f350fcb0c",
    db_id="8011160",
)

HAMBURG = Station(
    name="Hamburg Hbf",
    flixtrain_id="40d91e53-8646-11e6-9066-549f350fcb0c",
    db_id="8002549",
)

MÜNCHEN = Station(
    name="München Hbf",
    flixtrain_id="40d8f682-8646-11e6-9066-549f350fcb0c",  # TODO: verifizieren
    db_id="8000261",
)

FRANKFURT = Station(
    name="Frankfurt(Main)Hbf",
    db_id="8000105",
)

KÖLN = Station(
    name="Köln Hbf",
    db_id="8000207",
)

WIEN = Station(
    name="Wien Hbf",
    db_id="8100003",
    oebb_id="1190100",
)

MILANO = Station(
    name="Milano Centrale",
    trenitalia_id=830001700,
)

ROMA = Station(
    name="Roma Termini",
    trenitalia_id=830008409,
)

NAPOLI = Station(
    name="Napoli Centrale",
    trenitalia_id=830000219,
)

TORINO = Station(
    name="Torino Porta Nuova",
    trenitalia_id=830001098,
)

VENEZIA = Station(
    name="Venezia Santa Lucia",
    trenitalia_id=830001217,
)

BOLOGNA = Station(
    name="Bologna Centrale",
    trenitalia_id=830000351,
)

FIRENZE = Station(
    name="Firenze Santa Maria Novella",
    trenitalia_id=830000451,
)


# ─────────────────────────────────────────────────────────────
# ROUTEN
# Nur Wettbewerbsrouten (mind. 2 Anbieter)
# ─────────────────────────────────────────────────────────────

ROUTES = [

    # ── Deutschland: DB vs. Flixtrain ──────────────────────────
    Route(
        origin=BERLIN,
        destination=HAMBURG,
        operators=["db", "flixtrain"],
        description="Berlin–Hamburg (DB vs. Flixtrain)"
    ),
    Route(
        origin=MÜNCHEN,
        destination=BERLIN,
        operators=["db", "flixtrain"],
        description="München–Berlin (DB vs. Flixtrain)"
    ),
    Route(
        origin=MÜNCHEN,
        destination=FRANKFURT,
        operators=["db", "flixtrain"],
        description="München–Frankfurt (DB vs. Flixtrain)"
    ),
    Route(
        origin=KÖLN,
        destination=BERLIN,
        operators=["db", "flixtrain"],
        description="Köln–Berlin (DB vs. Flixtrain)"
    ),

    # ── International: DB vs. ÖBB ──────────────────────────────
    Route(
        origin=MÜNCHEN,
        destination=WIEN,
        operators=["db", "oebb"],
        description="München–Wien (DB vs. ÖBB)"
    ),

    # ── Italien: Trenitalia vs. Italo ──────────────────────────
    Route(
        origin=MILANO,
        destination=ROMA,
        operators=["trenitalia", "italo"],
        description="Milano–Roma (Trenitalia vs. Italo)"
    ),
    Route(
        origin=MILANO,
        destination=NAPOLI,
        operators=["trenitalia", "italo"],
        description="Milano–Napoli (Trenitalia vs. Italo)"
    ),
    Route(
        origin=ROMA,
        destination=NAPOLI,
        operators=["trenitalia", "italo"],
        description="Roma–Napoli (Trenitalia vs. Italo)"
    ),
    Route(
        origin=TORINO,
        destination=ROMA,
        operators=["trenitalia", "italo"],
        description="Torino–Roma (Trenitalia vs. Italo)"
    ),
    Route(
        origin=MILANO,
        destination=VENEZIA,
        operators=["trenitalia", "italo"],
        description="Milano–Venezia (Trenitalia vs. Italo)"
    ),

    # ── International: Deutschland–Italien ─────────────────────
    Route(
        origin=MÜNCHEN,
        destination=MILANO,
        operators=["db", "oebb"],
        description="München–Milano (DB / ÖBB)"
    ),
]


# ─────────────────────────────────────────────────────────────
# HILFSFUNKTIONEN
# ─────────────────────────────────────────────────────────────

def get_routes_for_operator(operator: str) -> list[Route]:
    """Gibt alle Routen zurück die ein bestimmter Anbieter bedient."""
    return [r for r in ROUTES if operator in r.operators]


def get_routes_with_competition() -> list[Route]:
    """Gibt alle Routen zurück auf denen mind. 2 Anbieter konkurrieren."""
    return [r for r in ROUTES if len(r.operators) >= 2]


# ─────────────────────────────────────────────────────────────
# BUCHUNGSHORIZONTE (Tage in die Zukunft)
# ─────────────────────────────────────────────────────────────

BOOKING_HORIZONS = [7, 30, 90]  # Tage


# ─────────────────────────────────────────────────────────────
# QUICK-CHECK beim direkten Ausführen
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"Gesamt Routen: {len(ROUTES)}")
    print()
    for op in ["db", "flixtrain", "trenitalia", "italo", "oebb"]:
        routes = get_routes_for_operator(op)
        print(f"{op.upper():<12} {len(routes)} Routen:")
        for r in routes:
            print(f"  → {r.description}")
        print()
    print(f"Buchungshorizonte: {BOOKING_HORIZONS} Tage")
    print(f"Requests/Tag (geschätzt): {len(ROUTES) * len(BOOKING_HORIZONS)}")
