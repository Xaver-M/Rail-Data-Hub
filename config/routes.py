# config/routes.py
# Zentrale Routen-Konfiguration für Rail Data Hub
# Nur Routen mit mindestens 2 Anbietern (Wettbewerbsrouten)

from dataclasses import dataclass
from typing import Optional


@dataclass
class Station:
    name: str
    flixtrain_id: Optional[str] = None
    flixtrain_city_id: Optional[str] = None
    flixbus_id: Optional[str] = None
    trenitalia_id: Optional[int] = None
    italo_id: Optional[int] = None
    db_id: Optional[str] = None
    oebb_id: Optional[str] = None
    ouigo_es_id: Optional[str] = None          # UIC-Code für Ouigo España
    renfe_id: Optional[str] = None
    iryo_id: Optional[str] = None
    regiojet_station_id: Optional[str] = None  # RegioJet STATION-ID
    regiojet_city_id: Optional[str] = None     # RegioJet CITY-ID 


@dataclass
class Route:
    origin: Station
    destination: Station
    operators: list[str]
    description: str = ""
    route_id: str = ""


# ─────────────────────────────────────────────────────────────
# STATIONEN
# ─────────────────────────────────────────────────────────────

BERLIN = Station(
    name="Berlin Hbf",
    flixtrain_id="394a5408-d778-4959-a63e-973253443ed2",
    flixtrain_city_id="40d8f682-8646-11e6-9066-549f350fcb0c",
    db_id="8011160",
)

HAMBURG = Station(
    name="Hamburg Hbf",
    flixtrain_id="38c4c04e-e957-4115-ac23-6fa87012bde4",
    flixtrain_city_id="40d91e53-8646-11e6-9066-549f350fcb0c",
    db_id="8002549",
)

MÜNCHEN = Station(
    name="München Hbf",
    flixtrain_id="dcbabbfa-9603-11e6-9066-549f350fcb0c",
    flixtrain_city_id="40d901a5-8646-11e6-9066-549f350fcb0c",
    db_id="8000261",
)

FRANKFURT = Station(
    name="Frankfurt(Main)Hbf",
    flixtrain_id="344886ff-4616-48b4-b476-98f0adcb907a",
    flixtrain_city_id="40d90407-8646-11e6-9066-549f350fcb0c",
    db_id="8000105",
)

KÖLN = Station(
    name="Köln Hbf",
    flixtrain_id="5e24b585-a2eb-42ea-acf5-b1063555f002",
    flixtrain_city_id="40d91025-8646-11e6-9066-549f350fcb0c",
    db_id="8000207",
)

STUTTGART = Station(
    name="Stuttgart Hbf",
    flixtrain_id="f6d07c4e-fa7e-4ab6-86bc-71b34ffb8cca",
    flixtrain_city_id="40d90995-8646-11e6-9066-549f350fcb0c",
    db_id="8000096",
)

LEIPZIG = Station(
    name="Leipzig Hbf",
    flixtrain_id="206a3e42-ff08-4902-b26c-fb192c94048e",
    flixtrain_city_id="40d917f9-8646-11e6-9066-549f350fcb0c",
    db_id="8010205",
)

HANNOVER = Station(
    name="Hannover Hbf",
    flixtrain_id="b3c64a07-e6ae-4e39-9e36-d6e3a739f083",
    flixtrain_city_id="40da4ac8-8646-11e6-9066-549f350fcb0c",
    db_id="8000152",
)

KARLSRUHE = Station(
    name="Karlsruhe Hbf",
    flixtrain_id="a661a63c-ac57-45c8-a3f4-141478a0b99c",
    flixtrain_city_id="40d912c2-8646-11e6-9066-549f350fcb0c",
    db_id="8000191",
)

BASEL = Station(
    name="Basel Bad Bf",
    flixtrain_id="086064da-8914-415f-83cc-8d6a087f5ed2",
    flixtrain_city_id="40de3026-8646-11e6-9066-549f350fcb0c",
    db_id="8000026",
)

