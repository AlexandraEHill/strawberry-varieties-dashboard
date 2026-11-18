"""
California Strawberry Variety Dashboard
Explore CA Strawberry Commission acreage-survey variety data by region, season,
and variety. Run locally with:  streamlit run app.py
Data: CA Strawberry Commission acreage surveys (variety x region x year, acres).
"""
from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="CA Strawberry Varieties", page_icon="🍓", layout="wide")
DATA = Path(__file__).parent / "data"

FALL_REGIONS = ["Statewide", "Watsonville/Salinas", "Santa Maria", "Oxnard"]
PALETTE = (px.colors.qualitative.Safe + px.colors.qualitative.Vivid
           + px.colors.qualitative.Bold + px.colors.qualitative.Alphabet)


# ----------------------------------------------------------------- access gate
def check_password():
    """Simple shared-password gate. Password is read from Streamlit secrets
    (key `app_password`), so it is never committed in the source code."""
    try:
        expected = st.secrets["app_password"]
    except Exception:
        expected = None
    if not expected:
        st.error("This app's password isn't configured yet. Add `app_password` to "
                 "`.streamlit/secrets.toml` (local) or the app's **Settings → Secrets** "
                 "(Streamlit Cloud).")
        st.stop()

    def _entered():
        st.session_state.auth_ok = st.session_state.get("pw", "") == expected
        if st.session_state.auth_ok:
            st.session_state.pop("pw", None)

    if st.session_state.get("auth_ok"):
        return
    st.markdown("### 🍓 California Strawberry Variety Explorer")
    st.text_input("Access password", type="password", key="pw", on_change=_entered)
    if st.session_state.get("auth_ok") is False:
        st.error("Incorrect password.")
    st.caption("Enter the access password to continue.")
    st.stop()


check_password()


# ----------------------------------------------------------------- data
@st.cache_data
def load_data():
    sf = pd.read_csv(DATA / "statewide_fall_variety_acres.csv").assign(season="Fall", region="Statewide")
    ss = pd.read_csv(DATA / "statewide_summer_variety_acres.csv").assign(season="Summer", region="Statewide")
    dd = (pd.read_csv(DATA / "district_fall_variety_acres.csv")
          .rename(columns={"district": "region"}).assign(season="Fall"))
    cols = ["season", "region", "year", "variety", "acres"]
    df = pd.concat([sf[cols], ss[cols], dd[cols]], ignore_index=True)
    df["year"] = df["year"].astype(int)
    df["acres"] = df["acres"].fillna(0.0)
    return df


df = load_data()


@st.cache_data
def load_extra():
    ov = pd.read_csv(DATA / "organic_statewide_variety_acres.csv")      # year, variety, acres (all organic)
    ort = pd.read_csv(DATA / "organic_region_total.csv")               # region, year, organic_acres
    rtrend = pd.read_csv(DATA / "regional_trend.csv")                  # region, year, acres, source
    rsnap = pd.read_csv(DATA / "regional_snapshot.csv")               # region, year, acres, group
    return ov, ort, rtrend, rsnap


ov, ort, rtrend, rsnap = load_extra()


def practice_variety(practice):
    """Statewide, all-plantings variety acres for Conventional / Organic (2021+)."""
    tot = df[df.region == "Statewide"].groupby(["year", "variety"], as_index=False).acres.sum()
    org = ov.rename(columns={"acres": "org"})
    if practice == "Organic":
        return org.rename(columns={"org": "acres"})[["year", "variety", "acres"]]
    m = tot.merge(org, on=["year", "variety"], how="left")
    m = m[m.year.isin(ov.year.unique())]
    m["org"] = m["org"].fillna(0)
    m["acres"] = (m.acres - m.org).clip(lower=0)
    return m[["year", "variety", "acres"]]


MAIN_N = 10
COLOR_OVERRIDES = {"Proprietary": "#7a2648", "Other / minor": "#b9bec4",
                   "Other": "#b9bec4", "Unreported / Underreported": "#d4d8dd"}


def top_keys(frame, n):
    tot = frame.groupby("key").acres.sum().sort_values(ascending=False)
    return list(tot.index[:n])


