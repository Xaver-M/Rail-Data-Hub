# config/flight_routes.py
# Flight corridors for the intermodal comparison (air vs. rail/bus).
#
# IMPORTANT: route_id deliberately matches the rail route_id in config/routes.py,
# so air and rail observations can be joined on price_observations.route_id.

from dataclasses import dataclass, field

from config.routes import BOOKING_HORIZONS


@dataclass
class FlightRoute:
    route_id: str                            # must match Route.route_id in config/routes.py
    description: str
    airport_pairs: list[tuple[str, str]]     # (origin IATA, destination IATA), nonstop only
    rail_operators: list[str] = field(default_factory=list)  # documentation only


# ─────────────────────────────────────────────────────────────
# AIRPORTS
# ─────────────────────────────────────────────────────────────

# Google Flights returns local airport times -> needed to build TIMESTAMPTZ
AIRPORT_TZ = {
    # Italy
    "LIN": "Europe/Rome",
    "MXP": "Europe/Rome",
    "BGY": "Europe/Rome",
    "FCO": "Europe/Rome",
    "CIA": "Europe/Rome",
    # Spain
    "MAD": "Europe/Madrid",
    "BCN": "Europe/Madrid",
    # France
    "CDG": "Europe/Paris",
    "ORY": "Europe/Paris",
    "NCE": "Europe/Paris",
}

AIRPORT_NAMES = {
    "LIN": "Milano Linate",
    "MXP": "Milano Malpensa",
    "BGY": "Milano Bergamo",
    "FCO": "Roma Fiumicino",
    "CIA": "Roma Ciampino",
    "MAD": "Madrid Barajas",
    "BCN": "Barcelona El Prat",
    "CDG": "Paris Charles de Gaulle",
    "ORY": "Paris Orly",
    "NCE": "Nice Côte d'Azur",
}


# ─────────────────────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────────────────────
# Test runs 07.10.2026 (horizons 7 + 30, both bag variants, nonstop only):
#   LIN-FCO  ITA Airways                    ~8-10 flights/day
#   MAD-BCN  Iberia, Vueling, Air Europa    ~11-14 flights/day
#   BCN-MAD  Iberia, Vueling                ~11 flights/day
#   ORY-NCE  Transavia, easyJet             ~9-12 flights/day
#   CDG-NCE  Air France                     ~8-9 flights/day
# No nonstop flights: MXP-FCO, BGY-FCO, LIN-CIA, MXP-CIA, BGY-CIA (pruned).
# -> 5 pairs x 14 horizons x 2 bag variants = 140 queries/day, ~13 min runtime.

FLIGHT_ROUTES = [
    FlightRoute(
        route_id="milan-rome",
        description="Milan-Rome (air vs. Trenitalia/Italo)",
        airport_pairs=[("LIN", "FCO")],
        rail_operators=["trenitalia", "italo"],
    ),
    FlightRoute(
        route_id="madrid-barcelona",
        description="Madrid-Barcelona (air vs. OUIGO ES)",
        airport_pairs=[("MAD", "BCN")],
        rail_operators=["ouigo_es"],
    ),
    FlightRoute(
        route_id="barcelona-madrid",
        description="Barcelona-Madrid (air vs. OUIGO ES)",
        airport_pairs=[("BCN", "MAD")],
        rail_operators=["ouigo_es"],
    ),
    FlightRoute(
        route_id="paris-nice",
        description="Paris-Nice (air vs. OUIGO FR)",
        airport_pairs=[("ORY", "NCE"), ("CDG", "NCE")],
        rail_operators=["ouigo_fr"],
    ),
]


# ─────────────────────────────────────────────────────────────
# HORIZONS & FARE VARIANTS
# ─────────────────────────────────────────────────────────────

# Same 14 horizons as rail -> horizon curves are directly comparable
FLIGHT_HORIZONS = BOOKING_HORIZONS

# carry_on_bags value -> stored in fare_class.
# "economy_nobag"    = cheapest headline fare (often personal item only)
# "economy_cabinbag" = fare incl. 1 cabin bag -> closer to rail, which includes luggage
BAG_VARIANTS = {
    0: "economy_nobag",
    1: "economy_cabinbag",
}
