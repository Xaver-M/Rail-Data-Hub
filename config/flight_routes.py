# config/flight_routes.py
# Flight corridors for the intermodal comparison (air vs. rail/bus).
#
# IMPORTANT: route_id deliberately matches the rail route_id in config/routes.py,
# so air and rail observations can be joined on price_observations.route_id.
# Corridors without a rail crawler (e.g. barcelona-paris) are air-only for now.

from dataclasses import dataclass, field


@dataclass
class FlightRoute:
    route_id: str                            # matches Route.route_id in config/routes.py (if rail exists)
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
    "VCE": "Europe/Rome",
    "TSF": "Europe/Rome",
    # Spain
    "MAD": "Europe/Madrid",
    "BCN": "Europe/Madrid",
    # France
    "CDG": "Europe/Paris",
    "ORY": "Europe/Paris",
    "BVA": "Europe/Paris",
    "NCE": "Europe/Paris",
    "LYS": "Europe/Paris",
    # United Kingdom
    "LHR": "Europe/London",
    "LGW": "Europe/London",
    "STN": "Europe/London",
    "LTN": "Europe/London",
    # Benelux
    "BRU": "Europe/Brussels",
    "CRL": "Europe/Brussels",
    "AMS": "Europe/Amsterdam",
    # Central / Eastern Europe
    "VIE": "Europe/Vienna",
    "MUC": "Europe/Berlin",
    "BER": "Europe/Berlin",
    "PRG": "Europe/Prague",
    "BUD": "Europe/Budapest",
    "BTS": "Europe/Bratislava",
    "WAW": "Europe/Warsaw",
    "WMI": "Europe/Warsaw",
    "OTP": "Europe/Bucharest",
}

AIRPORT_NAMES = {
    "LIN": "Milano Linate",
    "MXP": "Milano Malpensa",
    "BGY": "Milano Bergamo",
    "FCO": "Roma Fiumicino",
    "CIA": "Roma Ciampino",
    "VCE": "Venezia Marco Polo",
    "TSF": "Treviso",
    "MAD": "Madrid Barajas",
    "BCN": "Barcelona El Prat",
    "CDG": "Paris Charles de Gaulle",
    "ORY": "Paris Orly",
    "BVA": "Paris Beauvais",
    "NCE": "Nice Côte d'Azur",
    "LYS": "Lyon Saint-Exupéry",
    "LHR": "London Heathrow",
    "LGW": "London Gatwick",
    "STN": "London Stansted",
    "LTN": "London Luton",
    "BRU": "Brussels Airport",
    "CRL": "Brussels South Charleroi",
    "AMS": "Amsterdam Schiphol",
    "VIE": "Wien Schwechat",
    "MUC": "München",
    "BER": "Berlin Brandenburg",
    "PRG": "Praha Václav Havel",
    "BUD": "Budapest Liszt Ferenc",
    "BTS": "Bratislava",
    "WAW": "Warszawa Chopin",
    "WMI": "Warszawa Modlin",
    "OTP": "București Henri Coandă",
}


# ─────────────────────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────────────────────
# Original corridors: test runs 07.10.2026; return directions Rome-Milan and
# Nice-Paris 19.11.2026. IRG case-study corridors: test run 23.11.2026
# (horizons 14 + 45, cabin bag) over all candidate airports; only pairs with
# nonstop flights are listed.
# No nonstop flights (pruned, both directions): MXP/BGY-FCO, all -CIA pairs,
# EIN/RTM-Paris, LCY-Paris, LGW/STN/LTN-ORY, LGW/LCY/STN/LTN-Brussels, CRL-AMS/CDG/ORY,
# BGY-CDG/ORY, LIN-BVA, AMS-ORY/BVA, BTS-PRG, BTS-WAW.
# Stockholm-Oslo: ARN-OSL is served, but the result page is not parsed
# correctly (0 flights) -> left out until fixed.


def _both_ways(fwd_id: str, desc: str, pairs: list[tuple[str, str]],
               rail: list[str]) -> list[FlightRoute]:
    """Outbound corridor + return corridor with reversed airport pairs."""
    a, b = fwd_id.split("-", 1)
    rev_id = f"{b}-{a}"
    da, db = desc.split("-", 1)
    rail_txt = f" (air vs. {'/'.join(rail)})" if rail else " (air only)"
    return [
        FlightRoute(route_id=fwd_id, description=f"{da}-{db}{rail_txt}",
                    airport_pairs=list(pairs), rail_operators=list(rail)),
        FlightRoute(route_id=rev_id, description=f"{db}-{da}{rail_txt}",
                    airport_pairs=[(d, o) for o, d in pairs], rail_operators=list(rail)),
    ]