def collapse_minor(frame, keep):
    f = frame.copy()
    f["key"] = f.key.where(f.key.isin(keep), "Other / minor")
    return f.groupby(["year", "key"], as_index=False).acres.sum()


def group_sub(long_df, lo, hi):
    """Long [year,variety,acres] -> grouped [year,key,acres], year-filtered, zero-varieties dropped."""
    s = long_df[(long_df.year >= lo) & (long_df.year <= hi)][["year", "variety", "acres"]].copy()
    s["key"] = s.variety
    s = s.groupby(["year", "key"], as_index=False).acres.sum()
    nz = s.groupby("key").acres.sum()
    return s[s.key.isin(nz[nz > 0].index)]


def make_plot(sub, grouping):
    keep = top_keys(sub, MAIN_N)
    pdf = collapse_minor(sub, keep) if grouping == "Main varieties" else sub.copy()
    pdf["share"] = pdf.acres / pdf.groupby("year").acres.transform("sum") * 100
    keys = sorted(dict.fromkeys(pdf.key))
    cmap = {k: PALETTE[i % len(PALETTE)] for i, k in enumerate(keys)}
    for sp, col in COLOR_OVERRIDES.items():
        if sp in cmap:
            cmap[sp] = col
    return pdf, cmap


def show_kpis(sub):
    yr = int(sub.year.max())
    latest, prev = sub[sub.year == yr], sub[sub.year == yr - 1]
    tot_now, tot_prev = latest.acres.sum(), prev.acres.sum()
    prop = (latest[latest.key == "Proprietary"].acres.sum() / tot_now * 100) if tot_now else 0
    top = latest.sort_values("acres", ascending=False).key.iloc[0] if len(latest) else "—"
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(f"Total acres ({yr})", f"{tot_now:,.0f}",
              f"{(tot_now - tot_prev) / tot_prev * 100:+.1f}% vs {yr-1}" if tot_prev else None)
    c2.metric("Varieties reported", int((latest.acres > 0).sum()))
    c3.metric("Proprietary share", f"{prop:.0f}%")
    c4.metric("Largest variety", top)


# ----------------------------------------------------------------- sidebar (branding / about only)
st.sidebar.title("🍓 Strawberry varieties")
st.sidebar.caption("Data on strawberry varieties and acreage from: CA Strawberry Commission acreage surveys · USDA-NASS · USDA-FAS GAIN")
with st.sidebar.expander("About & how to use", expanded=False):
    st.markdown(
        "This dashboard consists of three tabs: **.\n\n"
        "- **CA Varieties Overview** — California planted strawberry varieties over time & "
        "(by cov/org, season, region, year).\n"
        "- **CA Varieties Focus** — Examine one or more varieties across districts and time.\n"
        "- **CA · FL · MX Comparison** — CA vs. Florida vs. Mexico planted area, plus Florida & "
        "Mexico variety notes (its own sources).")
#st.sidebar.markdown("---")
#st.sidebar.caption("District variety detail = fall-planted only. "
#                   "Conventional / organic splits = statewide, all plantings, 2021+.")

st.title("California Strawberry Variety Explorer")
tab_overview, tab_variety, tab_regional = st.tabs(
    ["📊 CA Varieties Overview", "🔎 CA Varieties Focus", "🗺 CA · FL · MX Comparison"])

