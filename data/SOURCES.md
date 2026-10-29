# Data sources

All accessed 2026-10-29 unless noted. Raw downloads are cached in `data/raw/` (git-ignored); re-run with `python -m data.run_all`.

## Study area and grid
Bounding box lat 12.85-13.25, lon 80.05-80.35 (WGS84). Grid built by us in UTM zone 44N (EPSG:32644), 250 m cells, row 0 southernmost, col 0 westernmost, exported to WGS84. The grid is the smallest UTM-aligned rectangle covering the bbox, so edge cells overhang it by up to one cell.

## Terrain
| Item | Source | URL | Licence |
|---|---|---|---|
| Elevation, slope, sink depth | Copernicus DEM GLO-30 (surface model, 30 m), AWS Open Data, tiles N12/N13 E080 | https://copernicus-dem-30m.s3.amazonaws.com/ | Copernicus DEM licence: free use with attribution. "Produced using Copernicus WorldDEM-30 (c) DLR e.V. 2010-2014 and (c) Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA; all rights reserved." |
| built_up_frac | ESA WorldCover 2021 v200, 10 m, class 50 (built-up), AWS Open Data tile N12E078 | https://esa-worldcover.s3.eu-central-1.amazonaws.com/ | CC BY 4.0. "(c) ESA WorldCover project 2021 / Contains modified Copernicus Sentinel data (2021) processed by the ESA WorldCover consortium." |

Method notes: the DEM is a surface model (buildings and trees included), warped to a 25 m grid aligned to the cells. `elevation_m` and `slope_deg` are cell means; `sink_depth_m` is the cell mean of (morphologically filled DEM minus DEM), with the raster border as outlet; `relief_m` (max-min in cell, in `features_extra.parquet`) is not part of the contract. Negative elevations occur in quarries and the sea. If WorldCover were unreachable we would fall back to a road-density proxy; it was reachable, so no proxy is used.

