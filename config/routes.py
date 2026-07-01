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
    italo_id: Optional[str] = None
    db_id: Optional[str] = None
    oebb_id: Optional[str] = None
    ouigo_es_id: Optional[str] = None   
    ouigo_fr_id: Optional[str] = None       
    renfe_id: Optional[str] = None
    iryo_id: Optional[str] = None
    regiojet_station_id: Optional[str] = None
    regiojet_city_id: Optional[str] = None
    cd_station_name: Optional[str] = None      # Name for CD CDIS API (Czech spelling)


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

# ── Austria ───────────────────────────────────────────────────

GRAZ = Station(
    name="Graz Hbf",
    db_id="8100173",
    cd_station_name="Graz Hbf",
)

LINZ = Station(
    name="Linz Hbf",
    cd_station_name="Linz Hbf",
)

VIENNA = Station(
    name="Wien Hbf",
    db_id="8100003",
    oebb_id="1190100",
    regiojet_city_id="10202052",
    regiojet_station_id="4218903000",
    cd_station_name="Wien Hbf",
)

# ── Belgium ───────────────────────────────────────────────────

BRUSSELS = Station(
    name="Brussels-Midi",
    db_id="8814001",
    ouigo_fr_id="88140010",
)

# ── Czech Republic ────────────────────────────────────────────

BRNO = Station(
    name="Brno hlavní nádraží",
    regiojet_city_id="10202002",
    regiojet_station_id="3088864001",
    cd_station_name="Brno hl.n.",
)

OSTRAVA = Station(
    name="Ostrava hlavní nádraží",
    regiojet_city_id="10202000",
    regiojet_station_id="372825008",
    cd_station_name="Ostrava hl.n.",
)

PRAGUE = Station(
    name="Praha hlavní nádraží",
    regiojet_city_id="10202003",
    regiojet_station_id="372825000",
    cd_station_name="Praha hl.n.",
)

# ── France ────────────────────────────────────────────────────

BORDEAUX = Station(
    name="Bordeaux St Jean",
    ouigo_fr_id="87581009",
)

BOURG_ST_MAURICE = Station(
    name="Bourg-Saint-Maurice",
    ouigo_fr_id="87749093",
)

BREST = Station(
    name="Brest",
    ouigo_fr_id="87474007",
)

COLMAR = Station(
    name="Colmar",
    ouigo_fr_id="87213645",
)

HENDAYE = Station(
    name="Hendaye",
    ouigo_fr_id="87600007",
)

LYON = Station(
    name="Lyon toutes gares",
    ouigo_fr_id="LY1",
    trenitalia_id=870076291,
)

MARSEILLE = Station(
    name="Marseille St Charles",
    ouigo_fr_id="87751008",
    db_id="8775100",
)

MONTPELLIER = Station(
    name="Montpellier toutes gares",
    ouigo_fr_id="MP1",
)

NANTES = Station(
    name="Nantes",
    ouigo_fr_id="87481002",
)

NICE = Station(
    name="Nice Ville",
    ouigo_fr_id="87756056",
)

PARIS = Station(
    name="Paris - Toutes les gares",
    ouigo_fr_id="PT1",
    trenitalia_id=870075890,
)

PARIS_EST = Station(
    name="Paris Est",
    db_id="8796066",
)

PERPIGNAN = Station(
    name="Perpignan",
    ouigo_fr_id="87696005",
)

RENNES = Station(
    name="Rennes",
    ouigo_fr_id="87471003",
)

STRASBOURG = Station(
    name="Strasbourg Ville",
    ouigo_fr_id="87212027",
)

TOULOUSE = Station(
    name="Toulouse Matabiau",
    ouigo_fr_id="87611004",
)

# ── Germany ───────────────────────────────────────────────────

AACHEN = Station(
    name="Aachen Hbf",
    db_id="8000001",
)

BASEL = Station(
    name="Basel Bad Bf",
    flixtrain_id="086064da-8914-415f-83cc-8d6a087f5ed2",
    flixtrain_city_id="40de3026-8646-11e6-9066-549f350fcb0c",
    db_id="8000026",
)

BERLIN = Station(
    name="Berlin Hbf",
    flixtrain_id="394a5408-d778-4959-a63e-973253443ed2",
    flixtrain_city_id="40d8f682-8646-11e6-9066-549f350fcb0c",
    flixbus_id="40d8f682-8646-11e6-9066-549f350fcb0c",
    db_id="8011160",
    cd_station_name="Berlin Hbf",
)

BINZ = Station(
    name="Ostseebad Binz",
    db_id="8010032",
)

BREMEN = Station(
    name="Bremen Hbf",
    db_id="8000050",
)

COLOGNE = Station(
    name="Köln Hbf",
    flixtrain_id="5e24b585-a2eb-42ea-acf5-b1063555f002",
    flixtrain_city_id="40d91025-8646-11e6-9066-549f350fcb0c",
    flixbus_id="40d91025-8646-11e6-9066-549f350fcb0c",
    db_id="8000207",
)

DORTMUND = Station(
    name="Dortmund Hbf",
    db_id="8000080",
)

DRESDEN = Station(
    name="Dresden Hbf",
    db_id="8010085",
    cd_station_name="Dresden Hbf",
)

DUSSELDORF = Station(
    name="Düsseldorf Hbf",
    db_id="8000085",
)

FRANKFURT = Station(
    name="Frankfurt(Main)Hbf",
    flixtrain_id="344886ff-4616-48b4-b476-98f0adcb907a",
    flixtrain_city_id="40d90407-8646-11e6-9066-549f350fcb0c",
    flixbus_id="40d90407-8646-11e6-9066-549f350fcb0c",
    db_id="8000105",
    cd_station_name="Frankfurt(Main)Hbf",
)