# ----------------------------------------------------------------- Overview
with tab_overview:
    practice = st.radio("Practice", ["Total", "Conventional", "Organic"], horizontal=True, key="ov_practice",
                        help="Conventional / Organic are reported statewide, all plantings combined, "
                             "by variety, 2021 onward.")
    cc = st.columns(4)
    grouping = cc[0].radio("Varieties", ["Main varieties", "Detailed varieties"], key="ov_grp")
    view = cc[1].selectbox("View", ["Share (100%)", "Acres", "Share trend lines"], key="ov_view")
    if practice == "Total":
        season = cc[2].radio("Season", ["Fall", "Summer"], horizontal=True, key="ov_season")
        if season == "Fall":
            region = cc[3].selectbox("Region", FALL_REGIONS, key="ov_region")
        else:
            region = "Statewide"
            cc[3].markdown("**Region**"); cc[3].caption("Statewide — summer is statewide-only")
        base = df[(df.season == season) & (df.region == region)][["year", "variety", "acres"]]
        scope = f"{season}-planted · {region}"
    else:
        season, region = "All plantings", "Statewide"
        cc[2].markdown("**Scope**"); cc[2].caption("Statewide")
        cc[3].markdown("**Plantings**"); cc[3].caption("All plantings combined · 2021+")
        base = practice_variety(practice)
        scope = f"{practice} · statewide · all plantings"
    yopts = sorted(base.year.unique())
    yr_lo, yr_hi = st.select_slider("Year range", options=yopts, value=(yopts[0], yopts[-1]), key="ov_years")
    st.caption(f"**{scope}** · {yr_lo}–{yr_hi}")

    osub = group_sub(base, yr_lo, yr_hi)
    if osub.empty:
        st.info("No data for this selection. Conventional/Organic are available 2021 onward — widen the year range.")
    else:
        show_kpis(osub)
        pdf, cmap = make_plot(osub, grouping)
        order = top_keys(pdf, 99)
        if view == "Share (100%)":
            fig = px.area(pdf, x="year", y="share", color="key", color_discrete_map=cmap,
                          category_orders={"key": order}, labels={"share": "Share of acreage (%)", "key": "Variety"})
            fig.update_yaxes(range=[0, 100], ticksuffix="%")
        elif view == "Acres":
            fig = px.area(pdf, x="year", y="acres", color="key", color_discrete_map=cmap,
                          category_orders={"key": order}, labels={"acres": "Acres", "key": "Variety"})
        else:
            fig = px.line(pdf, x="year", y="share", color="key", color_discrete_map=cmap,
                          category_orders={"key": order}, markers=True,
                          labels={"share": "Share of acreage (%)", "key": "Variety"})
            fig.update_yaxes(ticksuffix="%")
        fig.update_layout(height=540, hovermode="x unified", legend_title="")
        fig.update_traces(hovertemplate=("%{fullData.name}: %{y:,.0f} ac<extra></extra>" if view == "Acres"
                                         else "%{fullData.name}: %{y:.1f}%<extra></extra>"))
        st.plotly_chart(fig, use_container_width=True)
        if grouping == "Main varieties":
            st.caption(f"The {MAIN_N} largest varieties shown individually; the rest grouped as "
                       "“Other / minor”. Switch to *Detailed varieties* above to break these out.")
        else:
            st.caption("Every reported variety shown individually — including minor cultivars, experimental "
                       "selections (breeding codes), and the “Other” / “Unreported” catch-alls. "
                       "“Proprietary” = undisclosed private varieties (e.g., Driscoll's-type).")

# ----------------------------------------------------------------- Variety focus
with tab_variety:
    st.subheader("Track a variety across regions")
    vseason = st.radio("Season", ["Fall", "Summer"], horizontal=True, key="vf_season")
    st.caption("Fall-planted is compared across Statewide + the three districts. "
               "Summer-planted is statewide only (a single line)." if vseason == "Fall"
               else "Summer-planted is statewide only, so this shows a single line — "
               "switch to Fall for the district comparison.")
    pool = df[df.season == vseason]
    variety_opts = (pool.groupby("variety").acres.sum().sort_values(ascending=False))
    variety_opts = [v for v in variety_opts.index if variety_opts[v] > 0]
    default = [v for v in ["Monterey", "Albion", "Proprietary", "Fronteras", "Eclipse"] if v in variety_opts][:3]
    picks = st.multiselect("Varieties", variety_opts, default=default or variety_opts[:2])

    if picks:
        regions = FALL_REGIONS if vseason == "Fall" else ["Statewide"]
        vf = df[(df.season == vseason) & (df.region.isin(regions)) & (df.variety.isin(picks))].copy()
        tot = (df[(df.season == vseason) & (df.region.isin(regions))]
               .groupby(["region", "year"], as_index=False).acres.sum().rename(columns={"acres": "tot"}))
        vf = vf.merge(tot, on=["region", "year"], how="left")
        vf["share"] = vf.acres / vf.tot * 100
        metric = st.radio("Metric", ["Share (%)", "Acres"], horizontal=True, key="vf_metric")
        ycol, ylab = ("share", "Share of region acreage (%)") if metric == "Share (%)" else ("acres", "Acres")
        fig = px.line(vf.sort_values("year"), x="year", y=ycol, color="region",
                      facet_col="variety", facet_col_wrap=3, markers=True,
                      category_orders={"region": regions, "variety": picks}, labels={ycol: ylab})
        fig.update_layout(height=420 if len(picks) <= 3 else 760, legend_title="Region")
        fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
        fig.update_traces(hovertemplate=("%{fullData.name}: %{y:.1f}%<extra></extra>" if metric == "Share (%)"
                                         else "%{fullData.name}: %{y:,.0f} ac<extra></extra>"))
        if metric == "Share (%)":
            fig.update_yaxes(ticksuffix="%")
        st.plotly_chart(fig, use_container_width=True)

        # stats
        rows = []
        for (v, r), g in vf.groupby(["variety", "region"]):
            g = g.sort_values("year")
            nz = g[g.acres > 0]
            if nz.empty:
                continue
            peak = g.loc[g.share.idxmax()]
            cur = g.loc[g.year.idxmax()]
            rows.append({"Variety": v, "Region": r, "Debut": int(nz.year.min()),
                         "Peak share": f"{peak.share:.1f}% ({int(peak.year)})",
                         f"{int(cur.year)} share": f"{cur.share:.1f}%",
                         f"{int(cur.year)} acres": f"{cur.acres:,.0f}"})
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("Pick one or more varieties above.")

