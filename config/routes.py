# config/routes.py
# Central route configuration for Rail Data Hub

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
    ouigo_es_id: Optional[str] = None   
    ouigo_fr_id: Optional[str] = None       
    renfe_id: Optional[str] = None
    iryo_id: Optional[str] = None
    regiojet_station_id: Optional[str] = None  
    regiojet_city_id: Optional[str] = None     


@dataclass
class Route:
    origin: Station
    destination: Station
    operators: list[str]
    description: str = ""
    route_id: str = ""


# ─────────────────────────────────────────────────────────────
# STATIONS
# ─────────────────────────────────────────────────────────────

# ── Germany ─────────────────────────────────────────────────── 

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

MUNICH = Station(
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

COLOGNE = Station(
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

HANOVER = Station(
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

DUSSELDORF = Station(
    name="Düsseldorf Hbf",
    db_id="8000085",
)

AACHEN = Station(
    name="Aachen Hbf",
    db_id="8000001",
)

KOBLENZ = Station(
    name="Koblenz Hbf",
    db_id="8000206",
)

SAARBRUCKEN = Station(
    name="Saarbrücken Hbf",
    db_id="8000323",
)

DORTMUND = Station(
    name="Dortmund Hbf",
    db_id="8000080",
)

BREMEN = Station(
    name="Bremen Hbf",
    db_id="8000050",
)

KIEL = Station(
    name="Kiel Hbf",
    db_id="8000199",
)

LUBECK = Station(
    name="Lübeck Hbf",
    db_id="8000237",
)

DRESDEN = Station(
    name="Dresden Hbf",
    db_id="8010085",
)

WIESBADEN = Station(
    name="Wiesbaden Hbf",
    db_id="8000250",
)

PASSAU = Station(
    name="Passau Hbf",
    db_id="8000298",
)

BINZ = Station(
    name="Ostseebad Binz",
    db_id="8010032",
)

VIENNA = Station(
    name="Wien Hbf",
    db_id="8100003",
    oebb_id="1190100",
    regiojet_station_id="372825000",
    regiojet_city_id="10202052",
)

GRAZ = Station(
    name="Graz Hbf",
    db_id="8100173",
)

ZURICH = Station(
    name="Zürich HB",
    db_id="8503000",
)

PRAGUE = Station(
    name="Praha hlavní nádraží",
    regiojet_city_id="10202003",
)

BRATISLAVA = Station(
    name="Bratislava hlavná stanica",
    regiojet_city_id="10202001",
)

BUDAPEST = Station(
    name="Budapest-Keleti",
    db_id="5510017",
    regiojet_city_id="10202091",
)

# ── Italy ───────────────────────────────────────────────────── 

MILAN = Station(
    name="Milano Centrale",
    trenitalia_id=830001700,
    db_id="8300017",
)

ROME = Station(
    name="Roma Termini",
    trenitalia_id=830008409,
)

NAPLES = Station(
    name="Napoli Centrale",
    trenitalia_id=830000219,
)

TURIN = Station(
    name="Torino Porta Nuova",
    trenitalia_id=830000219,
)

VENICE = Station(
    name="Venezia Santa Lucia",
    trenitalia_id=830002593,
)

# ── Spain ──────────────────────────────────────────────────────
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

SEVILLE = Station(
    name="Sevilla - Santa Justa",
    ouigo_es_id="7151003",
)

ZARAGOZA = Station(
    name="Zaragoza - Delicias",
    ouigo_es_id="7104040",
)

# ── France ──────────────────────────────────────────────────────
PARIS = Station(
    name="Paris - Toutes les gares",
    ouigo_fr_id="PT1",
)

NANTES = Station(
    name="Nantes",
    ouigo_fr_id="87481002",
)

MONTPELLIER = Station(
    name="Montpellier toutes gares",
    ouigo_fr_id="MP1",
)

MARSEILLE = Station(
    name="Marseille St Charles",
    ouigo_fr_id="87751008",
    db_id="8775100",
)

LYON = Station(
    name="Lyon toutes gares",
    ouigo_fr_id="LY1",
)

BORDEAUX = Station(
    name="Bordeaux St Jean",
    ouigo_fr_id="87581009",
)

PARIS_EST = Station(
    name="Paris Est",
    db_id="8796066",
)

# ── Netherlands ──────────────────────────────────────────────
AMSTERDAM = Station(
    name="Amsterdam Centraal",
    db_id="8400058",
)

# ── Belgium ──────────────────────────────────────────────────
BRUSSELS = Station(
    name="Brüssel-Midi",
    db_id="8814001",
)

# ─────────────────────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────────────────────

ROUTES = [

    # ── FLX 10: Stuttgart–Frankfurt–Berlin ─────────────────────
    Route(
        origin=STUTTGART,
        destination=BERLIN,
        operators=["db", "flixtrain"],
        description="Stuttgart-Berlin (FLX10 vs. DB)",
        route_id="stuttgart-berlin"
    ),
    Route(
        origin=FRANKFURT,
        destination=BERLIN,
        operators=["db", "flixtrain"],
        description="Frankfurt-Berlin (FLX10 vs. DB)",
        route_id="frankfurt-berlin"
    ),

    # ── FLX 10: Basel–Frankfurt–Berlin ─────────────────────────
    Route(
        origin=BASEL,
        destination=BERLIN,
        operators=["db", "flixtrain"],
        description="Basel-Berlin (FLX10 vs. DB)",
        route_id="basel-berlin"
    ),

    # ── FLX 20: Hamburg–Cologne ────────────────────────────────
    Route(
        origin=HAMBURG,
        destination=COLOGNE,
        operators=["db", "flixtrain"],
        description="Hamburg-Cologne (FLX20 vs. DB)",
        route_id="hamburg-cologne"
    ),

    # ── FLX 30: Cologne–Berlin ─────────────────────────────────
    Route(
        origin=COLOGNE,
        destination=BERLIN,
        operators=["db", "flixtrain"],
        description="Cologne-Berlin (FLX30 vs. DB)",
        route_id="cologne-berlin"
    ),

    # ── FLX 35: Hamburg–Berlin, Hamburg–Leipzig ────────────────
    Route(
        origin=HAMBURG,
        destination=BERLIN,
        operators=["db", "flixtrain"],
        description="Hamburg-Berlin (FLX35 vs. DB)",
        route_id="hamburg-berlin"
    ),
    Route(
        origin=HAMBURG,
        destination=LEIPZIG,
        operators=["db", "flixtrain"],
        description="Hamburg-Leipzig (FLX35 vs. DB)",
        route_id="hamburg-leipzig"
    ),

    # ── Italy: Trenitalia vs. Italo ────────────────────────────
    Route(
        origin=MILAN,
        destination=ROME,
        operators=["trenitalia", "italo"],
        description="Milan-Rome (Trenitalia vs. Italo)",
        route_id="milan-rome"
    ),
    Route(
        origin=MILAN,
        destination=NAPLES,
        operators=["trenitalia", "italo"],
        description="Milan-Naples (Trenitalia vs. Italo)",
        route_id="milan-naples"
    ),
    Route(
        origin=ROME,
        destination=NAPLES,
        operators=["trenitalia", "italo"],
        description="Rome-Naples (Trenitalia vs. Italo)",
        route_id="rome-naples"
    ),
    Route(
        origin=TURIN,
        destination=ROME,
        operators=["trenitalia", "italo"],
        description="Turin-Rome (Trenitalia vs. Italo)",
        route_id="turin-rome"
    ),
    Route(
        origin=MILAN,
        destination=VENICE,
        operators=["trenitalia", "italo"],
        description="Milan-Venice (Trenitalia vs. Italo)",
        route_id="milan-venice"
    ),

    # ── Spain: Renfe vs. Ouigo España vs. Iryo ─────────────────
    Route(
        origin=MADRID,
        destination=BARCELONA,
        operators=["renfe", "ouigo_es", "iryo"],
        description="Madrid-Barcelona (Renfe vs. Ouigo vs. Iryo)",
        route_id="madrid-barcelona"
    ),
    Route(
        origin=MADRID,
        destination=VALENCIA,
        operators=["renfe", "ouigo_es"],
        description="Madrid-Valencia (Renfe vs. Ouigo)",
        route_id="madrid-valencia"
    ),
    Route(
        origin=MADRID,
        destination=SEVILLE,
        operators=["renfe", "ouigo_es"],
        description="Madrid-Seville (Renfe vs. Ouigo)",
        route_id="madrid-seville"
    ),

    # ── France: Ouigo vs. SNCF (TGV) ───────────────────────────────
    Route(
        origin=PARIS,
        destination=LYON,
        operators=["ouigo_fr", "SNCF"],
        description="Paris-Lyon (Ouigo vs. SNCF)",
        route_id="paris-lyon"
    ),

    Route(
        origin=PARIS,
        destination=MARSEILLE,
        operators=["ouigo_fr", "SNCF"],
        description="Paris-Marseille (Ouigo vs. SNCF)",
        route_id="paris-marseille"
    ),

    Route(
        origin=PARIS,
        destination=NANTES,
        operators=["ouigo_fr", "SNCF"],
        description="Paris-Nantes (Ouigo vs. SNCF)",
        route_id="paris-nantes"
    ),

    # ── International ──────────────────────────────────────────

    Route(
        origin=MUNICH,
        destination=VIENNA,
        operators=["db", "oebb"],
        description="Munich-Vienna (DB vs. OeBB)",
        route_id="munich-vienna"
    ),

    # ── RegioJet: Czech Republic / Austria ─────────────────────
    Route(
        origin=VIENNA,
        destination=PRAGUE,
        operators=["regiojet"],
        description="Vienna-Prague (RegioJet)",
        route_id="vienna-prague"
    ),
    Route(
        origin=PRAGUE,
        destination=VIENNA,
        operators=["regiojet"],
        description="Prague-Vienna (RegioJet)",
        route_id="prague-vienna"
    ),
    Route(
        origin=PRAGUE,
        destination=BRATISLAVA,
        operators=["regiojet"],
        description="Prague-Bratislava (RegioJet)",
        route_id="prague-bratislava"
    ),
    Route(
        origin=PRAGUE,
        destination=BUDAPEST,
        operators=["regiojet"],
        description="Prague-Budapest (RegioJet)",
        route_id="prague-budapest"
    ),

    # ── DB ICE / ECE domestic routes ───────────────────────────

    # ICE 2 / 10 / 14 / 19: Berlin ↔ Köln corridor
    Route(
        origin=BERLIN,
        destination=COLOGNE,
        operators=["db"],
        description="Berlin-Köln (DB ICE)",
        route_id="berlin-cologne"
    ),
    Route(
        origin=BERLIN,
        destination=DUSSELDORF,
        operators=["db"],
        description="Berlin-Düsseldorf (DB ICE 10)",
        route_id="berlin-dusseldorf"
    ),
    Route(
        origin=BERLIN,
        destination=AACHEN,
        operators=["db"],
        description="Berlin-Aachen (DB ICE 14)",
        route_id="berlin-aachen"
    ),
    Route(
        origin=BERLIN,
        destination=KOBLENZ,
        operators=["db"],
        description="Berlin-Koblenz (DB ICE 19)",
        route_id="berlin-koblenz"
    ),

    # ICE 11 / 18 / 24 / 25 / 28 / 29 / 42: Hamburg–München
    Route(
        origin=HAMBURG,
        destination=MUNICH,
        operators=["db"],
        description="Hamburg-München (DB ICE)",
        route_id="hamburg-munich"
    ),

    # ICE 12: Berlin–Zürich
    Route(
        origin=BERLIN,
        destination=ZURICH,
        operators=["db"],
        description="Berlin-Zürich (DB ICE 12)",
        route_id="berlin-zurich"
    ),

    # ICE 13: Berlin–Frankfurt
    Route(
        origin=BERLIN,
        destination=FRANKFURT,
        operators=["db", "flixtrain"],
        description="Berlin-Frankfurt (DB ICE 13 vs. Flixtrain)",
        route_id="berlin-frankfurt"
    ),

    # ICE 15 / 22: Hamburg–Stuttgart
    Route(
        origin=HAMBURG,
        destination=STUTTGART,
        operators=["db"],
        description="Hamburg-Stuttgart (DB ICE 15/22)",
        route_id="hamburg-stuttgart"
    ),

    # ICE 15: Hamburg–Saarbrücken
    Route(
        origin=HAMBURG,
        destination=SAARBRUCKEN,
        operators=["db"],
        description="Hamburg-Saarbrücken (DB ICE 15)",
        route_id="hamburg-saarbrucken"
    ),

    # ICE 16: Berlin–Saarbrücken
    Route(
        origin=BERLIN,
        destination=SAARBRUCKEN,
        operators=["db"],
        description="Berlin-Saarbrücken (DB ICE 16)",
        route_id="berlin-saarbrucken"
    ),

    # ICE 20 / 43: Hamburg–Basel / Hamburg–Zürich
    Route(
        origin=HAMBURG,
        destination=BASEL,
        operators=["db"],
        description="Hamburg-Basel (DB ICE 20/43)",
        route_id="hamburg-basel"
    ),
    Route(
        origin=HAMBURG,
        destination=ZURICH,
        operators=["db"],
        description="Hamburg-Zürich (DB ICE 20)",
        route_id="hamburg-zurich"
    ),

    # ICE 21: Berlin–Ostseebad Binz
    Route(
        origin=BERLIN,
        destination=BINZ,
        operators=["db"],
        description="Berlin-Ostseebad Binz (DB ICE 21)",
        route_id="berlin-binz"
    ),

    # ICE 22 / 42: Kiel–Stuttgart / Kiel–München
    Route(
        origin=KIEL,
        destination=STUTTGART,
        operators=["db"],
        description="Kiel-Stuttgart (DB ICE 22)",
        route_id="kiel-stuttgart"
    ),
    Route(
        origin=KIEL,
        destination=MUNICH,
        operators=["db"],
        description="Kiel-München (DB ICE 42)",
        route_id="kiel-munich"
    ),

    # ICE 25: Bremen–München
    Route(
        origin=BREMEN,
        destination=MUNICH,
        operators=["db"],
        description="Bremen-München (DB ICE 25)",
        route_id="bremen-munich"
    ),

    # ICE 26: Hamburg–Karlsruhe
    Route(
        origin=HAMBURG,
        destination=KARLSRUHE,
        operators=["db"],
        description="Hamburg-Karlsruhe (DB ICE 26)",
        route_id="hamburg-karlsruhe"
    ),

    # ICE 27: Hamburg–Dresden / Hamburg–Graz
    Route(
        origin=HAMBURG,
        destination=DRESDEN,
        operators=["db"],
        description="Hamburg-Dresden (DB ICE 27)",
        route_id="hamburg-dresden"
    ),
    Route(
        origin=HAMBURG,
        destination=GRAZ,
        operators=["db"],
        description="Hamburg-Graz (DB ICE 27)",
        route_id="hamburg-graz"
    ),

    # ICE 29: Lübeck–München
    Route(
        origin=LUBECK,
        destination=MUNICH,
        operators=["db"],
        description="Lübeck-München (DB ICE 29)",
        route_id="lubeck-munich"
    ),

   
    Route(
        origin=HAMBURG,
        destination=PASSAU,
        operators=["db"],
        description="Hamburg-Passau (DB ICE 39)",
        route_id="hamburg-passau"
    ),

   
    Route(
        origin=DORTMUND,
        destination=MUNICH,
        operators=["db"],
        description="Dortmund-München (DB ICE 41/47)",
        route_id="dortmund-munich"
    ),

   
    Route(
        origin=COLOGNE,
        destination=FRANKFURT,
        operators=["db"],
        description="Köln-Frankfurt (DB ICE 49)",
        route_id="cologne-frankfurt"
    ),

    
    Route(
        origin=DRESDEN,
        destination=WIESBADEN,
        operators=["db"],
        description="Dresden-Wiesbaden (DB ICE 50)",
        route_id="dresden-wiesbaden"
    ),

    
    Route(
        origin=DORTMUND,
        destination=STUTTGART,
        operators=["db"],
        description="Dortmund-Stuttgart (DB ICE 55)",
        route_id="dortmund-stuttgart"
    ),

    
    Route(
        origin=KARLSRUHE,
        destination=MUNICH,
        operators=["db"],
        description="Karlsruhe-München (DB ICE 60)",
        route_id="karlsruhe-munich"
    ),

    
    Route(
        origin=DORTMUND,
        destination=VIENNA,
        operators=["db"],
        description="Dortmund-Wien (DB ICE 91)",
        route_id="dortmund-vienna"
    ),

    
    Route(
        origin=MUNICH,
        destination=BUDAPEST,
        operators=["db"],
        description="München-Budapest (DB ICE 90)",
        route_id="munich-budapest"
    ),

    # ── DB ICE international routes ──────────────────────

    # ICE 77: Berlin–Amsterdam
    Route(
        origin=BERLIN,
        destination=AMSTERDAM,
        operators=["db"],
        description="Berlin-Amsterdam (DB ICE 77)",
        route_id="berlin-amsterdam"
    ),

    # ICE 78: Frankfurt–Amsterdam
    Route(
        origin=FRANKFURT,
        destination=AMSTERDAM,
        operators=["db"],
        description="Frankfurt-Amsterdam (DB ICE 78)",
        route_id="frankfurt-amsterdam"
    ),

    # ICE 79: Frankfurt–Brüssel
    Route(
        origin=FRANKFURT,
        destination=BRUSSELS,
        operators=["db"],
        description="Frankfurt-Brüssel (DB ICE 79)",
        route_id="frankfurt-brussels"
    ),

    # ICE 82: Frankfurt–Paris Est
    Route(
        origin=FRANKFURT,
        destination=PARIS_EST,
        operators=["db"],
        description="Frankfurt-Paris Est (DB ICE 82)",
        route_id="frankfurt-paris"
    ),

    # ICE 83: Stuttgart–Paris Est
    Route(
        origin=STUTTGART,
        destination=PARIS_EST,
        operators=["db"],
        description="Stuttgart-Paris Est (DB ICE 83)",
        route_id="stuttgart-paris"
    ),

    # ICE 84: Frankfurt–Marseille
    Route(
        origin=FRANKFURT,
        destination=MARSEILLE,
        operators=["db"],
        description="Frankfurt-Marseille (DB ICE 84)",
        route_id="frankfurt-marseille"
    ),

    # ECE 85: Frankfurt–Mailand
    Route(
        origin=FRANKFURT,
        destination=MILAN,
        operators=["db"],
        description="Frankfurt-Mailand (DB ECE 85)",
        route_id="frankfurt-milan"
    ),

    # ECE 88: München–Zürich
    Route(
        origin=MUNICH,
        destination=ZURICH,
        operators=["db"],
        description="München-Zürich (DB ECE 88)",
        route_id="munich-zurich"
    ),
]


# ─────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────

def get_routes_for_operator(operator: str) -> list[Route]:
    return [r for r in ROUTES if operator in r.operators]


def get_routes_with_competition() -> list[Route]:
    return [r for r in ROUTES if len(r.operators) >= 2]


# ─────────────────────────────────────────────────────────────
# BOOKING HORIZONS
# ─────────────────────────────────────────────────────────────

BOOKING_HORIZONS = [
    1, 2, 3, 4, 5, 6, 7,
    10, 14, 21, 30,
    45, 60, 90,
]


if __name__ == "__main__":
    print(f"Total routes: {len(ROUTES)}")
    print()
    for op in ["db", "flixtrain", "trenitalia", "italo", "oebb", "ouigo_es", "renfe", "iryo", "regiojet"]:
        routes = get_routes_for_operator(op)
        if routes:
            print(f"{op.upper():<12} {len(routes)} routes:")
            for r in routes:
                print(f"  -> {r.description} [{r.route_id}]")
            print()
    print(f"Booking horizons: {BOOKING_HORIZONS} days")
    print(f"Requests/day (estimated): {len(ROUTES) * len(BOOKING_HORIZONS)}")