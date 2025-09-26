# app.py — Diet: Top Protein + Top Fibre + centered Top Sugar/Top Fatty
from pathlib import Path
import numpy as np
import pandas as pd
import altair as alt
import streamlit as st

# ---------- Page config ----------
st.set_page_config(page_title="🥗 Diet & Nutrition Dashboard", layout="wide")
alt.data_transformers.disable_max_rows()

# ---------- Global CSS ----------
page_style = """
<style>
/* Main app background + text */
[data-testid="stAppViewContainer"] {
    background-image: url("https://img.freepik.com/premium-photo/chicken-breast-with-fresh-vegetables-spices-cooking_266870-353.jpg?semt=ais_hybrid&w=740&q=80");
    background-size: cover;
    color: black !important;
}

/* Sidebar background + text */
[data-testid="stSidebar"] {
    background-color: rgba(255, 255, 255, 0.9);
    color: black !important;
}
[data-testid="stSidebar"] * {
    color: black !important;
}

/* Header */
[data-testid="stHeader"] {
    background: rgba(0,0,0,0);
    color: black !important;
}

/* Metric cards */
div[data-testid="stMetricValue"], div[data-testid="stMetricLabel"] {
    color: black !important;
}

/* Dataframe headers + body */
thead tr th {
    color: black !important;
    text-transform: capitalize !important;
}
tbody tr td {
    color: black !important;
}

/* Captions → force black */
div[data-testid="stCaptionContainer"], .stCaption, div.stMarkdown p small, p[data-testid="stCaption"] {
    color: black !important;
    opacity: 1 !important;
}

/* Center align main headings (title + subheader) */
h1, h2, h3 {
    text-align: center !important;
    color: black !important;
}
</style>
"""
st.markdown(page_style, unsafe_allow_html=True)


# ---------- Altair theme ----------
ALT_AXIS_KW = dict(labelLimit=5000, labelFontSize=12, titleFontSize=12,
                   labelColor="black", titleColor="black")
ALT_LEGEND_KW = dict(labelFontSize=12, titleFontSize=12,
                     labelColor="black", titleColor="black")

def apply_theme(c: alt.Chart) -> alt.Chart:
    return (
        c.configure_axis(**ALT_AXIS_KW)
         .configure_legend(**ALT_LEGEND_KW)
         .configure_title(color="black")
         .configure_view(strokeOpacity=0)
    )

DATA_CSV = Path("./Final.csv")

