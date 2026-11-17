"""
California Strawberry Variety Dashboard
Explore CA Strawberry Commission acreage-survey variety data by region, season,
and variety. Run locally with:  streamlit run app.py
Data: CA Strawberry Commission acreage surveys (variety x region x year, acres).
"""
from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="CA Strawberry Varieties", page_icon="🍓", layout="wide")
DATA = Path(__file__).parent / "data"

FALL_REGIONS = ["Statewide", "Watsonville/Salinas", "Santa Maria", "Oxnard"]
PALETTE = px.colors.qualitative.Safe + px.colors.qualitative.Vivid + px.colors.qualitative.Bold


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


def variety_group(v: str) -> str:
    """Collapse varieties into ownership groups."""
    if v == "Proprietary":
        return "Proprietary (private)"
    if v in ("Other", "Unreported / Underreported") or v[:3] in ("BG-", "P18", "PS-"):
        return "Other / unreported"
    return "Public (named cultivars)"


df = load_data()

# ----------------------------------------------------------------- sidebar
st.sidebar.title("🍓 Strawberry varieties")
st.sidebar.caption("CA Strawberry Commission acreage surveys")

season = st.sidebar.radio("Planting season", ["Fall", "Summer"], horizontal=True,
                          help="Fall-planted makes the winter/spring/summer crop; summer-planted makes the fall crop. "
                               "Regional detail exists only for fall-planted.")
if season == "Fall":
    region = st.sidebar.selectbox("Region", FALL_REGIONS)
else:
    region = "Statewide"
    st.sidebar.selectbox("Region", ["Statewide"], disabled=True,
                         help="Summer-planted is reported statewide only.")

grouping = st.sidebar.radio("Group varieties by", ["Individual varieties", "Public vs Proprietary"])
view = st.sidebar.radio("View", ["Share (100%)", "Acres", "Share trend lines"])

sub = df[(df.season == season) & (df.region == region)].copy()
yrs = sorted(sub.year.unique())
yr_lo, yr_hi = st.sidebar.select_slider("Year range", options=yrs, value=(yrs[0], yrs[-1]))
sub = sub[(sub.year >= yr_lo) & (sub.year <= yr_hi)]

if grouping == "Public vs Proprietary":
    sub["key"] = sub.variety.map(variety_group)
else:
    sub["key"] = sub.variety
sub = sub.groupby(["year", "key"], as_index=False).acres.sum()

TOP_N = 9 if grouping == "Individual varieties" else 99


def top_keys(frame, n):
    tot = frame.groupby("key").acres.sum().sort_values(ascending=False)
    return list(tot.index[:n])


def collapse_minor(frame, keep):
    f = frame.copy()
    f["key"] = f.key.where(f.key.isin(keep), "Other / minor")
    return f.groupby(["year", "key"], as_index=False).acres.sum()


keep = top_keys(sub, TOP_N)
plot_df = collapse_minor(sub, keep) if grouping == "Individual varieties" else sub.copy()
plot_df["share"] = plot_df.acres / plot_df.groupby("year").acres.transform("sum") * 100

# consistent colors
all_keys = list(dict.fromkeys(plot_df.key))
cmap = {k: PALETTE[i % len(PALETTE)] for i, k in enumerate(sorted(all_keys))}
for special, col in {"Proprietary (private)": "#7a2648", "Public (named cultivars)": "#1d9e75",
                     "Other / unreported": "#b9bec4", "Other / minor": "#b9bec4"}.items():
    if special in cmap:
        cmap[special] = col

# ----------------------------------------------------------------- header + KPIs
st.title("California Strawberry Variety Explorer")
st.caption(f"**{season}-planted** · **{region}** · {yr_lo}–{yr_hi}")

latest = sub[sub.year == yr_hi]
prev = sub[sub.year == (yr_hi - 1)]
tot_now = latest.acres.sum()
tot_prev = prev.acres.sum()
prop_now = sub[(sub.year == yr_hi)].assign(g=lambda d: d.key.map(
    variety_group) if grouping == "Individual varieties" else d.key)
