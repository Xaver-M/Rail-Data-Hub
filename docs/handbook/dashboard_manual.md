# Rail Data Hub — User Manual

> This manual explains the features of the Rail Data Hub dashboard and is intended for all users of the portal — regardless of technical background.

**Dashboard URL:** http://193.196.37.50:8501

---

## Contents

1. [Getting Started](#1-getting-started)
2. [Navigation & Layout](#2-navigation--layout)
3. [Route Selection](#3-route-selection)
4. [Overview](#4-overview)
5. [Individual Train](#5-individual-train)
6. [Booking Horizon](#6-booking-horizon)
7. [Time of Day](#7-time-of-day)
8. [Operator Comparison](#8-operator-comparison)
9. [€/km & €/h](#9-km--h)
10. [Crawler Status](#10-crawler-status)
11. [Price Basis Toggle](#11-price-basis-toggle)
12. [Offline Mode](#12-offline-mode)
13. [Methodological Notes](#13-methodological-notes)

---

## 1. Getting Started

The dashboard opens on the **Landing Page**, which provides an overview of the entire project:

- **Key Results** — automatically calculated highlights from the dataset (early booking effect, lowest price, most observed route)
- **Data Growth** — cumulative growth curve of the database over the project lifetime
- **Data Density** — overview of which operators are well covered at which booking horizons
- **Covered Operators** — all 10 operators with collection period and record count
- **Analysis Modules** — brief explanation of what can be analysed in each tab

To begin analysing, click **"Analyse"** in the left sidebar.

---

## 2. Navigation & Layout

### Sidebar (left panel)

The sidebar is always visible and contains:

| Element | Function |
|---|---|
| **🇩🇪 DE / 🇬🇧 EN** | Language switch (German / English) |
| **⚡ Live · TimescaleDB** | Indicates that the database connection is active |
| **⚠ Offline · local snapshot** | Indicates that the dashboard is running in offline mode |
| **Start** | Return to the landing page |
| **Analyse** | Main analysis area (5 tabs) |
| **Operator Comparison** | Direct comparison across operators |
| **Crawler Status** | System health and data availability |
| **Observations / Last** | Number of records and last crawl time for the selected route |
| **Reload data** | Clears the cache and reloads all data from the database |

### Tabs (Analysis area)

The analysis area contains five tabs:

```
📊 Overview  |  🚆 Individual Train  |  ⏱ Booking Horizon  |  🕐 Time of Day  |  📐 €/km & €/h
```

---

## 3. Route Selection

The route selector appears at the top of the main area as soon as you open an analysis tab.

### Filters

Two optional filters sit above the route dropdowns:

**🌍 Country** — filters available routes by the country of the departure or arrival station. Multiple selections are possible. Example: selecting "🇮🇹 Italy" shows only routes with a start or end in Italy.

**🚄 Operator** — filters for routes served by a specific operator. The operator list adjusts dynamically to the selected countries — only operators running on the filtered routes are shown.

**✕ Reset** — clears all filters.

A small indicator below the filters shows how many routes remain after filtering (e.g. "🔍 12 of 144 routes").

### Cascading Dropdowns

After filtering, the route is selected in two steps:

1. **Departure** — choose the origin station from the (filtered) list
2. **Arrival** — the destination dropdown automatically shows only stations reachable from the selected origin

To the right of the dropdowns, the following are displayed immediately:
- **Coloured operator badges** — which operators have data on this route
- **Number of observations** and **last crawl timestamp**

---

## 4. Overview

The Overview tab shows the price development on a route over time.

### View mode

At the top of the tab, two view modes are available:

**📍 Whole route** — aggregated view across all trains and departure times. Best for a general picture of how prices have developed over weeks.

**🚆 Single trip** — prices for a specific departure date. Shows how prices for trains on that date varied across booking horizons.

### KPI cards

The key metrics for the selected route and time range are displayed at the top of the tab:

| KPI | Meaning |
|---|---|
| **Lowest price** | Cheapest observed ticket in the selected period, with the corresponding operator |
| **Average price** | Mean price across all observations |
| **Highest price** | Most expensive observed fare |
| **Trend (last 7d)** | Price change over the last 7 days compared to the prior period |
| **Operators** | Number of operators with data on this route |
| **€/km** | Average price per straight-line kilometre |
| **€/h** | Average price per hour of travel |

### Time range

The slider sets the analysis window from 7 to 90 days back.

### Charts

**Price timeline** — line chart showing the selected price basis (MIN/AVG/MAX) per operator per day. Hovering over a data point shows MIN, AVG and MAX simultaneously.

**Price range Min/Avg/Max** — shows the spread between the cheapest and most expensive observed fare for each operator. The diamond marks the average.

**Connections by departure hour** — how many connections were crawled per hour? Gives an indication of the daily coverage.

---

## 5. Individual Train

The Individual Train tab analyses the price history of a specific train service.

### Selection

1. Choose an **operator**
2. Choose **connection type**:
   - **All** — direct and connecting services
   - **Direct only** — direct connections only (train numbers without `+`)
   - **With transfer** — connecting services only (train numbers with `+`, e.g. "ICE 144 + ICE 2311")
3. Choose a **train** from the filtered list

### KPI cards

| KPI | Meaning |
|---|---|
| **Current price** | Most recently observed price for this train |
| **Min / Max** | Cheapest and most expensive price ever observed |
| **7-day change** | Price change over the last 7 days |
| **Seats available** | Most recently reported seat availability (where provided) |

### Charts

**Price history over observation period** — how did the price of this train change day by day? The dashed line shows the average.

**Surcharge over lowest price** — bar chart showing by how many percent the price at late booking exceeds the lowest observed price. Green = cheap, red = expensive.

**Absolute price by booking horizon** — line chart showing the same information in absolute euro values. The dashed line marks the lowest ever observed price.

**Recommendation** — automatically generated note showing at which booking horizon the train was typically cheapest and how much more one pays by booking late.

---

## 6. Booking Horizon

The Booking Horizon tab shows how prices change depending on how far in advance the ticket is purchased — the core research question of the project.

### Optimal booking time

Cards at the top of the tab show for each operator:
- At how many days in advance the price was cheapest
- How much can be saved by booking early compared to the latest booking

### Charts

**Average price by booking horizon** — line chart comparing all operators. The x-axis shows days before departure (90 on the left, 1 on the right). An upward slope towards the right means: the later you book, the more you pay.

**Connections per horizon** — bar chart showing how many observations exist per horizon. Thin bars at a horizon indicate a smaller data basis.

**Detail table** — full pivot table of operator x horizon with exact prices.

### Interpretation

- A **steep upward slope** from left to right (90d → 1d) indicates aggressive dynamic pricing
- A **flat curve** means stable prices regardless of booking time
- **Anomalies** (e.g. cheaper prices close to departure) may indicate last-minute discounts

---

## 7. Time of Day

The Time of Day tab investigates whether certain departure times or weekdays are systematically cheaper or more expensive.

### Select operator

Since departure times are operator-specific, an operator must be selected first.

### Charts

**Price by departure hour** — bar chart showing the average price (or MIN/MAX depending on the toggle) per departure hour. Colours range from green (cheap) to red (expensive).

**Heatmap weekday x hour** — two-dimensional colour map that considers weekday and departure hour simultaneously. Dark = cheap, light = expensive.

**Available seats by hour** — shows average seat availability per departure hour (where provided).

### KPI cards

Below the charts, the cheapest and most expensive hour and the cheapest and most expensive weekday are automatically identified.

### ⚠ Important note on data coverage

The Deutsche Bahn crawler only queries connections in the morning window (approximately 08:00-13:15 departure time). For DB, no evening or night connections will appear — this reflects the crawler's fixed query window, not the actual timetable.

---

## 8. Operator Comparison

The Operator Comparison tab enables direct price comparison across operators on a shared route.

### Select booking horizon

The slider sets the comparison point (e.g. +30 days before departure). All charts and metrics then refer to bookings at that point in time.

### KPI cards

| KPI | Meaning |
|---|---|
| **Cheapest operator** | Operator with the lowest minimum price at the selected horizon |
| **Most expensive operator** | Operator with the highest minimum price |
| **Max. savings** | Price difference between cheapest and most expensive operator |

### Charts

**Min/Avg/Max at +Xd** — bar chart showing the price range for each operator at the selected horizon.

**Extra cost vs. cheapest operator** — shows the percentage surcharge of each operator compared to the cheapest.

**Operator profile (radar)** — spider chart evaluating four dimensions simultaneously: cheap price, price stability, availability, data density.

**Available seats by horizon** — line chart showing how seat availability decreases as departure approaches.

---

## 9. €/km & €/h

This tab normalises prices by distance and travel time to enable fair comparison across routes of different lengths.

### Why normalise?

A ticket for €50 sounds expensive — but for a 600 km route that is only €0.083/km, which is cheap. Without normalisation, prices for different routes cannot be meaningfully compared.

### Connection type filter

As in the Individual Train tab, you can filter between direct connections and connecting services. Recommendation: for €/h analyses, select "Direct only", as transfer waiting times strongly inflate travel duration.

### Charts

**€/km by booking horizon** — how does the price per kilometre change with lead time?

**€/h by booking horizon** — how does the price per hour of travel change with lead time?

**Scatter: €/km vs. €/h** — scatter plot showing both dimensions simultaneously. Operators in the bottom-left are cheap on both metrics.

**Boxplot: €/km distribution** — shows the statistical spread of €/km values per operator across all horizons.

### Note on distances

Distances are based on the **straight-line Haversine distance** between departure and arrival station. Actual rail distances are typically 15–25% longer. €/km values are therefore not equivalent to actual cost per kilometre travelled, but enable a consistent relative comparison.

---

## 10. Crawler Status

The Crawler Status tab provides an overview of the health of the data collection system.

### Data overview

- **Total records** — all price observations stored to date
- **Operators** — active data sources
- **Routes** — configured routes
- **Last crawl** — when data was last collected

### Bar chart: records per operator

Shows the total number of observations per operator. Differences are explained by:
- Number of configured routes per operator
- Crawling start date (newer operators have less data)
- API availability (frequent errors → fewer records)
- Timetable density (Flixtrain operates only 3 daily departures on most routes)

### 7-day health indicator

| Symbol | Meaning |
|---|---|
| ✅ | Operator delivered data on ≥6 of the last 7 days |
| ⚠️ | Operator delivered data on 3-5 of the last 7 days |
| ❌ | Operator delivered data on ≤2 of the last 7 days |

### Status per operator

Tabular overview with last crawl time, total record count, number of routes and average price per operator.

---

## 11. Price Basis Toggle

All analysis tabs include a toggle to switch between three price bases:

| Option | Meaning | Recommended use |
|---|---|---|
| **Minimum** | Cheapest observed price per group | Yield management analysis, booking recommendation |
| **Average** | Mean of all observations | General price level, trend analysis |
| **Maximum** | Most expensive observed price | Price range, worst-case analysis |

**Recommendation for scientific analysis:** The **Minimum** is the most robust basis for yield management studies, as it reflects the actually bookable entry price at each point in time — regardless of which trains were crawled on which day.

---

## 12. Offline Mode

When no database connection is available (e.g. running locally without Docker), the dashboard automatically switches to **offline mode**. The sidebar will show:

```
⚠ Offline · local snapshot
```

In offline mode, all data is read from a local CSV file (`data/snapshot.csv`). All analysis functions are available, but the data reflects the state at the time the snapshot was taken and is not updated live.

---

## 13. Methodological Notes

### Price basis

All analyses default to the **cheapest available fare** (`MIN(price_eur)`) per route, horizon and collection day. Standardisation:
- 1 adult
- 2nd class or economy fare
- Single journey
- No railcards or additional services

### Fare classes

The `fare_class` column is operator-specific and not directly comparable across operators:
- **Italo:** internal product class codes
- **Trenitalia:** offer names
- **RegioJet:** `vehicleStandardKey`
- **DB / Flixtrain / OUIGO:** fixed strings or empty

For cross-operator comparisons, only `price_eur` is used.

### Booking horizons

The 14 booking horizons (1, 2, 3, 4, 5, 6, 7, 10, 14, 21, 30, 45, 60, 90 days) are fixed. The actual gap between `collected_at` and `departure_at` may deviate by ±1-2 days, as crawls do not run at exactly the target horizon.

### Distances

€/km calculations are based on the **Haversine straight-line distance** between departure and arrival station. Actual rail distances are 15-25% longer. Values are suitable for relative comparison, not for absolute cost calculations.

### Time zones

All timestamps are stored in **UTC**. Exception: Trenitalia stores departure times in local time (`Europe/Rome`), which may cause slight offsets in time-of-day analyses.

### Weekday effect at RegioJet

RegioJet operates different service frequencies depending on the day of the week (more trains at weekends). This causes fluctuations in daily record counts and is not a crawler issue.