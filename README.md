# California Strawberry Variety Dashboard

Interactive Streamlit app for exploring CA Strawberry Commission acreage-survey
variety data — by region, planting season, and variety.

## Run it

```bash
cd "Strawberry Variety Dashboard"
pip install -r requirements.txt
streamlit run app.py
```

It opens in your browser at http://localhost:8501.

## What it does

**Controls live on each tab** (the sidebar is just branding + an "About" note — there
are no global filters, so every control visibly affects the tab you're on).

Overview-tab controls:
- **Practice** — Total, Conventional, or Organic. Conventional/Organic are reported
  statewide, all plantings combined, by variety, 2021 onward (so Season/Region are
  replaced by a "statewide / all plantings" note in those modes).
- **Varieties** — *Main* (the 10 largest + “Other / minor”) or *Detailed* (every variety).
- **View** — 100% share, absolute acres, or share-trend lines.
- **Season** (Fall/Summer) and **Region** (Statewide + 3 fall districts).
- **Year range** slider.

Other tabs carry their own controls: CA Varieties Focus has a Season toggle + variety
picker + metric; the Comparison tab has a season-year slider.

**Tabs**
- **CA Varieties Overview** — stacked-area / line chart for the current selection, plus
  KPIs (total acres, variety count, proprietary share, largest variety, YoY change).
- **CA Varieties Focus** — pick one or more varieties and see their trajectory across
  all districts at once, with a debut / peak / current stats table.
- **CA · MX · FL Comparison** — strawberry planted area by growing region: a multi-source
  trend (CA/FL via NASS *and* Commission; Mexico via GAIN + Commission), a single-season
  snapshot across CA districts + Florida + Baja + Other Mexico, and qualitative Florida &
  Mexico variety notes with source links (incl. the USDA-FAS GAIN reports for Mexico).

## Password protection

The app is gated by a shared password, read from **Streamlit secrets** (never
hardcoded in `app.py`, so it stays out of your public GitHub repo).

- **Locally:** the password lives in `.streamlit/secrets.toml`:
  ```toml
  app_password = "strawbcomm_test2026"
  ```
  This file is listed in `.gitignore`, so `git` will not push it.
- **On Streamlit Community Cloud:** open your app → **Settings → Secrets** and paste
  the same line (`app_password = "strawbcomm_test2026"`), then save. The app reloads
  with the gate active.

To change the password, edit it in both places. (It's a single shared password for
all viewers — not per-user accounts.)

## Data

`data/` holds CSVs parsed from the CA Strawberry Commission acreage surveys, plus a
few multi-source regional files:
- `statewide_fall_variety_acres.csv` (2009–2026)
- `statewide_summer_variety_acres.csv` (2010–2026)
- `district_fall_variety_acres.csv` (2010–2026, three districts)
- `organic_statewide_variety_acres.csv` (2021–2026, statewide organic by variety)
- `organic_region_total.csv` (2022–2026, organic total acres by CA district)
- `regional_trend.csv` (CA/FL = USDA-NASS + Commission; Mexico = SIAP/USDA-FAS GAIN)
- `regional_snapshot.csv` (Commission North-America frame: CA districts + Florida + Baja + Other Mexico)

To refresh, replace these files (same `year, variety, acres` / `district, year,
variety, acres` columns). The ownership grouping lives in `variety_group()` in
`app.py` if you want to reclassify any variety.
