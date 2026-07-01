"""
geocode_stations.py — Geocodes all stations in config/routes.py via OpenStreetMap
Nominatim, then computes Haversine (great-circle) distances for all ROUTES.

Usage:
    PYTHONPATH=. python3 analysis/geocode_stations.py

Output:
    config/station_coordinates.py   -- lat/lon per station (review before committing!)
    analysis/route_distances.csv    -- route_id, origin, destination, haversine_km

Notes:
    - Nominatim usage policy: max 1 request/second, descriptive User-Agent required.
    - Results are cached in analysis/_geocode_cache.json — re-runs are fast.
    - Spot-check config/station_coordinates.py after first run (display_name column).
    - SEARCH_OVERRIDES maps internal station names to better Nominatim search terms.
"""

import sys, os, time, json, math
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import requests
from config.routes import ROUTES

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT    = "RailDataHub/1.0 (KIT research project; github.com/Xaver-M/Rail-Data-Hub)"
CACHE_FILE    = os.path.join(os.path.dirname(__file__), "_geocode_cache.json")

# Internal names that Nominatim won't find — map to a better search query
SEARCH_OVERRIDES = {
    "Lyon toutes gares":                  "Lyon-Perrache, Lyon, France",
    "Paris - Toutes les gares":           "Paris Gare de Lyon, Paris, France",
    "Montpellier toutes gares":           "Montpellier-Saint-Roch, Montpellier, France",
    "Madrid - Todas las estaciones":      "Madrid Puerta de Atocha, Madrid, Spain",
    "Barcelona - Sants":                  "Barcelona Sants, Barcelona, Spain",
    "Madrid - Todas las estaciones":      "Madrid Atocha, Madrid, Spain",
    "Valencia - Joaquín Sorolla":         "Valencia Joaquin Sorolla, Valencia, Spain",
    "Zaragoza - Delicias":                "Zaragoza Delicias, Zaragoza, Spain",
    "Sevilla - Santa Justa":              "Sevilla Santa Justa, Sevilla, Spain",
    "Albacete - Los Llanos":              "Albacete Los Llanos, Albacete, Spain",
    "Albacete - Los Llanos":              "Albacete, Spain",
    "Reggio Emilia AV Mediopadana":       "Reggio Emilia, Italy",
    "Latisana Lignano Bibione":           "Latisana, Italy",
    "Frankfurt(Main)Hbf":                 "Frankfurt Hauptbahnhof, Frankfurt, Germany",
    "München Hbf":                        "München Hauptbahnhof, Munich, Germany",
    "Köln Hbf":                           "Köln Hauptbahnhof, Cologne, Germany",
    "Zürich HB":                          "Zürich Hauptbahnhof, Zurich, Switzerland",
    "Bratislava hlavná stanica":          "Bratislava hlavna stanica, Bratislava, Slovakia",
    "Praha hlavní nádraží":               "Praha hlavni nadrazi, Prague, Czech Republic",
    "Brno hlavní nádraží":                "Brno hlavni nadrazi, Brno, Czech Republic",
    "Ostrava hlavní nádraží":             "Ostrava hlavni nadrazi, Ostrava, Czech Republic",
    "Kraków Główny":                      "Krakow Glowny, Krakow, Poland",
    "Gdańsk Główny":                      "Gdansk Glowny, Gdansk, Poland",
    "Warszawa Centralna":                 "Warszawa Centralna, Warsaw, Poland",
    "Wrocław Główny":                     "Wroclaw Glowny, Wroclaw, Poland",
    "Firenze Santa Maria Novella":        "Firenze Santa Maria Novella, Florence, Italy",
    "Venezia Santa Lucia":                "Venezia Santa Lucia, Venice, Italy",
    "Venezia Mestre":                     "Venezia Mestre, Venice, Italy",
    "Reggio di Calabria Centrale":        "Reggio Calabria Centrale, Reggio Calabria, Italy",
    "Roma Termini":                       "Roma Termini, Rome, Italy",
    "Roma Tiburtina":                     "Roma Tiburtina, Rome, Italy",
    "Napoli Centrale":                    "Napoli Centrale, Naples, Italy",
    "Milano Centrale":                    "Milano Centrale, Milan, Italy",
    "Torino Porta Nuova":                 "Torino Porta Nuova, Turin, Italy",
    "Torino Porta Susa":                  "Torino Porta Susa, Turin, Italy",
    "Genova Piazza Principe":             "Genova Piazza Principe, Genoa, Italy",
    "Genova Brignole":                    "Genova Brignole, Genoa, Italy",
    "Budapest-Keleti":                    "Budapest Keleti, Budapest, Hungary",
    "Wien Hbf":                           "Wien Hauptbahnhof, Vienna, Austria",
    "Brussels-Midi":                      "Bruxelles-Midi, Brussels, Belgium",
}


