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

**Sidebar controls**
- **Planting season** — Fall (winter/spring/summer crop) or Summer (fall crop).
- **Region** — Statewide plus the three districts (Watsonville/Salinas, Santa Maria,
  Oxnard). Regional detail exists for *fall-planted only*; summer is statewide.
- **Group varieties by** — individual varieties, or Public vs Proprietary
  ("Proprietary" = undisclosed private varieties; named cultivars are mostly UC
  public releases).
- **View** — 100% share, absolute acres, or share-trend lines.
- **Year range** slider.

**Tabs**
- **Overview** — stacked-area / line chart for the current selection, plus KPIs
  (total acres, variety count, proprietary share, largest variety, YoY change).
- **Variety focus** — pick one or more varieties and see their trajectory across
  all districts at once, with a debut / peak / current stats table.
- **Data** — the current view as a pivot table, with a CSV download button.

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

`data/` holds three CSVs parsed from the CA Strawberry Commission acreage surveys:
- `statewide_fall_variety_acres.csv` (2009–2026)
- `statewide_summer_variety_acres.csv` (2010–2026)
- `district_fall_variety_acres.csv` (2010–2026, three districts)

To refresh, replace these files (same `year, variety, acres` / `district, year,
variety, acres` columns). The ownership grouping lives in `variety_group()` in
`app.py` if you want to reclassify any variety.