# ---------- Nutrient cleaning ----------
def clean_fiber_outliers(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d["fiber_g"] = pd.to_numeric(d.get("fiber_g"), errors="coerce").fillna(0).clip(lower=0)
    cat = d["category"].astype(str).str.lower()

    is_animal = cat.str.contains(r"(meat|poultry|seafood|fish|egg|dairy|cheese|milk|yogurt|paneer|butter)", na=False)
    d.loc[is_animal, "fiber_g"] = 0.0

    is_bev = cat.str.contains(r"(beverage|drink|tea|coffee|juice|latte|smoothie)", na=False)
    d.loc[is_bev, "fiber_g"] = d.loc[is_bev, "fiber_g"].clip(upper=1.0)

    is_spice = cat.str.contains(r"(spice|condiment|herb|seasoning)", na=False)
    d.loc[is_spice, "fiber_g"] = d.loc[is_spice, "fiber_g"].clip(upper=40.0)

    other = ~(is_animal | is_bev | is_spice)
    d.loc[other, "fiber_g"] = d.loc[other, "fiber_g"].clip(upper=30.0)

    if "carbs_g" in d.columns:
        d["carbs_g"] = pd.to_numeric(d["carbs_g"], errors="coerce").fillna(0).clip(lower=0)
        d.loc[d["fiber_g"] > d["carbs_g"], "fiber_g"] = (d["carbs_g"] * 0.9)

    if "food" in d.columns:
        food_lower = d["food"].astype(str).str.lower()
        d.loc[food_lower.str.contains("oyster", na=False), "fiber_g"] = 0.0
    return d

def clean_protein_outliers(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d["protein_g"] = pd.to_numeric(d.get("protein_g"), errors="coerce").fillna(0).clip(lower=0)

    food = d.get("food", pd.Series("", index=d.index)).astype(str).str.lower()
    cat  = d.get("category", pd.Series("", index=d.index)).astype(str).str.lower()

    is_powder = food.str.contains(r"(protein powder|whey|isolate|casein|soy protein|pea protein|powder)", na=False)
    is_jerky  = food.str.contains(r"(jerky|dried)", na=False)
    is_sweet  = cat.str.contains(r"(sweet|dessert|snack|cookie|baked|confection|candy|chocolate)", na=False)
    is_bev    = cat.str.contains(r"(beverage|drink)", na=False) & ~food.str.contains(r"shake|protein", na=False)
    is_meal   = cat.str.contains(r"(prepared|meal|soup|entree)", na=False)

    d.loc[is_powder, "protein_g"] = d.loc[is_powder, "protein_g"].clip(upper=95)
    d.loc[is_jerky,  "protein_g"] = d.loc[is_jerky,  "protein_g"].clip(upper=55)
    d.loc[is_sweet,  "protein_g"] = d.loc[is_sweet,  "protein_g"].clip(upper=15)
    d.loc[is_bev,    "protein_g"] = d.loc[is_bev,    "protein_g"].clip(upper=12)
    d.loc[is_meal,   "protein_g"] = d.loc[is_meal,   "protein_g"].clip(upper=25)
    other = ~(is_powder | is_jerky | is_sweet | is_bev | is_meal)
    d.loc[other,     "protein_g"] = d.loc[other,     "protein_g"].clip(upper=60)

    if {"carbs_g", "fat_g"}.issubset(d.columns):
        carbs = pd.to_numeric(d["carbs_g"], errors="coerce").fillna(0).clip(lower=0)
        fat   = pd.to_numeric(d["fat_g"],   errors="coerce").fillna(0).clip(lower=0)
        max_p = (100 - (carbs + fat)).clip(lower=0)
        d["protein_g"] = np.minimum(d["protein_g"], max_p)
    return d

def clean_other_macros(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    for c in ["calories_kcal","carbs_g","fat_g","sugar_g"]:
        d[c] = pd.to_numeric(d.get(c), errors="coerce").fillna(0).clip(lower=0)
    cat = d["category"].astype(str).str.lower()

    is_oil   = cat.str.contains(r"(oil|shortening|ghee|butter|lard|fat)", na=False)
    is_meat  = cat.str.contains(r"(meat|poultry|seafood|fish)", na=False)
    is_bev   = cat.str.contains(r"(beverage|drink|tea|coffee|juice|latte|smoothie|beer|wine)", na=False)
    is_sweet = cat.str.contains(r"(sweet|dessert|snack|cookie|baked|confection|candy|chocolate)", na=False)

    d.loc[is_oil, ["carbs_g","sugar_g","fiber_g"]] = 0
    d.loc[is_meat, ["carbs_g","sugar_g","fiber_g"]] = 0
    d.loc[is_bev, "fat_g"] = d.loc[is_bev, "fat_g"].clip(upper=20)
    d.loc[is_bev, "calories_kcal"] = d.loc[is_bev, "calories_kcal"].clip(upper=120)
    d.loc[is_sweet, "sugar_g"] = d.loc[is_sweet, "sugar_g"].clip(upper=90)
    d.loc[is_sweet, "fat_g"]   = d.loc[is_sweet,   "fat_g"].clip(upper=60)

    d["sugar_g"] = np.minimum(d["sugar_g"], d["carbs_g"])
    p = pd.to_numeric(d.get("protein_g"), errors="coerce").fillna(0)
    c = d["carbs_g"]; f = d["fat_g"]
    total = p + c + f
    too_high = total > 100
    scale = (100 / total.replace(0, np.nan)).where(too_high, 1).fillna(1)
    d["protein_g"] = (p * scale).round(2)
    d["carbs_g"]   = (c * scale).round(2)
    d["fat_g"]     = (f * scale).round(2)
    return d

# ---------- Table helper ----------
def show_table(df: pd.DataFrame):
    d = df.reset_index(drop=True).copy()
    d.index = np.arange(1, len(d) + 1)
    d.index.name = "#"
    # Capitalize headers
    d = d.rename(columns={c: c.capitalize() for c in d.columns})
    st.dataframe(d, use_container_width=True)

# ---------- Tooling for charts ----------
def tooltip_cols(df: pd.DataFrame):
    cols = ["food","category","protein_g","calories_kcal","carbs_g","fat_g","fiber_g","protein_per_100kcal"]
    if "sugar_g" in df.columns: cols.insert(6, "sugar_g")
    return [c for c in cols if c in df.columns]

def bar_color(single_cat: bool):
    return (
        alt.Color("food:N", legend=None, scale=alt.Scale(scheme="category20"))
        if single_cat
        else alt.Color("category:N", title="Category", scale=alt.Scale(scheme="set2"))
    )

def make_top_bar(df, metric_col, x_title, single_cat, tooltips):
    chart = (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X(f"{metric_col}:Q", title=x_title),
            y=alt.Y("food:N", sort="-x", title=""),
            color=bar_color(single_cat),
            tooltip=tooltips,
        )
        .properties(height=max(260, 36*len(df)))
    )
    return apply_theme(chart)

# ---------- Loader ----------
@st.cache_data
def load_catalog(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {path.resolve()}")
    df = pd.read_csv(path)

    df = df.rename(columns={
        "Food_Item":"food","Category":"category","Calories (kcal)":"calories_kcal",
        "Protein (g)":"protein_g","Carbohydrates (g)":"carbs_g",
        "Fats (g)":"fat_g","Fibre (g)":"fiber_g","Sugars (g)":"sugar_g","Sugars":"sugar_g"
    })
    for c in ["food","category"]:
        if c in df.columns: df[c] = df[c].astype(str).str.strip()
    for c in ["calories_kcal","protein_g","carbs_g","fat_g","fiber_g","sugar_g"]:
        df[c] = pd.to_numeric(df.get(c), errors="coerce")

    df = clean_fiber_outliers(df)
    df = clean_protein_outliers(df)
    df = clean_other_macros(df)

    df = (df.sort_values(["food","protein_g"], ascending=[True, False])
            .drop_duplicates(subset=["food"], keep="first"))

    df["protein_per_100kcal"] = df["protein_g"] / (df["calories_kcal"].replace(0, np.nan)/100.0)
    df["protein_per_100kcal"] = df["protein_per_100kcal"].replace([np.inf,-np.inf], np.nan).fillna(0)

    order = df["category"].value_counts().index.tolist()
    df["category"] = pd.Categorical(df["category"], categories=order, ordered=True)

    for c in ["calories_kcal","protein_g","carbs_g","fat_g","fiber_g","sugar_g","protein_per_100kcal"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).clip(lower=0)
    return df.reset_index(drop=True)

# ---------- Load ----------
catalog = load_catalog(DATA_CSV)
tips = tooltip_cols(catalog)

# ---------- Sidebar ----------
with st.sidebar:
    st.header("Filters")
    st.caption(f"File: {DATA_CSV.name}")
    max_kcal = st.slider("Max calories (per 100 g)", 50, 900, 500, step=10)
    min_protein = st.slider("Min protein (g per 100 g)", 0, 80, 5, step=1)
    min_fiber = st.slider("Min fibre (g per 100 g)", 0, 50, 0, step=1)
    categories = sorted(catalog["category"].dropna().unique().tolist())
    picked = st.multiselect("Categories", categories)
    search = st.text_input("Search food name")
    top_n = st.slider("Top N", 5, 30, 10)
    rank_by = st.radio("Rank by", ["Protein per 100 g", "Protein per 100 kcal"], index=0)

# ---------- Filter ----------
base = catalog[
    (catalog["calories_kcal"] <= max_kcal) &
    (catalog["protein_g"] >= min_protein) &
    (catalog["fiber_g"] >= min_fiber)
]
if picked: base = base[base["category"].isin(set(picked))]
if search: base = base[base["food"].str.contains(search, case=False, na=False)]

st.title("🥗 Diet & Nutrition Dashboard")
#st.caption(f"{len(base)} items after filters")
if base.empty:
    st.warning("No items match your filters. Relax them or clear the search box.")
    st.stop()

single_cat = bool(picked) and len(picked) == 1

# ---------- Top Protein ----------
metric_col = "protein_g" if rank_by == "Protein per 100 g" else "protein_per_100kcal"
x_title = "Protein (g per 100 g)" if metric_col == "protein_g" else "Protein per 100 kcal (g)"
top = base.sort_values(metric_col, ascending=False).head(top_n)
st.subheader(f"🍗Top {top_n} by {x_title}")
st.altair_chart(make_top_bar(top, metric_col, x_title, single_cat, tips), use_container_width=True)
show_table(top)

st.markdown("---")

# ---------- Top Fibre ----------
st.subheader("🌾 Top fibre foods (g / 100 g)")
top_fiber = base.sort_values("fiber_g", ascending=False).head(top_n)[
    ["food","category","fiber_g","calories_kcal","carbs_g","fat_g","protein_g"]
]
c_fiber = (
    alt.Chart(top_fiber)
    .mark_bar()
    .encode(
        x=alt.X("fiber_g:Q", title="Fibre (g / 100 g)"),
        y=alt.Y("food:N", sort="-x", title=""),
        color=bar_color(single_cat),
        tooltip=["fiber_g","food","category","calories_kcal","carbs_g","fat_g","protein_g"],
    )
    .properties(height=max(260, 36*len(top_fiber)))
)
st.altair_chart(apply_theme(c_fiber), use_container_width=True)

st.markdown("---")

# ---------- Centered: Top Sugar / Top Fatty ----------
st.subheader("🍭🍯High sugar / high fat foods")
left_spacer, center_col, right_spacer = st.columns([1, 8, 1])

with center_col:
    tabs = st.tabs(["Top Sugary Foods🍫", "Top Fatty Foods🍟"])

    with tabs[0]:
        top_sugar = base.sort_values("sugar_g", ascending=False).head(top_n)[
            ["food","category","sugar_g","calories_kcal","carbs_g","fiber_g","fat_g","protein_g"]
        ]
        c_sugar = (
            alt.Chart(top_sugar)
            .mark_bar()
            .encode(
                x=alt.X("sugar_g:Q", title="Sugar (g / 100 g)"),
                y=alt.Y("food:N", sort="-x", title=""),
                color=bar_color(single_cat),
                tooltip=["sugar_g","food","category","calories_kcal","carbs_g","fiber_g","fat_g","protein_g"],
            )
            .properties(height=max(260, 36*len(top_sugar)))
        )
        st.altair_chart(apply_theme(c_sugar), use_container_width=True)

    with tabs[1]:
        top_fat = base.sort_values("fat_g", ascending=False).head(top_n)[
            ["food","category","fat_g","calories_kcal","carbs_g","fiber_g","protein_g"]
        ]
        c_fat = (
            alt.Chart(top_fat)
            .mark_bar()
            .encode(
                x=alt.X("fat_g:Q", title="Fat (g / 100 g)"),
                y=alt.Y("food:N", sort="-x", title=""),
                color=bar_color(single_cat),
                tooltip=["fat_g","food","category","calories_kcal","carbs_g","fiber_g","protein_g"],
            )
            .properties(height=max(260, 36*len(top_fat)))
        )
        st.altair_chart(apply_theme(c_fat), use_container_width=True)
