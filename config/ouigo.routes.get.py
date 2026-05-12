import requests
import json

headers = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# 1. Token holen
r = requests.post(
    "https://mdw.api-fr.ouigo.com/api/Token/login",
    json={"username": "ouigo.web", "password": "SquirelWeb!2020"},
    headers=headers
)
token = r.json()["token"]
print("Token OK")

# 2. Stationen abrufen
r2 = requests.get(
    "https://mdw.api-fr.ouigo.com/api/Data/GetStations",
    headers={**headers, "Authorization": f"Bearer {token}"}
)



stations=r2.json()


#top_stations = [s for s in stations if s["top_origin"] == True]



#print(f"{len(top_stations)} Top-Stationen gefunden:\n")
#for s in top_stations:
#    print(f"{s['name']:<30} | ID: {s['_u_i_c_station_code']}")
    