FLIGHT_ROUTES = [
    # ── Original corridors ──
    *_both_ways("milan-rome", "Milan-Rome", [("LIN", "FCO")], ["trenitalia", "italo"]),
    *_both_ways("madrid-barcelona", "Madrid-Barcelona", [("MAD", "BCN")], ["ouigo_es"]),
    *_both_ways("paris-nice", "Paris-Nice", [("ORY", "NCE"), ("CDG", "NCE")], ["ouigo_fr"]),

    # ── IRG case studies: international high speed ──
    *_both_ways("london-paris", "London-Paris",
                [("LHR", "CDG"), ("LHR", "ORY"), ("LGW", "CDG"), ("STN", "CDG"), ("LTN", "CDG")], ["eurostar"]),
    *_both_ways("london-brussels", "London-Brussels", [("LHR", "BRU")], ["eurostar"]),
    *_both_ways("amsterdam-paris", "Amsterdam-Paris", [("AMS", "CDG")], ["eurostar"]),
    *_both_ways("amsterdam-brussels", "Amsterdam-Brussels", [("AMS", "BRU")], ["eurostar"]),
    *_both_ways("brussels-paris", "Brussels-Paris", [("BRU", "CDG")], ["eurostar"]),
    *_both_ways("milan-paris", "Milan-Paris",
                [("LIN", "CDG"), ("LIN", "ORY"), ("MXP", "CDG"), ("MXP", "ORY"), ("MXP", "BVA"), ("BGY", "BVA")],
                ["trenitalia"]),
    *_both_ways("barcelona-paris", "Barcelona-Paris", [("BCN", "CDG"), ("BCN", "ORY"), ("BCN", "BVA")], []),

    # ── IRG case studies: domestic high speed ──
    *_both_ways("paris-lyon", "Paris-Lyon", [("CDG", "LYS")], ["ouigo_fr", "trenitalia"]),

    # ── IRG case studies: night trains ──
    *_both_ways("brussels-vienna", "Brussels-Vienna", [("BRU", "VIE"), ("CRL", "VIE")], []),
    *_both_ways("brussels-prague", "Brussels-Prague", [("BRU", "PRG"), ("CRL", "PRG")], ["european_sleeper"]),
    *_both_ways("vienna-venice", "Vienna-Venice", [("VIE", "VCE"), ("VIE", "TSF")], []),
    *_both_ways("budapest-warsaw", "Budapest-Warsaw", [("BUD", "WAW"), ("BUD", "WMI")], ["regiojet", "ceske-drahy"]),
    *_both_ways("budapest-prague", "Budapest-Prague", [("BUD", "PRG")], ["regiojet", "ceske-drahy"]),
    *_both_ways("bratislava-warsaw", "Bratislava-Warsaw", [("BTS", "WMI")], ["regiojet", "ceske-drahy"]),

    # ── IRG case studies: long distance ──
    *_both_ways("vienna-munich", "Vienna-Munich", [("VIE", "MUC")], []),
    *_both_ways("vienna-prague", "Vienna-Prague", [("VIE", "PRG")], ["regiojet", "ceske-drahy"]),
    *_both_ways("vienna-budapest", "Vienna-Budapest", [("VIE", "BUD")], ["regiojet", "ceske-drahy"]),
    *_both_ways("prague-warsaw", "Prague-Warsaw", [("PRG", "WAW")], ["regiojet", "ceske-drahy"]),
    *_both_ways("berlin-warsaw", "Berlin-Warsaw", [("BER", "WAW")], ["pkp_intercity"]),
    *_both_ways("budapest-bucharest", "Budapest-Bucharest", [("BUD", "OTP")], []),
]


# ─────────────────────────────────────────────────────────────
# HORIZONS & FARE VARIANTS
# ─────────────────────────────────────────────────────────────

# Every second rail horizon (agreed with IRG 11/2026); all are also rail horizons,
# so horizon curves stay directly comparable. One-way flights only.
FLIGHT_HORIZONS = [1, 3, 5, 7, 14, 30, 60, 90]

# carry_on_bags value -> stored in fare_class.
# "economy_nobag"    = cheapest headline fare (often personal item only)
# "economy_cabinbag" = fare incl. 1 cabin bag -> closer to rail, which includes luggage
BAG_VARIANTS = {
    0: "economy_nobag",
    1: "economy_cabinbag",
}