## OpenStreetMap
Roads, waterways and water bodies/wetlands from the Overpass API (endpoints: overpass.private.coffee, maps.mail.ru, overpass-api.de). Water = `natural=water|wetland`, `landuse=reservoir`, `waterway=riverbank` (ways and relations). `dist_drain_m` = distance from the cell centre to the nearest drain/canal/stream/river/ditch; `dist_water_m` = distance to the nearest water body or river/canal (0 if the centre lies inside one); `road_density` = km of road per km2 within the cell. Data (c) OpenStreetMap contributors, **ODbL** (https://www.openstreetmap.org/copyright): attribution is required, and derived databases must stay under ODbL.

## Rainfall
| Use | Source | Notes |
|---|---|---|
| **Historical** (event windows +/- 2 days) | Open-Meteo Historical Weather API (https://archive-api.open-meteo.com/v1/archive) | Reanalysis-based (model blend chosen by the API's default, not pinned), roughly 10-25 km. Understates extreme local rain. |
| **Forecast** (next 72 h and more; `past_days=3`) | Open-Meteo Forecast API (https://api.open-meteo.com/v1/forecast) | NWP model blend chosen by the API. |

Licence: Open-Meteo data is **CC BY 4.0**; the free API is for **non-commercial** use only (https://open-meteo.com/en/license). Attribution: "Weather data by Open-Meteo.com".
Conventions: 20 request points on a 0.1 degree lattice over the bbox; timezone Asia/Kolkata; Open-Meteo labels hourly values with the END of the hour, so we shift timestamps back one hour to the START of the hour (+05:30), `precip_mm` = accumulation in that hour. Historical and forecast come from different products, so their statistics are not identical.

## Events (events.csv)
- `2015`: 2015-11-30T00:00+05:30 to 2015-12-03T00:00+05:30. This is the 1-2 December 2015 deluge only. All hotspot sources describe that spell (Adyar breach, Chembarambakkam release). Earlier November spells (about 8-17 Nov, per https://en.wikipedia.org/wiki/2015_South_India_floods and https://www.downtoearth.org.in/urbanisation/chennai-apart-52265) also flooded parts of the city but are outside the window; flooding that happened only then is not represented.
- `2023` (Cyclone Michaung): 2023-12-03T00:00+05:30 to 2023-12-06T00:00+05:30. Heavy rain began the evening of 3 Dec and peaked on 4 Dec; water stood in the city until 6-7 Dec (see sources below). The start equals the demo replay `as_of`.
Window starts are set so that a 72 h replay from `start` covers the main rain; this is a judgement, not a fitted choice.

## Flood-extent products checked (not usable)
- **Copernicus EMS rapid mapping:** a web search found no activation for Chennai in December 2015 or for Cyclone Michaung; not confirmed on the EMS portal itself, so treat as "none found".
- **UNOSAT** published Chennai water-extent products, but from imagery dated 1 Sep, 14 Oct, 12 Nov and 24 Nov 2015 (before the 1-2 Dec peak): https://unosat.org/static/unosat_filesystem/1039/UNOSAT_A3_Chennai_Flooding_Portrait_India.pdf and the Humanitarian Data Exchange dataset. Not used as labels.
- **IWMI** flood maps (Nov 2015 only): https://www.iwmi.cgiar.org/tools/maps/floods/Flood_Chennai_Nov2015_11_24B.pdf. Not used.
- **NRSC/ISRO** RISAT-1A map for Michaung dated 7 Dec 2023 (PDF, preliminary, no machine-readable layer found): https://www.nrsc.gov.in/sites/default/files/pdf/DMSP/TN_7_12_2023_Michaung_Cyclone1of2.pdf. Not used.
So hotspot labels are named localities geocoded to one cell each (coarse; real flooding covered more cells).

## Hotspot sources (hotspots.csv / hotspot_sources.csv)
Each row's `source` column holds the URL. Articles used:
2015: https://indiawaterportal.org/governance-and-policy/governance/braving-deluge-chennais-worst-december , https://www.dtnext.in/news/chennai/flood-of-memories , https://www.thenewsminute.com/article/tn-update-rains-relent-flooding-remains-rescue-operations-stepped-36514 , https://en.wikipedia.org/wiki/2015_South_India_floods , https://thesouthfirst.com/news/chennai-floods-no-power-no-drinking-water-varadharajapuram-residents-share-tales-of-desperation
2023: https://www.deccanherald.com/india/tamil-nadu/floating-cars-submerged-localities-chennai-battles-floods-in-the-wake-of-cyclone-michuang-2796547 , https://www.deccanherald.com/india/tamil-nadu/cyclone-michaung-chennai-hit-by-heavy-rains-low-lying-areas-inundated-2795516 , https://www.thenewsminute.com/tamil-nadu/bodies-found-inside-homes-and-floating-in-flooded-streets-in-chennai , https://www.thenewsminute.com/tamil-nadu/why-flood-water-in-chennai-did-not-drain-for-days , https://citizenmatters.in/devastation-storm-chennai-cyclone-michaung-monsoon-flooding/ , https://swarajyamag.com/tamil-nadu/first-thing-was-no-power-how-these-chennai-residents-survived-72-hours-of-downpour
Rules followed: a locality is included only if one of these articles names it as flooded, waterlogged or inundated in that event; names mentioned only for power cuts, closures or cut-off roads were left out. Pages were read by us (some via automated summaries, then spot-checked against the page text); the articles are cited, not reproduced.
Geocoding: Nominatim (https://nominatim.openstreetmap.org, OSM data under ODbL), 1 request/second, bounded to the study bbox, results cached in `data/raw/nominatim/`. Unmatched localities are dropped and logged in `data/processed/hotspots_geocode_log.csv`. Nominatim sometimes returns an administrative-zone centroid (for example "Adyar"), which is coarse.