WIEN = Station(
    name="Wien Hbf",
    db_id="8100003",
    oebb_id="1190100",
    regiojet_station_id="372825000",
)

PRAG = Station(
    name="Praha hlavní nádraží",
    regiojet_city_id="10202052",
)

BRATISLAVA = Station(
    name="Bratislava hlavná stanica",
    regiojet_city_id="10202043",
)

BUDAPEST = Station(
    name="Budapest-Keleti",
    regiojet_city_id="10202059",
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
    trenitalia_id=830000219,
)

VENEZIA = Station(
    name="Venezia Santa Lucia",
    trenitalia_id=830002593,
)

# ── Spanien ────────────────────────────────────────────────────
MADRID = Station(
    name="Madrid - Todas las estaciones",
    ouigo_es_id="MT1",
    renfe_id="0071,MADRI,null",
)

BARCELONA = Station(
    name="Barcelona - Sants",
    ouigo_es_id="7171801",
    renfe_id="0071,BARCE,null",
)

VALENCIA = Station(
    name="Valencia - Joaquín Sorolla",
    ouigo_es_id="7103216",
)

SEVILLA = Station(
    name="Sevilla - Santa Justa",
    ouigo_es_id="7151003",
)

ZARAGOZA = Station(
    name="Zaragoza - Delicias",
    ouigo_es_id="7104040",
)


# ─────────────────────────────────────────────────────────────
# ROUTEN
# ─────────────────────────────────────────────────────────────