# ----------------------------------------------------------------- Regional acreage
with tab_regional:
    st.subheader("Regional Trends: CA · Florida · Mexico")
    st.caption("Compares **total planted area** across regions and data sources.")

    st.markdown("**Trend — planted area over time (thousand acres)**")
    rt = rtrend.copy()
    rt["acres_k"] = rt.acres / 1000
    figt = px.line(rt.sort_values("year"), x="year", y="acres_k", color="region", line_dash="source",
                   markers=True,
                   color_discrete_map={"California": "#d6453f", "Florida": "#5b9bd5", "Mexico": "#f5b724"},
                   line_dash_map={"NASS (planted)": "solid", "USDA-FAS GAIN": "solid", "Commission (reported)": "dash"},
                   category_orders={"source": ["NASS (planted)", "USDA-FAS GAIN", "Commission (reported)"]},
                   labels={"acres_k": "Planted area (1,000 ac)", "region": "", "source": "Source"})
    figt.update_layout(height=450, hovermode="x unified", legend_title="")
    figt.update_traces(hovertemplate="%{fullData.name}: %{y:.1f}k ac<extra></extra>")
    st.plotly_chart(figt, use_container_width=True)
    st.caption(
        "**How to read Florida vs. California.** USDA-NASS *acres planted* (solid) shows planted acreage "
        "for both states on a consistent basis. On that basis Florida (~17k ac, 2025) is roughly a third "
        "of California (~46k ac). The **Commission (reported)** series (dashed) runs higher for Florida "
        "because it includes tax-collector *ranch* acres (including greenbelt / non-planted land); "
        "for California it is the commission survey's total reported acreage and tracks NASS closely. "
        "Mexico: Data comes from the USDA-FAS GAIN annual reports on national area (ha→ac, solid) "
        "plus the Commission's North-America estimate (Baja + Other, dashed, last two seasons); "
        "the series agree closely at ~37k ac. (Links to the GAIN reports are at the bottom of this page.)")

    st.divider()
    st.markdown("**Snapshot: A single year by detailed region**")
    snap_years = sorted(rsnap.year.unique())
    snap_yr = st.select_slider("Season (year)", options=snap_years, value=snap_years[-1])
    s = rsnap[rsnap.year == snap_yr].sort_values("acres", ascending=True)
    figs = px.bar(s, x="acres", y="region", color="group", orientation="h",
                  color_discrete_map={"California": "#d6453f", "Florida": "#5b9bd5", "Mexico": "#f5b724"},
                  labels={"acres": "Planted acres", "region": "", "group": ""})
    figs.update_layout(height=430)
    figs.update_traces(hovertemplate="%{y}: %{x:,.0f} ac<extra></extra>")
    st.plotly_chart(figs, use_container_width=True)
    st.caption("CA = Commission district acreage (fall + summer). Florida = Commission tax-collector ranch "
               "acreage. Mexico (Baja + Other) = industry estimates in the Commission survey — reported only "
               "for the last two seasons. Measures differ by region; treat cross-region levels as indicative.")

    st.divider()
    st.subheader("Florida & Mexico variety trends")
    st.caption("Neither Florida nor Mexico publishes a CA-style variety-acreage survey, so these are "
               "qualitative — named cultivars and directional shifts from USDA and trade sources.")

    with st.expander("🌴 Florida: Shifts to new varieties", expanded=True):
        st.markdown(
            "Florida's mix mirrors California's old→new transition, driven by UF/IFAS releases:\n\n"
            "- **Florida Radiance** — once dominant (~75% of acreage pre-2018), now largely displaced.\n"
            "- **Florida Brilliance** — the new leader, ~55–60% of acreage in recent seasons.\n"
            "- **Sweet Sensation® ‘Florida127’** — rising through 2022, now ~25–30%.\n"
            "- **Medallion™** — a 2020 release gaining ground (~20%).\n"
            "- **Festival / Florida Beauty** — older, fading.\n\n"
            "Shares are approximate spot estimates, not a consistent annual series.\n\n"
            "**Sources**\n"
            "- [UF/IFAS — breeding program & Radiance ~75% (2016)](https://blogs.ifas.ufl.edu/news/2016/02/17/national-strawberry-day-time-to-recognize-ufifas-breeding-program/)\n"
            "- [USDA-ARS — ‘Florida Brilliance’ release](https://www.ars.usda.gov/research/publications/publication/?seqNo115=366363)\n"
            "- [USDA-ARS — ‘Medallion’ (Florida127 successor)](https://www.ars.usda.gov/research/publications/publication/?seqNo115=424464)\n"
            "- [The Packer — ‘Florida Brilliance’ a hit](https://www.thepacker.com/markets/shipping/floridas-brilliance-strawberry-variety-hit)\n"
            "- [The Packer — UF standout varieties](https://www.thepacker.com/news/produce-crops/university-florida-research-center-offers-standout-strawberry-varieties)\n"
            "- [FreshPlaza — new ‘Florida Brilliance’ variety](https://www.freshplaza.com/europe/article/9062095/new-florida-brilliance-variety-appealing-to-state-s-strawberry-industry/)\n"
            "- [Florida Strawberry (FFSP) — ‘Florida Brilliance’ profile](https://ffsp.net/varieties/strawberry/florida-brilliance/)\n"
            "- [Produce Business — Florida strawberry report](https://producebusiness.com/florida-strawberry-report-the-varieties-making-waves/)\n"
            "- [Agronometrics — Florida's $300M strawberry industry](https://stories.agronometrics.com/researchers-play-key-role-in-floridas-300-million-strawberry-industry/)")

    with st.expander("🌵 Mexico: Imported Genetics, Consolidating", expanded=True):
        st.markdown(
            "Mexican strawberry growers largely plant **imported California / Florida "
            "genetics**:\n\n"
            "- **Festival** and **Camarosa** — long-standing and still prominent.\n"
            "- **Albion, San Andreas, Sweet Charlie** — UC/other day-neutrals and short-day types.\n"
            "- The main trend is **consolidation to fewer varieties** for more uniform, targeted management.\n"
            "- Not following CA's shift to proprietary cultivars.\n\n"
            "Production is concentrated in **Michoacán, Baja California, Guanajuato and Jalisco**; the "
            "USDA-FAS GAIN Berry Annuals track named varieties and planted area but give no acreage split.\n\n"
            "**Sources**\n"
            "- [USDA-FAS GAIN — Berry Annual, Guadalajara (MX2026-0015)](https://apps.fas.usda.gov/newgainapi/api/Report/DownloadReportByFileName?fileName=Berry+Annual+Voluntary_Guadalajara_Mexico_MX2026-0015.pdf)\n"
            "- [USDA-FAS GAIN — Berry Annual, Guadalajara (MX2025-0005)](https://apps.fas.usda.gov/newgainapi/api/Report/DownloadReportByFileName?fileName=Berry+Annual+Voluntary_Guadalajara_Mexico_MX2025-0005.pdf)")