HAMBURG = Station(
    name="Hamburg Hbf",
    flixtrain_id="38c4c04e-e957-4115-ac23-6fa87012bde4",
    flixtrain_city_id="40d91e53-8646-11e6-9066-549f350fcb0c",
    flixbus_id="40d91e53-8646-11e6-9066-549f350fcb0c",
    db_id="8002549",
    cd_station_name="Hamburg Hbf",
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

KIEL = Station(
    name="Kiel Hbf",
    db_id="8000199",
)

KOBLENZ = Station(
    name="Koblenz Hbf",
    db_id="8000206",
)

LEIPZIG = Station(
    name="Leipzig Hbf",
    flixtrain_id="206a3e42-ff08-4902-b26c-fb192c94048e",
    flixtrain_city_id="40d917f9-8646-11e6-9066-549f350fcb0c",
    flixbus_id="40d917f9-8646-11e6-9066-549f350fcb0c",
    db_id="8010205",
)

LUBECK = Station(
    name="Lübeck Hbf",
    db_id="8000237",
)

MUNICH = Station(
    name="München Hbf",
    flixtrain_id="dcbabbfa-9603-11e6-9066-549f350fcb0c",
    flixtrain_city_id="40d901a5-8646-11e6-9066-549f350fcb0c",
    db_id="8000261",
    cd_station_name="München Hbf",
)

PASSAU = Station(
    name="Passau Hbf",
    db_id="8000298",
)

SAARBRUCKEN = Station(
    name="Saarbrücken Hbf",
    db_id="8000323",
)

STUTTGART = Station(
    name="Stuttgart Hbf",
    flixtrain_id="f6d07c4e-fa7e-4ab6-86bc-71b34ffb8cca",
    flixtrain_city_id="40d90995-8646-11e6-9066-549f350fcb0c",
    flixbus_id="40d90995-8646-11e6-9066-549f350fcb0c",
    db_id="8000096",
)

WIESBADEN = Station(
    name="Wiesbaden Hbf",
    db_id="8000250",
)

# ── Hungary ───────────────────────────────────────────────────

BUDAPEST = Station(
    name="Budapest-Keleti",
    db_id="5510017",
    regiojet_city_id="10202091",
    regiojet_station_id="7063331001",
    cd_station_name="Budapest-Keleti pu",
)

# ── Italy ─────────────────────────────────────────────────────

AGROPOLI = Station(
    name="Agropoli",
    italo_id="AGR",
)

ANCONA = Station(
    name="Ancona",
    trenitalia_id=830006003,
)

BARI = Station(
    name="Bari Centrale",
    italo_id="BAC",
)

BARLETTA = Station(
    name="Barletta",
    trenitalia_id=830013300,
    italo_id="BLT",
)

BENEVENTO = Station(
    name="Benevento",
    trenitalia_id=830009300,
    italo_id="BEN",
)

BERGAMO = Station(
    name="Bergamo",
    trenitalia_id=830001529,
    italo_id="BGM",
)

BISCEGLIE = Station(
    name="Bisceglie",
    italo_id="BIG",
)

BOLOGNA = Station(
    name="Bologna Centrale",
    trenitalia_id=830002700,
    italo_id="BC_",
)

BOLZANO = Station(
    name="Bolzano",
    trenitalia_id=830002026,
    italo_id="BLZ",
)

BRESCIA = Station(
    name="Brescia",
    trenitalia_id=830001717,
    italo_id="BSC",
)

CASERTA = Station(
    name="Caserta",
    trenitalia_id=830009600,
    italo_id="CEA",
)

CONEGLIANO = Station(
    name="Conegliano",
    italo_id="CON",
)

DESENZANO = Station(
    name="Desenzano",
    italo_id="DSG",
)

FERRARA = Station(
    name="Ferrara",
    italo_id="F__",
)

FLORENCE = Station(
    name="Firenze Santa Maria Novella",
    trenitalia_id=830005240,
    italo_id="SMN",
)

FOGGIA = Station(
    name="Foggia",
    trenitalia_id=830013200,
    italo_id="FG_",
)

GENOVA_BRIGNOLE = Station(
    name="Genova Brignole",
    italo_id="GB_",
)

GENOA = Station(
    name="Genova Piazza Principe",
    trenitalia_id=830004700,
    italo_id="G__",
)

LAMEZIA_TERME = Station(
    name="Lamezia Terme",
    trenitalia_id=830011400,
    italo_id="LON",
)

LATISANA = Station(
    name="Latisana Lignano Bibione",
    italo_id="LTL",
)

LECCE = Station(
    name="Lecce",
    trenitalia_id=830013555,
    italo_id="LCC",
)

MARATEA = Station(
    name="Maratea",
    italo_id="MRT",
)

MILAN = Station(
    name="Milano Centrale",
    trenitalia_id=830001700,
    db_id="8300017",
    italo_id="MC_",
)

NAPLES = Station(
    name="Napoli Centrale",
    trenitalia_id=830009218,
    italo_id="NAC",
)

PADOVA = Station(
    name="Padova",
    trenitalia_id=830002312,
    italo_id="PD_",
)

RAVENNA = Station(
    name="Ravenna",
    trenitalia_id=830005811,
)

REGGIO_CALABRIA = Station(
    name="Reggio di Calabria Centrale",
    trenitalia_id=830011781,
    italo_id="RCE",
)

REGGIO_EMILIA_AV = Station(
    name="Reggio Emilia AV",
    trenitalia_id=830003100,
    italo_id="AAV",
)

ROMA_TIBURTINA = Station(
    name="Roma Tiburtina",
    italo_id="RTB",
)

ROME = Station(
    name="Roma Termini",
    trenitalia_id=830008409,
    italo_id="RMT",
)

SALERNO = Station(
    name="Salerno",
    trenitalia_id=830009818,
    italo_id="SAL",
)

TARANTO = Station(
    name="Taranto",
    trenitalia_id=830013554,
)

TRIESTE = Station(
    name="Trieste Centrale",
    trenitalia_id=830003317,
    italo_id="TSC",
)

TURIN = Station(
    name="Torino Porta Nuova",
    trenitalia_id=830000219,
    db_id="8000096",
    italo_id="TOP",
)

TURIN_PS = Station(
    name="Torino Porta Susa",
    italo_id="OUE",
)

UDINE = Station(
    name="Udine",
    trenitalia_id=830003026,
    italo_id="UDN",
)

VENEZIA_MESTRE = Station(
    name="Venezia Mestre",
    trenitalia_id=830002560,
    italo_id="VEM",
)

VENICE = Station(
    name="Venezia Santa Lucia",
    trenitalia_id=830002593,
    italo_id="VSL",
)

VERONA = Station(
    name="Verona Porta Nuova",
    trenitalia_id=830002600,
    italo_id="VPN",
)

# ── Netherlands ───────────────────────────────────────────────

AMSTERDAM = Station(
    name="Amsterdam Centraal",
    db_id="8400058",
)

# ── Poland ────────────────────────────────────────────────────

CRACOW = Station(
    name="Kraków Główny",
    regiojet_city_id="1225791000",
    regiojet_station_id="6135257001",
)

GDANSK = Station(
    name="Gdańsk Główny",
    regiojet_city_id="8167554001",
    regiojet_station_id="8167535002",
)

WARSAW = Station(
    name="Warszawa Centralna",
    regiojet_city_id="2737640000",
    regiojet_station_id="7998876003",
    cd_station_name="Warszawa Centralna",
)

WROCLAW = Station(
    name="Wrocław Główny",
    regiojet_city_id="1801253000",
    regiojet_station_id="7691639003",
)

# ── Slovakia ──────────────────────────────────────────────────

BRATISLAVA = Station(
    name="Bratislava hlavná stanica",
    regiojet_city_id="10202001",
    regiojet_station_id="1841058000",
    cd_station_name="Bratislava hl.st.",
)

# ── Spain ─────────────────────────────────────────────────────

ALBACETE = Station(
    name="Albacete - Los Llanos",
    ouigo_es_id="7160600",
)

BARCELONA = Station(
    name="Barcelona - Sants",
    ouigo_es_id="7171801",
    renfe_id="0071,BARCE,null",
)

MADRID = Station(
    name="Madrid - Todas las estaciones",
    ouigo_es_id="MT1",
    renfe_id="0071,MADRI,null",
)

SEVILLE = Station(
    name="Sevilla - Santa Justa",
    ouigo_es_id="7151003",
)

VALENCIA = Station(
    name="Valencia - Joaquín Sorolla",
    ouigo_es_id="7103216",
)

ZARAGOZA = Station(
    name="Zaragoza - Delicias",
    ouigo_es_id="7104040",
)

# ── Switzerland ───────────────────────────────────────────────

ZURICH = Station(
    name="Zürich HB",
    db_id="8503000",
    cd_station_name="Zürich HB",
)

# ─────────────────────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────────────────────

ROUTES = [

    # ── Italy: selected routes Trenitalia vs. Italo ────────────────────────────
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

     Route(
        origin=TRIESTE,
        destination=ROME,
        operators=["trenitalia", "italo"],
        description="Trieste-Rome (FA)",
        route_id="trieste-rome"
    ),

    # ── Italy: Trenitalia Frecciarossa (FR) ────────────────────
    Route(
        origin=TURIN,
        destination=SALERNO,
        operators=["trenitalia"],
        description="Turin-Salerno (FR)",
        route_id="turin-salerno"
    ),
    Route(
        origin=VENICE,
        destination=SALERNO,
        operators=["trenitalia", "italo"],
        description="Venice-Salerno (FR vs. Italo)",
        route_id="venice-salerno"
    ),
    Route(
        origin=UDINE,
        destination=SALERNO,
        operators=["trenitalia"],
        description="Udine-Salerno (FR)",
        route_id="udine-salerno"
    ),
    Route(
        origin=TRIESTE,
        destination=SALERNO,
        operators=["trenitalia"],
        description="Trieste-Salerno (FR)",
        route_id="trieste-salerno"
    ),
    Route(
        origin=TURIN,
        destination=LECCE,
        operators=["trenitalia", "italo"],
        description="Turin-Lecce (Trenitalia vs. Italo)",
        route_id="turin-lecce"
    ),
    Route(
        origin=TURIN,
        destination=REGGIO_CALABRIA,
        operators=["trenitalia"],
        description="Turin-Reggio Calabria (FR)",
        route_id="turin-reggio-calabria"
    ),
    Route(
        origin=PARIS,
        destination=MILAN,
        operators=["trenitalia"],
        description="Paris-Milan (FR international)",
        route_id="paris-milan"
    ),

    # ── Italy: Trenitalia Frecciargento (FA) ───────────────────

    Route(
        origin=ROME,
        destination=GENOA,
        operators=["trenitalia"],
        description="Genoa-Rome (FA)",
        route_id="genoa-rome"
    ),
    Route(
        origin=ROME,
        destination=LECCE,
        operators=["trenitalia", "italo"],
        description="Rome-Lecce (FA vs. Italo)",
        route_id="rome-lecce"
    ),
    Route(
        origin=ROME,
        destination=REGGIO_CALABRIA,
        operators=["trenitalia"],
        description="Rome-Reggio Calabria (FA)",
        route_id="rome-reggio-calabria"
    ),

    # ── Italy: Trenitalia Frecciabianca (FB) ───────────────────
    Route(
        origin=MILAN,
        destination=GENOA,
        operators=["trenitalia", "italo"],
        description="Milan-Genoa (FB vs. Italo)",
        route_id="milan-genoa"
    ),
    Route(
        origin=ROME,
        destination=RAVENNA,
        operators=["trenitalia"],
        description="Rome-Ravenna (FB)",
        route_id="rome-ravenna"
    ),
    Route(
        origin=TURIN,
        destination=ROME,
        operators=["trenitalia"],
        description="Turin-Rome (FB)",
        route_id="turin-rome-fb"   
    ),

    # ── Italy: Italo-exclusive routes ──────────────────────────

    Route(
        origin=TURIN_PS,
        destination=ROME,
        operators=["italo"],
        description="Turin Porta Susa-Rome (Italo)",
        route_id="turin-ps-rome"
    ),
    Route(
        origin=TURIN_PS,
        destination=NAPLES,
        operators=["italo"],
        description="Turin Porta Susa-Naples (Italo)",
        route_id="turin-ps-naples"
    ),
    Route(
        origin=TURIN_PS,
        destination=SALERNO,
        operators=["italo"],
        description="Turin Porta Susa-Salerno (Italo)",
        route_id="turin-ps-salerno"
    ),

    # Milan corridors (Italo-only)
    Route(
        origin=MILAN,
        destination=SALERNO,
        operators=["italo"],
        description="Milan-Salerno (Italo)",
        route_id="milan-salerno"
    ),
    Route(
        origin=MILAN,
        destination=BARI,
        operators=["italo"],
        description="Milan-Bari (Italo)",
        route_id="milan-bari"
    ),
    Route(
        origin=MILAN,
        destination=BOLZANO,
        operators=["italo"],
        description="Milan-Bolzano (Italo)",
        route_id="milan-bolzano"
    ),

    Route(
        origin=VENICE,
        destination=ROME,
        operators=["italo"],
        description="Venice-Rome (Italo)",
        route_id="venice-rome"
    ),
    Route(
        origin=VENICE,
        destination=NAPLES,
        operators=["italo"],
        description="Venice-Naples (Italo)",
        route_id="venice-naples"
    ),
    Route(
        origin=VENICE,
        destination=TURIN_PS,
        operators=["italo"],
        description="Venice-Turin Porta Susa (Italo)",
        route_id="venice-turin-ps"
    ),

    Route(
        origin=ROME,
        destination=SALERNO,
        operators=["italo"],
        description="Rome-Salerno (Italo)",
        route_id="rome-salerno"
    ),
    Route(
        origin=ROME,
        destination=BARI,
        operators=["italo"],
        description="Rome-Bari (Italo)",
        route_id="rome-bari"
    ),

    Route(
        origin=NAPLES,
        destination=BARI,
        operators=["italo"],
        description="Naples-Bari (Italo)",
        route_id="naples-bari"
    ),
    Route(
        origin=NAPLES,
        destination=LECCE,
        operators=["italo"],
        description="Naples-Lecce (Italo)",
        route_id="naples-lecce"
    ),

    Route(
        origin=ANCONA,
        destination=MILAN,
        operators=["italo"],
        description="Ancona-Milan (Italo)",
        route_id="ancona-milan"
    ),
    Route(
        origin=ANCONA,
        destination=ROME,
        operators=["italo"],
        description="Ancona-Rome (Italo)",
        route_id="ancona-rome"
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
        origin=BARCELONA,
        destination=MADRID,
        operators=["renfe", "ouigo_es", "iryo"],
        description="Barcelona-Madrid (Renfe vs. Ouigo vs. Iryo)",
        route_id="barcelona-madrid"
    ),
    Route(
        origin=MADRID,
        destination=VALENCIA,
        operators=["renfe", "ouigo_es"],
        description="Madrid-Valencia (Renfe vs. Ouigo)",
        route_id="madrid-valencia"
    ),
    Route(
        origin=VALENCIA,
        destination=MADRID,
        operators=["renfe", "ouigo_es"],
        description="Valencia-Madrid (Renfe vs. Ouigo)",
        route_id="valencia-madrid"
    ),
    Route(
        origin=MADRID,
        destination=SEVILLE,
        operators=["renfe", "ouigo_es"],
        description="Madrid-Seville (Renfe vs. Ouigo)",
        route_id="madrid-seville"
    ),
    Route(
        origin=SEVILLE,
        destination=MADRID,
        operators=["renfe", "ouigo_es"],
        description="Seville-Madrid (Renfe vs. Ouigo)",
        route_id="seville-madrid"
    ),
    Route(
        origin=MADRID,
        destination=ZARAGOZA,
        operators=["renfe", "ouigo_es"],
        description="Madrid-Zaragoza (Renfe vs. Ouigo)",
        route_id="madrid-zaragoza"
    ),
    Route(
        origin=ZARAGOZA,
        destination=MADRID,
        operators=["renfe", "ouigo_es"],
        description="Zaragoza-Madrid (Renfe vs. Ouigo)",
        route_id="zaragoza-madrid"
    ),
    Route(
        origin=MADRID,
        destination=ALBACETE,
        operators=["ouigo_es"],
        description="Madrid-Albacete (Ouigo)",
        route_id="madrid-albacete"
    ),
    Route(
        origin=BARCELONA,
        destination=ZARAGOZA,
        operators=["renfe", "ouigo_es"],
        description="Barcelona-Zaragoza (Renfe vs. Ouigo)",
        route_id="barcelona-zaragoza"
    ),
    Route(
        origin=ZARAGOZA,
        destination=BARCELONA,
        operators=["renfe", "ouigo_es"],
        description="Zaragoza-Barcelona (Renfe vs. Ouigo)",
        route_id="zaragoza-barcelona"
    ),
    Route(
        origin=SEVILLE,
        destination=BARCELONA,
        operators=["renfe", "ouigo_es"],
        description="Seville-Barcelona (Renfe vs. Ouigo)",
        route_id="seville-barcelona"
    ),
    Route(
        origin=SEVILLE,
        destination=ZARAGOZA,
        operators=["ouigo_es"],
        description="Seville-Zaragoza (Ouigo)",
        route_id="seville-zaragoza"
    ),

    # ── France: Ouigo Grande Vitesse (OGV) ────────────────────────
    Route(
        origin=PARIS,
        destination=LYON,
        operators=["ouigo_fr", "SNCF", "trenitalia"],
        description="Paris-Lyon (Ouigo vs. SNCF vs. Trenitalia)",
        route_id="paris-lyon"
    ),
    Route(
        origin=PARIS,
        destination=MARSEILLE,
        operators=["ouigo_fr", "SNCF", "trenitalia"],
        description="Paris-Marseille (Ouigo vs. SNCF vs. Trenitalia)",
        route_id="paris-marseille"
    ),
    Route(
        origin=PARIS,
        destination=NANTES,
        operators=["ouigo_fr", "SNCF"],
        description="Paris-Nantes (Ouigo vs. SNCF)",
        route_id="paris-nantes"
    ),
    Route(
        origin=PARIS,
        destination=MONTPELLIER,
        operators=["ouigo_fr"],
        description="Paris-Montpellier (Ouigo OGV)",
        route_id="paris-montpellier"
    ),
    Route(
        origin=PARIS,
        destination=NICE,
        operators=["ouigo_fr"],
        description="Paris-Nice (Ouigo OGV)",
        route_id="paris-nice"
    ),
    Route(
        origin=PARIS,
        destination=TOULOUSE,
        operators=["ouigo_fr"],
        description="Paris-Toulouse (Ouigo OGV)",
        route_id="paris-toulouse"
    ),
    Route(
        origin=PARIS,
        destination=BORDEAUX,
        operators=["ouigo_fr"],
        description="Paris-Bordeaux (Ouigo OGV/OTC)",
        route_id="paris-bordeaux"
    ),
    Route(
        origin=PARIS,
        destination=HENDAYE,
        operators=["ouigo_fr"],
        description="Paris-Hendaye (Ouigo OGV)",
        route_id="paris-hendaye"
    ),
    Route(
        origin=PARIS,
        destination=PERPIGNAN,
        operators=["ouigo_fr"],
        description="Paris-Perpignan (Ouigo OGV)",
        route_id="paris-perpignan"
    ),
    Route(
        origin=PARIS,
        destination=RENNES,
        operators=["ouigo_fr"],
        description="Paris-Rennes (Ouigo OGV)",
        route_id="paris-rennes"
    ),
    Route(
        origin=PARIS,
        destination=STRASBOURG,
        operators=["ouigo_fr"],
        description="Paris-Strasbourg (Ouigo OGV)",
        route_id="paris-strasbourg"
    ),
    Route(
        origin=PARIS,
        destination=COLMAR,
        operators=["ouigo_fr"],
        description="Paris-Colmar (Ouigo OGV)",
        route_id="paris-colmar"
    ),
    Route(
        origin=PARIS,
        destination=BREST,
        operators=["ouigo_fr"],
        description="Paris-Brest (Ouigo OGV)",
        route_id="paris-brest"
    ),
    Route(
        origin=PARIS,
        destination=BOURG_ST_MAURICE,
        operators=["ouigo_fr"],
        description="Paris-Bourg-Saint-Maurice (Ouigo OGV, seasonal)",
        route_id="paris-bourg-st-maurice"
    ),
    Route(
        origin=PARIS,
        destination=BRUSSELS,
        operators=["ouigo_fr"],
        description="Paris-Brussels (Ouigo OGV)",
        route_id="paris-brussels-ouigo"
    ),

    # ── International ──────────────────────────────────────────

    Route(
        origin=MUNICH,
        destination=VIENNA,
        operators=["db", "oebb"],
        description="Munich-Vienna (DB vs. OeBB)",
        route_id="munich-vienna"
    ),

    # ── RegioJet + České dráhy: Czech Republic / Austria / Slovakia / Hungary ──
    Route(
        origin=PRAGUE,
        destination=VIENNA,
        operators=["regiojet", "ceske-drahy"],
        description="Prague-Vienna (RegioJet vs. CD)",
        route_id="prague-vienna"
    ),
    Route(
        origin=VIENNA,
        destination=PRAGUE,
        operators=["regiojet", "ceske-drahy"],
        description="Vienna-Prague (RegioJet vs. CD)",
        route_id="vienna-prague"
    ),
    Route(
        origin=PRAGUE,
        destination=BRATISLAVA,
        operators=["regiojet", "ceske-drahy"],
        description="Prague-Bratislava (RegioJet vs. CD)",
        route_id="prague-bratislava"
    ),
    Route(
        origin=BRATISLAVA,
        destination=PRAGUE,
        operators=["regiojet", "ceske-drahy"],
        description="Bratislava-Prague (RegioJet vs. CD)",
        route_id="bratislava-prague"
    ),
    Route(
        origin=PRAGUE,
        destination=BUDAPEST,
        operators=["regiojet", "ceske-drahy"],
        description="Prague-Budapest (RegioJet vs. CD)",
        route_id="prague-budapest"
    ),
    Route(
        origin=BUDAPEST,
        destination=PRAGUE,
        operators=["regiojet", "ceske-drahy"],
        description="Budapest-Prague (RegioJet vs. CD)",
        route_id="budapest-prague"
    ),
    Route(
        origin=PRAGUE,
        destination=OSTRAVA,
        operators=["regiojet", "ceske-drahy"],
        description="Prague-Ostrava (RegioJet)",
        route_id="prague-ostrava"
    ),
    Route(
        origin=OSTRAVA,
        destination=PRAGUE,
        operators=["regiojet", "ceske-drahy"],
        description="Ostrava-Prague (RegioJet)",
        route_id="ostrava-prague"
    ),
    Route(
        origin=PRAGUE,
        destination=BRNO,
        operators=["regiojet", "ceske-drahy"],
        description="Prague-Brno (RegioJet)",
        route_id="prague-brno",
    ),
    Route(
        origin=BRNO,
        destination=PRAGUE,
        operators=["regiojet", "ceske-drahy"],
        description="Brno-Prague (RegioJet)",
        route_id="brno-prague"
    ),

    # ── RegioJet + CD: Poland ──────────────────────────────────
    Route(
        origin=PRAGUE,
        destination=WARSAW,
        operators=["regiojet", "ceske-drahy"],
        description="Prague-Warsaw (RegioJet vs. CD)",
        route_id="prague-warsaw"
    ),
    Route(
        origin=WARSAW,
        destination=PRAGUE,
        operators=["regiojet", "ceske-drahy"],
        description="Warsaw-Prague (RegioJet vs. CD)",
        route_id="warsaw-prague"
    ),
    Route(
        origin=PRAGUE,
        destination=CRACOW,
        operators=["regiojet"],
        description="Prague-Cracow (RegioJet)",
        route_id="prague-cracow"
    ),
    Route(
        origin=CRACOW,
        destination=PRAGUE,
        operators=["regiojet"],
        description="Cracow-Prague (RegioJet)",
        route_id="cracow-prague"
    ),
    Route(
        origin=PRAGUE,
        destination=WROCLAW,
        operators=["regiojet"],
        description="Prague-Wroclaw (RegioJet)",
        route_id="prague-wroclaw"
    ),
    Route(
        origin=WROCLAW,
        destination=PRAGUE,
        operators=["regiojet"],
        description="Wroclaw-Prague (RegioJet)",
        route_id="wroclaw-prague"
    ),
    Route(
        origin=PRAGUE,
        destination=GDANSK,
        operators=["regiojet"],
        description="Prague-Gdansk (RegioJet)",
        route_id="prague-gdansk"
    ),
    Route(
        origin=GDANSK,
        destination=PRAGUE,
        operators=["regiojet"],
        description="Gdansk-Prague (RegioJet)",
        route_id="gdansk-prague"
    ),

    # ── České dráhy: Praha international ──────────────────────
    Route(
        origin=PRAGUE,
        destination=BERLIN,
        operators=["ceske-drahy"],
        description="Prague-Berlin (CD EC)",
        route_id="prague-berlin"
    ),
    Route(
        origin=BERLIN,
        destination=PRAGUE,
        operators=["ceske-drahy"],
        description="Berlin-Prague (CD EC)",
        route_id="berlin-prague"
    ),
    Route(
        origin=PRAGUE,
        destination=MUNICH,
        operators=["ceske-drahy"],
        description="Prague-Munich (CD EC)",
        route_id="prague-munich"
    ),
    Route(
        origin=MUNICH,
        destination=PRAGUE,
        operators=["ceske-drahy"],
        description="Munich-Prague (CD EC)",
        route_id="munich-prague"
    ),
    Route(
        origin=PRAGUE,
        destination=FRANKFURT,
        operators=["ceske-drahy"],
        description="Prague-Frankfurt (CD)",
        route_id="prague-frankfurt"
    ),
    Route(
        origin=FRANKFURT,
        destination=PRAGUE,
        operators=["ceske-drahy"],
        description="Frankfurt-Prague (CD)",
        route_id="frankfurt-prague"
    ),
    Route(
        origin=PRAGUE,
        destination=HAMBURG,
        operators=["ceske-drahy"],
        description="Prague-Hamburg (CD)",
        route_id="prague-hamburg"
    ),
    Route(
        origin=HAMBURG,
        destination=PRAGUE,
        operators=["ceske-drahy"],
        description="Hamburg-Prague (CD)",
        route_id="hamburg-prague"
    ),
    Route(
        origin=PRAGUE,
        destination=ZURICH,
        operators=["ceske-drahy"],
        description="Prague-Zurich (CD)",
        route_id="prague-zurich"
    ),
    Route(
        origin=ZURICH,
        destination=PRAGUE,
        operators=["ceske-drahy"],
        description="Zurich-Prague (CD)",
        route_id="zurich-prague"
    ),
    Route(
        origin=PRAGUE,
        destination=GRAZ,
        operators=["ceske-drahy"],
        description="Prague-Graz (CD)",
        route_id="prague-graz"
    ),
    Route(
        origin=GRAZ,
        destination=PRAGUE,
        operators=["ceske-drahy"],
        description="Graz-Prague (CD)",
        route_id="graz-prague"
    ),
    Route(
        origin=PRAGUE,
        destination=LINZ,
        operators=["ceske-drahy"],
        description="Prague-Linz (CD)",
        route_id="prague-linz"
    ),
    Route(
        origin=LINZ,
        destination=PRAGUE,
        operators=["ceske-drahy"],
        description="Linz-Prague (CD)",
        route_id="linz-prague"
    ),

    # ── FLX 10: Stuttgart–Frankfurt–Berlin ─────────────────────
    Route(
        origin=STUTTGART,
        destination=BERLIN,
        operators=["db", "flixtrain", "flixbus", "db_parsebot"],
        description="Stuttgart-Berlin (FLX10 vs. DB)",
        route_id="stuttgart-berlin"
    ),
    Route(
        origin=BERLIN,
        destination=STUTTGART,
        operators=["db", "flixtrain", "flixbus", "db_parsebot"],
        description="Berlin-Stuttgart (FLX10 vs. DB)",
        route_id="berlin-stuttgart"
    ),
    Route(
        origin=FRANKFURT,
        destination=BERLIN,
        operators=["db", "flixtrain", "flixbus", "db_parsebot"],
        description="Frankfurt-Berlin (FLX10 vs. DB)",
        route_id="frankfurt-berlin"
    ),
    Route(
        origin=BERLIN,
        destination=FRANKFURT,
        operators=["db", "flixtrain", "flixbus", "db_parsebot"],
        description="Berlin-Frankfurt (FLX10 vs. DB)",
        route_id="berlin-frankfurt"
    ),

    # ── FLX 10: Basel–Frankfurt–Berlin ─────────────────────────
    Route(
        origin=BASEL,
        destination=BERLIN,
        operators=["db", "flixtrain", "db_parsebot"],
        description="Basel-Berlin (FLX10 vs. DB)",
        route_id="basel-berlin"
    ),
    Route(
        origin=BERLIN,
        destination=BASEL,
        operators=["db", "flixtrain", "db_parsebot"],
        description="Berlin-Basel (FLX10 vs. DB)",
        route_id="berlin-basel"
    ),

    # ── FLX 20: Hamburg–Cologne ────────────────────────────────
    Route(
        origin=HAMBURG,
        destination=COLOGNE,
        operators=["db", "flixtrain", "flixbus", "db_parsebot"],
        description="Hamburg-Cologne (FLX20 vs. DB)",
        route_id="hamburg-cologne"
    ),
    Route(
        origin=COLOGNE,
        destination=HAMBURG,
        operators=["db", "flixtrain", "flixbus", "db_parsebot"],
        description="Cologne-Hamburg (FLX20 vs. DB)",
        route_id="cologne-hamburg"
    ),

    # ── FLX 30: Cologne–Berlin ─────────────────────────────────
    Route(
        origin=COLOGNE,
        destination=BERLIN,
        operators=["db", "flixtrain", "flixbus", "db_parsebot"],
        description="Cologne-Berlin (FLX30 vs. DB)",
        route_id="cologne-berlin"
    ),
    Route(
        origin=BERLIN,
        destination=COLOGNE,
        operators=["db", "flixtrain", "flixbus", "db_parsebot"],
        description="Berlin-Cologne (FLX30 vs. DB)",
        route_id="berlin-cologne"
    ),

    # ── FLX 35: Hamburg–Berlin, Hamburg–Leipzig ────────────────
    Route(
        origin=HAMBURG,
        destination=BERLIN,
        operators=["db", "flixtrain", "flixbus", "db_parsebot"],
        description="Hamburg-Berlin (FLX35 vs. DB)",
        route_id="hamburg-berlin"
    ),
    Route(
        origin=BERLIN,
        destination=HAMBURG,
        operators=["db", "flixtrain", "flixbus", "db_parsebot"],
        description="Berlin-Hamburg (FLX35 vs. DB)",
        route_id="berlin-hamburg"
    ),
    Route(
        origin=HAMBURG,
        destination=LEIPZIG,
        operators=["db", "flixtrain", "flixbus", "db_parsebot"],
        description="Hamburg-Leipzig (FLX35 vs. DB)",
        route_id="hamburg-leipzig"
    ),
    Route(
        origin=LEIPZIG,
        destination=HAMBURG,
        operators=["db", "flixtrain", "flixbus", "db_parsebot"],
        description="Leipzig-Hamburg (FLX35 vs. DB)",
        route_id="leipzig-hamburg"
    ),

    # ── DB domestic ────────────────────────────────────────────
    Route(
        origin=BERLIN,
        destination=DUSSELDORF,
        operators=["db"],
        description="Berlin-Dusseldorf (DB)",
        route_id="berlin-dusseldorf"
    ),
    Route(
        origin=DUSSELDORF,
        destination=BERLIN,
        operators=["db"],
        description="Dusseldorf-Berlin (DB)",
        route_id="dusseldorf-berlin"
    ),
    Route(
        origin=BERLIN,
        destination=AACHEN,
        operators=["db"],
        description="Berlin-Aachen (DB)",
        route_id="berlin-aachen"
    ),
    Route(
        origin=AACHEN,
        destination=BERLIN,
        operators=["db"],
        description="Aachen-Berlin (DB)",
        route_id="aachen-berlin"
    ),
    Route(
        origin=BERLIN,
        destination=KOBLENZ,
        operators=["db"],
        description="Berlin-Koblenz (DB)",
        route_id="berlin-koblenz"
    ),
    Route(
        origin=KOBLENZ,
        destination=BERLIN,
        operators=["db"],
        description="Koblenz-Berlin (DB)",
        route_id="koblenz-berlin"
    ),
    Route(
        origin=BERLIN,
        destination=MUNICH,
        operators=["db", "db_parsebot"],
        description="Berlin-Munich (DB)",
        route_id="berlin-munich"
    ),
    Route(
        origin=MUNICH,
        destination=BERLIN,
        operators=["db", "db_parsebot"],
        description="Munich-Berlin (DB)",
        route_id="munich-berlin"
    ),
    Route(
        origin=HAMBURG,
        destination=MUNICH,
        operators=["db", "db_parsebot"],
        description="Hamburg-Munich (DB)",
        route_id="hamburg-munich"
    ),
    Route(
        origin=MUNICH,
        destination=HAMBURG,
        operators=["db", "db_parsebot"],
        description="Munich-Hamburg (DB)",
        route_id="munich-hamburg"
    ),
    Route(
        origin=BERLIN,
        destination=ZURICH,
        operators=["db"],
        description="Berlin-Zurich (DB)",
        route_id="berlin-zurich"
    ),
    Route(
        origin=ZURICH,
        destination=BERLIN,
        operators=["db"],
        description="Zurich-Berlin (DB)",
        route_id="zurich-berlin"
    ),
    Route(
        origin=HAMBURG,
        destination=STUTTGART,
        operators=["db"],
        description="Hamburg-Stuttgart (DB)",
        route_id="hamburg-stuttgart"
    ),
    Route(
        origin=STUTTGART,
        destination=HAMBURG,
        operators=["db"],
        description="Stuttgart-Hamburg (DB)",
        route_id="stuttgart-hamburg"
    ),
    Route(
        origin=HAMBURG,
        destination=SAARBRUCKEN,
        operators=["db"],
        description="Hamburg-Saarbrucken (DB)",
        route_id="hamburg-saarbrucken"
    ),
    Route(
        origin=SAARBRUCKEN,
        destination=HAMBURG,
        operators=["db"],
        description="Saarbrucken-Hamburg (DB)",
        route_id="saarbrucken-hamburg"
    ),
    Route(
        origin=BERLIN,
        destination=SAARBRUCKEN,
        operators=["db"],
        description="Berlin-Saarbrucken (DB)",
        route_id="berlin-saarbrucken"
    ),
    Route(
        origin=SAARBRUCKEN,
        destination=BERLIN,
        operators=["db"],
        description="Saarbrucken-Berlin (DB)",
        route_id="saarbrucken-berlin"
    ),
    Route(
        origin=HAMBURG,
        destination=BASEL,
        operators=["db"],
        description="Hamburg-Basel (DB)",
        route_id="hamburg-basel"
    ),
    Route(
        origin=BASEL,
        destination=HAMBURG,
        operators=["db"],
        description="Basel-Hamburg (DB)",
        route_id="basel-hamburg"
    ),
    Route(
        origin=HAMBURG,
        destination=ZURICH,
        operators=["db"],
        description="Hamburg-Zurich (DB)",
        route_id="hamburg-zurich"
    ),
    Route(
        origin=ZURICH,
        destination=HAMBURG,
        operators=["db"],
        description="Zurich-Hamburg (DB)",
        route_id="zurich-hamburg"
    ),
    Route(
        origin=BERLIN,
        destination=BINZ,
        operators=["db"],
        description="Berlin-Ostseebad Binz (DB)",
        route_id="berlin-binz"
    ),
    Route(
        origin=BINZ,
        destination=BERLIN,
        operators=["db"],
        description="Ostseebad Binz-Berlin (DB)",
        route_id="binz-berlin"
    ),
    Route(
        origin=KIEL,
        destination=STUTTGART,
        operators=["db"],
        description="Kiel-Stuttgart (DB)",
        route_id="kiel-stuttgart"
    ),
    Route(
        origin=STUTTGART,
        destination=KIEL,
        operators=["db"],
        description="Stuttgart-Kiel (DB)",
        route_id="stuttgart-kiel"
    ),
    Route(
        origin=KIEL,
        destination=MUNICH,
        operators=["db"],
        description="Kiel-Munich (DB)",
        route_id="kiel-munich"
    ),
    Route(
        origin=MUNICH,
        destination=KIEL,
        operators=["db"],
        description="Munich-Kiel (DB)",
        route_id="munich-kiel"
    ),
    Route(
        origin=BREMEN,
        destination=MUNICH,
        operators=["db"],
        description="Bremen-Munich (DB)",
        route_id="bremen-munich"
    ),
    Route(
        origin=MUNICH,
        destination=BREMEN,
        operators=["db"],
        description="Munich-Bremen (DB)",
        route_id="munich-bremen"
    ),
    Route(
        origin=HAMBURG,
        destination=KARLSRUHE,
        operators=["db"],
        description="Hamburg-Karlsruhe (DB)",
        route_id="hamburg-karlsruhe"
    ),
    Route(
        origin=KARLSRUHE,
        destination=HAMBURG,
        operators=["db"],
        description="Karlsruhe-Hamburg (DB)",
        route_id="karlsruhe-hamburg"
    ),
    Route(
        origin=HAMBURG,
        destination=DRESDEN,
        operators=["db"],
        description="Hamburg-Dresden (DB)",
        route_id="hamburg-dresden"
    ),
    Route(
        origin=DRESDEN,
        destination=HAMBURG,
        operators=["db"],
        description="Dresden-Hamburg (DB)",
        route_id="dresden-hamburg"
    ),
    Route(
        origin=HAMBURG,
        destination=GRAZ,
        operators=["db"],
        description="Hamburg-Graz (DB)",
        route_id="hamburg-graz"
    ),
    Route(
        origin=GRAZ,
        destination=HAMBURG,
        operators=["db"],
        description="Graz-Hamburg (DB)",
        route_id="graz-hamburg"
    ),
    Route(
        origin=LUBECK,
        destination=MUNICH,
        operators=["db"],
        description="Lubeck-Munich (DB)",
        route_id="lubeck-munich"
    ),
    Route(
        origin=MUNICH,
        destination=LUBECK,
        operators=["db"],
        description="Munich-Lubeck (DB)",
        route_id="munich-lubeck"
    ),
    Route(
        origin=HAMBURG,
        destination=PASSAU,
        operators=["db"],
        description="Hamburg-Passau (DB)",
        route_id="hamburg-passau"
    ),
    Route(
        origin=PASSAU,
        destination=HAMBURG,
        operators=["db"],
        description="Passau-Hamburg (DB)",
        route_id="passau-hamburg"
    ),
    Route(
        origin=DORTMUND,
        destination=MUNICH,
        operators=["db"],
        description="Dortmund-Munich (DB)",
        route_id="dortmund-munich"
    ),
    Route(
        origin=MUNICH,
        destination=DORTMUND,
        operators=["db"],
        description="Munich-Dortmund (DB)",
        route_id="munich-dortmund"
    ),
    Route(
        origin=COLOGNE,
        destination=FRANKFURT,
        operators=["db"],
        description="Cologne-Frankfurt (DB)",
        route_id="cologne-frankfurt"
    ),
    Route(
        origin=FRANKFURT,
        destination=COLOGNE,
        operators=["db"],
        description="Frankfurt-Cologne (DB)",
        route_id="frankfurt-cologne"
    ),
    Route(
        origin=DRESDEN,
        destination=WIESBADEN,
        operators=["db"],
        description="Dresden-Wiesbaden (DB)",
        route_id="dresden-wiesbaden"
    ),
    Route(
        origin=WIESBADEN,
        destination=DRESDEN,
        operators=["db"],
        description="Wiesbaden-Dresden (DB)",
        route_id="wiesbaden-dresden"
    ),
    Route(
        origin=DORTMUND,
        destination=STUTTGART,
        operators=["db"],
        description="Dortmund-Stuttgart (DB)",
        route_id="dortmund-stuttgart"
    ),
    Route(
        origin=STUTTGART,
        destination=DORTMUND,
        operators=["db"],
        description="Stuttgart-Dortmund (DB)",
        route_id="stuttgart-dortmund"
    ),
    Route(
        origin=KARLSRUHE,
        destination=MUNICH,
        operators=["db"],
        description="Karlsruhe-Munich (DB)",
        route_id="karlsruhe-munich"
    ),
    Route(
        origin=MUNICH,
        destination=KARLSRUHE,
        operators=["db"],
        description="Munich-Karlsruhe (DB)",
        route_id="munich-karlsruhe"
    ),
    Route(
        origin=DORTMUND,
        destination=VIENNA,
        operators=["db"],
        description="Dortmund-Vienna (DB)",
        route_id="dortmund-vienna"
    ),
    Route(
        origin=VIENNA,
        destination=DORTMUND,
        operators=["db"],
        description="Vienna-Dortmund (DB)",
        route_id="vienna-dortmund"
    ),
    Route(
        origin=MUNICH,
        destination=BUDAPEST,
        operators=["db"],
        description="Munich-Budapest (DB)",
        route_id="munich-budapest"
    ),
    Route(
        origin=BUDAPEST,
        destination=MUNICH,
        operators=["db"],
        description="Budapest-Munich (DB)",
        route_id="budapest-munich"
    ),

    # ── DB international ────────────────────────────────────────

    Route(
        origin=BERLIN,
        destination=AMSTERDAM,
        operators=["db"],
        description="Berlin-Amsterdam (DB)",
        route_id="berlin-amsterdam"
    ),
    Route(
        origin=AMSTERDAM,
        destination=BERLIN,
        operators=["db"],
        description="Amsterdam-Berlin (DB)",
        route_id="amsterdam-berlin"
    ),
    Route(
        origin=FRANKFURT,
        destination=AMSTERDAM,
        operators=["db"],
        description="Frankfurt-Amsterdam (DB)",
        route_id="frankfurt-amsterdam"
    ),
    Route(
        origin=AMSTERDAM,
        destination=FRANKFURT,
        operators=["db"],
        description="Amsterdam-Frankfurt (DB)",
        route_id="amsterdam-frankfurt"
    ),
    Route(
        origin=FRANKFURT,
        destination=BRUSSELS,
        operators=["db"],
        description="Frankfurt-Brussels (DB)",
        route_id="frankfurt-brussels"
    ),
    Route(
        origin=BRUSSELS,
        destination=FRANKFURT,
        operators=["db"],
        description="Brussels-Frankfurt (DB)",
        route_id="brussels-frankfurt"
    ),
    Route(
        origin=FRANKFURT,
        destination=PARIS_EST,
        operators=["db"],
        description="Frankfurt-Paris Est (DB)",
        route_id="frankfurt-paris"
    ),
    Route(
        origin=PARIS_EST,
        destination=FRANKFURT,
        operators=["db"],
        description="Paris Est-Frankfurt (DB)",
        route_id="paris-frankfurt"
    ),
    Route(
        origin=STUTTGART,
        destination=PARIS_EST,
        operators=["db"],
        description="Stuttgart-Paris Est (DB)",
        route_id="stuttgart-paris"
    ),
    Route(
        origin=PARIS_EST,
        destination=STUTTGART,
        operators=["db"],
        description="Paris Est-Stuttgart (DB)",
        route_id="paris-stuttgart"
    ),
    Route(
        origin=FRANKFURT,
        destination=MARSEILLE,
        operators=["db"],
        description="Frankfurt-Marseille (DB)",
        route_id="frankfurt-marseille"
    ),
    Route(
        origin=MARSEILLE,
        destination=FRANKFURT,
        operators=["db"],
        description="Marseille-Frankfurt (DB)",
        route_id="marseille-frankfurt"
    ),
    Route(
        origin=FRANKFURT,
        destination=MILAN,
        operators=["db"],
        description="Frankfurt-Milan (DB)",
        route_id="frankfurt-milan"
    ),
    Route(
        origin=MILAN,
        destination=FRANKFURT,
        operators=["db"],
        description="Milan-Frankfurt (DB)",
        route_id="milan-frankfurt"
    ),
    Route(
        origin=MUNICH,
        destination=ZURICH,
        operators=["db"],
        description="Munich-Zurich (DB)",
        route_id="munich-zurich"
    ),
    Route(
        origin=ZURICH,
        destination=MUNICH,
        operators=["db"],
        description="Zurich-Munich (DB)",
        route_id="zurich-munich"
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

# Trimmed horizon set for credit-limited crawlers (e.g. db_parsebot ~167 credits/day)
# 18 routes x 6 horizons = 108 requests/day, leaves headroom under the daily credit cap
DB_PARSEBOT_HORIZONS = [1, 2, 3, 7, 14, 21]


if __name__ == "__main__":
    print(f"Total routes: {len(ROUTES)}")
    print()
    for op in ["db", "db_parsebot", "flixtrain", "trenitalia", "italo", "oebb", "ouigo_es", "renfe", "iryo", "regiojet"]:
        routes = get_routes_for_operator(op)
        if routes:
            print(f"{op.upper():<12} {len(routes)} routes:")
            for r in routes:
                print(f"  -> {r.description} [{r.route_id}]")
            print()
    print(f"Booking horizons: {BOOKING_HORIZONS} days")
    print(f"Requests/day (estimated): {len(ROUTES) * len(BOOKING_HORIZONS)}")