prop_share = (prop_now[prop_now.g == "Proprietary (private)"].acres.sum() / tot_now * 100) if tot_now else 0
top_var = latest.sort_values("acres", ascending=False).key.iloc[0] if len(latest) else "—"
n_var = int((latest.acres > 0).sum())

c1, c2, c3, c4 = st.columns(4)
c1.metric(f"Total acres ({yr_hi})", f"{tot_now:,.0f}",
          f"{(tot_now - tot_prev) / tot_prev * 100:+.1f}% vs {yr_hi-1}" if tot_prev else None)
c2.metric("Varieties reported", n_var)
c3.metric("Proprietary share", f"{prop_share:.0f}%")
c4.metric("Largest variety", top_var)

tab_overview, tab_variety, tab_data = st.tabs(["📊 Overview", "🔎 Variety focus", "🗂 Data"])

# ----------------------------------------------------------------- Overview
with tab_overview:
    order = top_keys(plot_df, 99)
    if view == "Share (100%)":
        fig = px.area(plot_df, x="year", y="share", color="key", color_discrete_map=cmap,
                      category_orders={"key": order}, labels={"share": "Share of acreage (%)", "key": "Variety"})
        fig.update_yaxes(range=[0, 100], ticksuffix="%")
    elif view == "Acres":
        fig = px.area(plot_df, x="year", y="acres", color="key", color_discrete_map=cmap,
                      category_orders={"key": order}, labels={"acres": "Acres", "key": "Variety"})
    else:
        fig = px.line(plot_df, x="year", y="share", color="key", color_discrete_map=cmap,
                      category_orders={"key": order}, markers=True,
                      labels={"share": "Share of acreage (%)", "key": "Variety"})
        fig.update_yaxes(ticksuffix="%")
    fig.update_layout(height=560, hovermode="x unified", legend_title="")
    st.plotly_chart(fig, use_container_width=True)
    if grouping == "Individual varieties":
        st.caption("Top varieties shown individually; the rest are grouped as “Other / minor”. "
                   "Switch to *Public vs Proprietary* in the sidebar for the ownership view.")
    else:
        st.caption("“Proprietary (private)” = undisclosed private varieties (e.g., Driscoll's-type). "
                   "Named cultivars are mostly University of California public releases.")

# ----------------------------------------------------------------- Variety focus
with tab_variety:
    st.subheader("Track a variety across regions")
    pool = df[df.season == season]
    variety_opts = (pool.groupby("variety").acres.sum().sort_values(ascending=False))
    variety_opts = [v for v in variety_opts.index if variety_opts[v] > 0]
    default = [v for v in ["Monterey", "Albion", "Proprietary", "Fronteras", "Eclipse"] if v in variety_opts][:3]
    picks = st.multiselect("Varieties", variety_opts, default=default or variety_opts[:2])

    if picks:
        regions = FALL_REGIONS if season == "Fall" else ["Statewide"]
        vf = df[(df.season == season) & (df.region.isin(regions)) & (df.variety.isin(picks))].copy()
        tot = (df[(df.season == season) & (df.region.isin(regions))]
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

# ----------------------------------------------------------------- Data
with tab_data:
    raw = df[(df.season == season) & (df.region == region) &
             (df.year >= yr_lo) & (df.year <= yr_hi)].copy()
    raw = raw.sort_values(["year", "acres"], ascending=[True, False])
    wide = raw.pivot_table(index="variety", columns="year", values="acres", aggfunc="sum").fillna(0)
    wide = wide.round(0).astype(int)
    wide.columns = [str(c) for c in wide.columns]
    st.dataframe(wide, use_container_width=True)
    st.download_button("⬇ Download current view (CSV)",
                       raw[["season", "region", "year", "variety", "acres"]].to_csv(index=False),
                       file_name=f"strawberry_varieties_{season}_{region.replace('/', '-')}_{yr_lo}-{yr_hi}.csv",
                       mime="text/csv")

st.sidebar.markdown("---")
st.sidebar.caption("Source: California Strawberry Commission acreage surveys. "
                   "Regional detail = fall-planted only.")
