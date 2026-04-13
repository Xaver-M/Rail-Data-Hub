import requests
import json
from datetime import datetime, timedelta

BASE_URL = "https://www.lefrecce.it/Channels.Website.BFF.WEB/website"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Content-Type": "application/json",
    "Accept": "application/json"
}

# ─────────────────────────────────────────
# Schritt 1: Bahnhofs-IDs suchen
# ─────────────────────────────────────────
def get_station_id(name: str) -> dict:
    url = f"{BASE_URL}/locations/search?name={name}&limit=3"
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    results = resp.json()
    if not results:
        raise ValueError(f"Keine Station gefunden für: {name}")
    station = results[0]
    print(f"  ✓ {name} → '{station['name']}' (ID: {station['id']})")
    return station

# ─────────────────────────────────────────
# Schritt 2: Verbindungen + Preise suchen
# ─────────────────────────────────────────
def search_connections(departure_id: int, arrival_id: int, date: datetime) -> dict:
    url = f"{BASE_URL}/ticket/solutions"
    payload = {
        "departureLocationId": departure_id,
        "arrivalLocationId": arrival_id,
        "departureTime": date.strftime("%Y-%m-%dT%H:%M:%S.000+01:00"),
        "adults": 1,
        "children": 0,
        "criteria": {
            "frecceOnly": False,
            "regionalOnly": False,
            "noChanges": True,       # Nur Direktverbindungen
            "order": "DEPARTURE_DATE",
            "limit": 10,
            "offset": 0
        },
        "advancedSearchRequest": {
            "bestFare": False        # Alle Preisklassen zurückgeben
        }
    }
    resp = requests.post(url, json=payload, headers=HEADERS)
    resp.raise_for_status()
    return resp.json()

# ─────────────────────────────────────────
# Schritt 3: Ergebnisse ausgeben
# ─────────────────────────────────────────
def print_results(data: dict):
    solutions = data.get("solutions", [])
    print(f"\nGefunden: {len(solutions)} Verbindungen\n")
    print(f"{'Abfahrt':<8} {'Ankunft':<8} {'Zug':<20} {'Preis':<10} {'Status':<12} {'Min. Tickets'}")
    print("-" * 75)

    for s in solutions:
        sol = s.get("solution", {})
        dep = sol.get("departureTime", "")[:16].replace("T", " ")
        arr = sol.get("arrivalTime", "")[:16].replace("T", " ")

        # Zugname aus nodes
        trains = sol.get("nodes", [])
        train_name = trains[0].get("train", {}).get("name", "?") if trains else "?"
        train_cat = trains[0].get("train", {}).get("trainCategory", "?") if trains else "?"

        # Günstigster Preis
        price_obj = sol.get("price", {})
        price = f"{price_obj.get('amount', '?')} {price_obj.get('currency', '')}" if price_obj else "?"

        status = sol.get("status", "?")

        # Minimale verfügbare Tickets über alle grids/offers
        min_available = None
        for grid in s.get("grids", []):
            for service in grid.get("services", []):
                for offer in service.get("offers", []):
                    avail = offer.get("availableAmount")
                    if avail is not None and avail != 32767:  # 32767 = unnumerierte Plätze
                        if min_available is None or avail < min_available:
                            min_available = avail

        avail_str = str(min_available) if min_available is not None else "k.A."

        print(f"{dep[11:]:<8} {arr[11:]:<8} {train_cat+' '+train_name:<20} {price:<10} {status:<12} {avail_str}")

# ─────────────────────────────────────────
# Main
# ─────────────────────────────────────────
if __name__ == "__main__":
    target_date = datetime.now() + timedelta(days=7)
    print(f"Trenitalia Test: Milano → Roma am {target_date.strftime('%d.%m.%Y')}")
    print("=" * 60)

    # Bahnhofs-IDs holen
    print("\nSuche Bahnhofs-IDs...")
    milano = get_station_id("Milano Centrale")
    roma = get_station_id("Roma Termini")

    # Verbindungen suchen
    print(f"\nSuche Verbindungen...")
    data = search_connections(milano["id"], roma["id"], target_date)

    # Rohe Antwort speichern für Analyse
    with open("trenitalia_response.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print("Rohe Antwort gespeichert in: trenitalia_response.json")

    # Ergebnisse ausgeben
    print_results(data)