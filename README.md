# Rail Data Hub

Automatisiertes Tool zur Erfassung und Analyse von Preis- und Kapazitätsdaten im europäischen Schienenpersonenfernverkehr.

## Projektübersicht

Dieses Tool sammelt regelmäßig Daten von verschiedenen Bahnanbietern (DB, Flixtrain, Trenitalia, ÖBB, SNCF) und ermöglicht eine systematische Wettbewerbsanalyse anhand von Preis- und Kapazitätsentwicklungen.

**Forschungsfrage:** Wie entwickelt sich der Wettbewerb im europäischen Schienenpersonenfernverkehr?

## Team



## Projektstruktur
```
rail-data-hub/
├── crawlers/           # Operator-spezifische Webcrawler
│   ├── base/           # Basis-Crawler-Klasse
│   ├── db/             # Deutsche Bahn
│   ├── flixtrain/      # Flixtrain
│   ├── trenitalia/     # Trenitalia
│   ├── oebb/           # ÖBB
│   └── sncf/           # SNCF
├── database/
│   ├── timescaledb/    # Schema & Migrations
│   └── duckdb/         # Analytische Queries
├── dashboard/          # UI & Visualisierung
├── analysis/           # Wettbewerbsanalyse-Module
├── docs/               # Handbuch & Lastenheft
├── tests/              # Tests
└── config/             # Konfiguration & Scheduling
```

## Technologie-Stack

| Komponente | Technologie | Zweck |
|------------|-------------|-------|
| Scraping | Python, BeautifulSoup | Datenabruf |
| Scheduling | APScheduler | Automatisierung |
| Datenbank (Schreiben) | TimescaleDB | Zeitreihenspeicherung |
| Datenbank (Analyse) | DuckDB | Analytische Queries |
| Dashboard | TBD | Visualisierung |

## Setup

### Voraussetzungen

- [Python 3.13+](https://python.org/downloads) – beim Installieren "Add to PATH" aktivieren
- [Docker Desktop](https://docker.com/products/docker-desktop) – für die lokale Datenbank
- [Git](https://git-scm.com) – Versionskontrolle
- [VSCode](https://code.visualstudio.com) – empfohlener Editor

### 1. Repository klonen
```bash
git clone https://github.com/Xaver-M/Rail-Data-Hub.git
cd Rail-Data-Hub
```

### 2. Python-Umgebung einrichten
```bash
py -m pip install -r requirements.txt
```

### 3. Umgebungsvariablen einrichten
```bash
copy .env.example .env
```

Dann `.env` öffnen und Werte eintragen – Passwort von Xaver erfragen.

### 4. Datenbank starten
```bash
docker-compose up -d
```

Die Datenbank läuft jetzt lokal auf Port 5432. Beim ersten Start wird das Schema automatisch angelegt.

### 5. Verbindung testen
```bash
py -c "import psycopg2; conn = psycopg2.connect(host='localhost', dbname='rail_data', user='rail_user', password='DEIN_PASSWORT'); print('Datenbankverbindung erfolgreich!')"
```

### Datenbank stoppen
```bash
docker-compose down
```

## Git-Workflow

Wir arbeiten **nie direkt auf `main`**. Der Workflow ist immer:
```
1. Neuen Branch erstellen:   git checkout -b feature/mein-feature
2. Änderungen machen & committen
3. Branch pushen:            git push origin feature/mein-feature
4. Pull Request auf GitHub erstellen
5. Review von mindestens 1 Teammitglied
6. Merge in main
```

### Commit-Konventionen
```
feat:     Neues Feature
fix:      Bugfix
docs:     Dokumentation
refactor: Code-Umbau ohne neue Funktion
test:     Tests hinzufügen
```

## Datenquellen

| Anbieter | Quelle | Methode |
|----------|--------|---------|
| Deutsche Bahn | DB API Marketplace | Offizielle API |
| ÖBB | Open Data Portal (GTFS) | Offizielle API |
| SNCF | SNCF Developer API | Offizielle API |
| Trenitalia | ViaggiaTreno | Inoffizielle API |
| Flixtrain | Website + | Offizielle API |

*Die Methode ist bisher nur der Stand einer kurzen Recherche, APIs sind verfügbar, genauere Analyse der bereitgestellten Informationen nötig. Vermutlich je nach Website js. Scraper nötig um Auslastungs- und Preisdaten zu erhalten.

Ziel / Plan ist es das GTFS Format (https://gtfs.org/) zur Skalierbarkeit beizubehalten.

## Wichtige Dateien

| Datei | Zweck |
|-------|-------|
| `.env` | Lokale "Settings" – **niemals committen!** |
| `.env.example` | Vorlage für `.env` |
| `docker-compose.yml` | Startet lokale TimescaleDB |
| `requirements.txt` | Python-Abhängigkeiten |