def load_cache() -> dict:
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_cache(cache: dict) -> None:
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def geocode(name: str, cache: dict) -> dict | None:
    if name in cache:
        return cache[name]

    query = SEARCH_OVERRIDES.get(name, name)
    params = {"q": query, "format": "json", "limit": 1, "addressdetails": 0}
    headers = {"User-Agent": USER_AGENT}

    try:
        resp = requests.get(NOMINATIM_URL, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        results = resp.json()
    except Exception as e:
        print(f"  ERROR: '{name}' -> '{query}': {e}")
        return None

    if not results:
        print(f"  NOT FOUND: '{name}' (searched: '{query}')")
        return None

    result = {
        "lat":          float(results[0]["lat"]),
        "lon":          float(results[0]["lon"]),
        "display_name": results[0].get("display_name", ""),
        "search_query": query,
    }
    cache[name] = result
    return result


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0088
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi    = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def collect_unique_stations() -> dict:
    stations = {}
    for route in ROUTES:
        for st in (route.origin, route.destination):
            if st.name not in stations:
                stations[st.name] = st
    return stations


def main():
    stations = collect_unique_stations()
    print(f"{len(stations)} unique stations found in ROUTES\n")

    cache   = load_cache()
    results = {}

    for i, (name, _) in enumerate(sorted(stations.items()), 1):
        if name in cache:
            print(f"[{i:>3}/{len(stations)}] (cached) {name}")
            results[name] = cache[name]
            continue

        print(f"[{i:>3}/{len(stations)}] geocoding: {name}")
        geo = geocode(name, cache)
        if geo:
            results[name] = geo
            print(f"         -> {geo['lat']:.4f}, {geo['lon']:.4f}  |  {geo['display_name'][:65]}")
        save_cache(cache)
        time.sleep(1.1)

    missing = [n for n in stations if n not in results]
    if missing:
        print(f"\nWARNING: {len(missing)} stations not geocoded — fill in manually:")
        for n in missing:
            print(f"  - {n}")

    # Write config/station_coordinates.py
    out_coords = os.path.join(os.path.dirname(__file__), "..", "config", "station_coordinates.py")
    with open(out_coords, "w", encoding="utf-8") as f:
        f.write('"""\nAuto-generated by analysis/geocode_stations.py — REVIEW BEFORE USE.\n'
                'Maps station display name -> (lat, lon) via OpenStreetMap Nominatim.\n"""\n\n')
        f.write("STATION_COORDINATES: dict[str, tuple[float, float]] = {\n")
        for name in sorted(results):
            geo = results[name]
            f.write(f'    {name!r}: ({geo["lat"]:.6f}, {geo["lon"]:.6f}),')
            f.write(f'  # {geo["display_name"][:65]}\n')
        f.write("}\n")
    print(f"\nWrote {out_coords}  ({len(results)} stations)")

    # Write analysis/route_distances.csv
    out_csv = os.path.join(os.path.dirname(__file__), "route_distances.csv")
    written, missing_routes = 0, 0
    with open(out_csv, "w", encoding="utf-8") as f:
        f.write("route_id,origin,destination,haversine_km\n")
        for route in ROUTES:
            o = results.get(route.origin.name)
            d = results.get(route.destination.name)
            if not o or not d:
                f.write(f"{route.route_id},{route.origin.name},{route.destination.name},NA\n")
                missing_routes += 1
                continue
            dist = haversine_km(o["lat"], o["lon"], d["lat"], d["lon"])
            f.write(f"{route.route_id},{route.origin.name},{route.destination.name},{dist:.4f}\n")
            written += 1
    print(f"Wrote {out_csv}  ({written} routes with distance, {missing_routes} NA)")


if __name__ == "__main__":
    main()