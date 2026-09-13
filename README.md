# SG Nature Park Parking

**Where to park at every Singapore nature park — built entirely from official government data.**

A driver's companion for Singapore's nature reserves, nature parks, nature areas and the
Southern Ridges. For each park it answers the questions that actually matter before you
drive out: *is there a car park, how many lots, is it free, is it open when I arrive, will
my vehicle fit through the gantry — and if the park has no car park, where do I leave the car?*

## What it shows

- **Park boundaries** (official NParks managed-area polygons) and park markers at the
  coordinates NParks publishes on each park page.
- **Published car park capacity per park** — lot counts, motorcycle / handicapped / bus-coach
  lots, free or paid, car park opening hours, no-overnight-parking restrictions, quoted
  straight from each park's official NParks page.
- **HDB car park fallback** — every HDB car park within 2 km of the park, sorted by
  straight-line distance, with free-parking days/hours, night parking, short-term parking
  rules, parking system, deck count and **gantry height**.
- **Vehicle-height warning** — enter your vehicle height and any HDB car park with a lower
  gantry is flagged red on the map and in the list (van/lorry drivers, this one is for you).
- **Official OneMap + Google directions** links, and a direct link to the park's NParks page.
- Filters: nature reserves / nature parks / nature areas / Southern Ridges, has in-park car
  park, free parking, no car park published, HDB fallback under 500 m. Sorting by distance
  (with geolocation), name, most car lots, or nearest HDB car park.
- **Mobile-first layout** — verified at a 390 px phone viewport: map on top with the park list
  below, park detail opens as a full-screen panel, the lot-count table restacks into labelled
  rows instead of overflowing, the legend collapses to a tap-to-open pill, and the data/method
  footer becomes a bottom sheet.
- **Suggested routes (official)** — named trails and distances from each park's own NParks map
  (e.g. Thomson's Langur 0.15 km / Ruins & Figs 1.50 km, Sungei Buloh's Coastal 1.3 km /
  Migratory Bird 1.95 km), a one-tap **Open official park map (PDF)** link, and the official
  trail network for every park (total km, bike-friendly km, wheelchair-accessible km,
  staircases) drawn on the map via an "Official trail routes" toggle — green = cycling,
  grey dashed = walking.

## Coverage

25 parks, 28 car parks, **1,332 published car park lots**, and **862 HDB car parks** within
2 km of a park — covering 4 nature reserves, 10 nature parks, 6 nature areas and 5 Southern
Ridges / Labrador-network parks.

## Data sources — all official

| Source | Agency | Used for |
|---|---|---|
| [NParks Parks and Nature Reserves](https://data.gov.sg/datasets/d_77d7ec97be83d44f61b85454f844382f/view) `d_77d7ec97be83d44f61b85454f844382f` | NParks | Park / reserve boundary polygons |
| [NParks Car Park Lots](https://data.gov.sg/datasets/d_d5594e4c43e838380155f05f53f58567/view) `d_d5594e4c43e838380155f05f53f58567` | NParks | Mapped car park lot boundaries (indicative) |
| [HDB Carpark Information](https://data.gov.sg/datasets/d_23f946fa557947f93a8043bbef41dd09/view) `d_23f946fa557947f93a8043bbef41dd09` | HDB | HDB car parks, rules, gantry heights, SVY21 coordinates |
| [NParks park pages](https://www.nparks.gov.sg/visit/parks) | NParks | Published car park counts, free/paid, car park hours, park hours, address, coordinates |
| [Nature park networks & areas](https://www.nparks.gov.sg/visit/when-visiting-parks/about-parks-nature-reserves-pcns/nature-park-networks-areas) | NParks | Official nature park / nature area classification |

Dataset use falls under the [Singapore Open Data Licence](https://data.gov.sg/open-data-licence).
Base maps are OpenStreetMap / OpenTopoMap / CARTO tiles (open data, ODbL).

## Method and caveats

- Car park lot counts, free/paid status and car park hours are **quoted** from each park's
  official NParks page — they are not estimates.
- HDB coordinates are supplied in **SVY21** and converted to WGS84 (`EPSG:3414` → `EPSG:4326`).
  The conversion was verified against the SVY21 origin point and cross-checked against an
  independent map source (median error ≈ 15 m).
- **Distances are straight-line**, not driving distances. Use the OneMap link for an official
  route.
- "Car park lots mapped by NParks" is derived by grouping the official lot-boundary layer
  (~2.5 m between lots in a row, ~25 m across an aisle) and is **indicative, not a capacity
  guarantee**. That layer does not cover most nature park car parks.
- Where NParks publishes no parking details for a park, the site says so plainly instead of
  guessing, and shows officially mapped and HDB alternatives.
- Always check on-site signage. Parking rules at nature reserves can change (e.g. seasonal
  or event closures).

## Running locally

```bash
python -m http.server 8899 --bind 127.0.0.1
# open http://127.0.0.1:8899/index.html
```

The page works from `file://` too, since the dataset is loaded from `data/data.js`.

## Automation

`tools/park_parking_refresh.py` refreshes the whole site from the official sources:
re-downloads the three data.gov.sg datasets, re-scrapes the NParks park pages, rebuilds
`data/parks.json` + `data/data.js`, and commits and pushes to GitHub Pages if anything
changed. It is wired to a Hermes cron job on the 1st of each month, prints a short
summary on stdout (progress goes to stderr), and exits non-zero on failure so the
scheduler raises an alert. Run it by hand any time:

```bash
python tools/park_parking_refresh.py
```

## Repository layout

```
index.html                       single-page app (Leaflet + vanilla JS, no build step)
data/data.js                     dataset as a JS global (works offline / file://)
data/parks.json                  the same dataset as plain JSON
make_data_js.py                  regenerates data/data.js from data/parks.json
tools/park_parking_refresh.py    monthly refresh + publish job
```

_Data captured 2026-09-13._