ROUTES = [

    # ── FLX 10: Stuttgart–Frankfurt–Berlin ─────────────────────
    Route(
        origin=STUTTGART,
        destination=BERLIN,
        operators=["db", "flixtrain"],
        description="Stuttgart–Berlin (FLX10 vs. DB)",
        route_id="stuttgart-berlin"
    ),
    Route(
        origin=FRANKFURT,
        destination=BERLIN,
        operators=["db", "flixtrain"],
        description="Frankfurt–Berlin (FLX10 vs. DB)",
        route_id="frankfurt-berlin"
    ),

    # ── FLX 10: Basel–Frankfurt–Berlin ─────────────────────────
    Route(
        origin=BASEL,
        destination=BERLIN,
        operators=["db", "flixtrain"],
        description="Basel–Berlin (FLX10 vs. DB)",
        route_id="basel-berlin"
    ),

    # ── FLX 20: Hamburg–Köln ───────────────────────────────────
    Route(
        origin=HAMBURG,
        destination=KÖLN,
        operators=["db", "flixtrain"],
        description="Hamburg–Köln (FLX20 vs. DB)",
        route_id="hamburg-koeln"
    ),

    # ── FLX 30: Köln–Berlin ────────────────────────────────────
    Route(
        origin=KÖLN,
        destination=BERLIN,
        operators=["db", "flixtrain"],
        description="Köln–Berlin (FLX30 vs. DB)",
        route_id="koeln-berlin"
    ),

    # ── FLX 35: Hamburg–Berlin, Hamburg–Leipzig ────────────────
    Route(
        origin=HAMBURG,
        destination=BERLIN,
        operators=["db", "flixtrain"],
        description="Hamburg–Berlin (FLX35 vs. DB)",
        route_id="hamburg-berlin"
    ),
    Route(
        origin=HAMBURG,
        destination=LEIPZIG,
        operators=["db", "flixtrain"],
        description="Hamburg–Leipzig (FLX35 vs. DB)",
        route_id="hamburg-leipzig"
    ),

    # ── Italien: Trenitalia vs. Italo ──────────────────────────
    Route(
        origin=MILANO,
        destination=ROMA,
        operators=["trenitalia", "italo"],
        description="Milano–Roma (Trenitalia vs. Italo)",
        route_id="milano-roma"
    ),
    Route(
        origin=MILANO,
        destination=NAPOLI,
        operators=["trenitalia", "italo"],
        description="Milano–Napoli (Trenitalia vs. Italo)",
        route_id="milano-napoli"
    ),
    Route(
        origin=ROMA,
        destination=NAPOLI,
        operators=["trenitalia", "italo"],
        description="Roma–Napoli (Trenitalia vs. Italo)",
        route_id="roma-napoli"
    ),
    Route(
        origin=TORINO,
        destination=ROMA,
        operators=["trenitalia", "italo"],
        description="Torino–Roma (Trenitalia vs. Italo)",
        route_id="torino-roma"
    ),
    Route(
        origin=MILANO,
        destination=VENEZIA,
        operators=["trenitalia", "italo"],
        description="Milano–Venezia (Trenitalia vs. Italo)",
        route_id="milano-venezia"
    ),

    # ── Spanien: Renfe vs. Ouigo España vs. Iryo ───────────────
    Route(
        origin=MADRID,
        destination=BARCELONA,
        operators=["renfe", "ouigo_es", "iryo"],
        description="Madrid–Barcelona (Renfe vs. Ouigo vs. Iryo)",
        route_id="madrid-barcelona"
    ),
    Route(
        origin=MADRID,
        destination=VALENCIA,
        operators=["renfe", "ouigo_es"],
        description="Madrid–Valencia (Renfe vs. Ouigo)",
        route_id="madrid-valencia"
    ),
    Route(
        origin=MADRID,
        destination=SEVILLA,
        operators=["renfe", "ouigo_es"],
        description="Madrid–Sevilla (Renfe vs. Ouigo)",
        route_id="madrid-sevilla"
    ),

    # ── International ──────────────────────────────────────────
    Route(
        origin=MÜNCHEN,
        destination=WIEN,
        operators=["db", "oebb"],
        description="München–Wien (DB vs. ÖBB)",
        route_id="muenchen-wien"
    ),

    # ── RegioJet: Tschechien / Österreich ──────────────────────
    Route(
        origin=WIEN,
        destination=PRAG,
        operators=["regiojet"],
        description="Wien–Praha (RegioJet)",
        route_id="wien-prag"
    ),
    Route(
        origin=PRAG,
        destination=WIEN,
        operators=["regiojet"],
        description="Praha–Wien (RegioJet)",
        route_id="prag-wien"
    ),
    Route(
        origin=PRAG,
        destination=BRATISLAVA,
        operators=["regiojet"],
        description="Praha–Bratislava (RegioJet)",
        route_id="prag-bratislava"
    ),
    Route(
        origin=PRAG,
        destination=BUDAPEST,
        operators=["regiojet"],
        description="Praha–Budapest (RegioJet)",
        route_id="prag-budapest"
    ),
]


# ─────────────────────────────────────────────────────────────
# HILFSFUNKTIONEN
# ─────────────────────────────────────────────────────────────

def get_routes_for_operator(operator: str) -> list[Route]:
    return [r for r in ROUTES if operator in r.operators]


def get_routes_with_competition() -> list[Route]:
    return [r for r in ROUTES if len(r.operators) >= 2]


# ─────────────────────────────────────────────────────────────
# BUCHUNGSHORIZONTE
# ─────────────────────────────────────────────────────────────

BOOKING_HORIZONS = [
    1, 2, 3, 4, 5, 6, 7,
    10, 14, 21, 30,
    45, 60, 90,
]


if __name__ == "__main__":
    print(f"Gesamt Routen: {len(ROUTES)}")
    print()
    for op in ["db", "flixtrain", "trenitalia", "italo", "oebb", "ouigo_es", "renfe", "iryo", "regiojet"]:
        routes = get_routes_for_operator(op)
        if routes:
            print(f"{op.upper():<12} {len(routes)} Routen:")
            for r in routes:
                print(f"  → {r.description} [{r.route_id}]")
            print()
    print(f"Buchungshorizonte: {BOOKING_HORIZONS} Tage")
    print(f"Requests/Tag (geschätzt): {len(ROUTES) * len(BOOKING_HORIZONS)}")