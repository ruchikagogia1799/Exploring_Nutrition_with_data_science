# pages/2_Category_Insights.py — 📊 Category Insights & Balance
from pathlib import Path
import numpy as np
import pandas as pd
import altair as alt
import streamlit as st

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
ALT_AXIS_KW = dict(
    labelLimit=10000, labelFontSize=12, titleFontSize=12,
    labelColor="black", titleColor="black"
)
ALT_LEGEND_KW = dict(
    labelFontSize=12, titleFontSize=12,
    labelColor="black", titleColor="black"
)

def apply_theme(c: alt.Chart) -> alt.Chart:
    return (
        c.configure_axis(**ALT_AXIS_KW)
         .configure_legend(**ALT_LEGEND_KW)
         .configure_title(color="black")
         .configure_view(strokeOpacity=0)
    )

DATA_CSV = Path("./diet_corrected.csv")

# ---------- Helpers ----------
def show_table(df: pd.DataFrame):
    d = df.reset_index(drop=True).copy()
    d.index = np.arange(1, len(d) + 1)
    d.index.name = "#"
    # Capitalize headers
    d = d.rename(columns={c: c.capitalize() for c in d.columns})
    st.dataframe(d, use_container_width=True)

# ---------- Cleaning ----------
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
    d.loc[is_sweet, "fat_g"]   = d.loc[is_sweet, "fat_g"].clip(upper=60)

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

# ---------- Loader ----------
@st.cache_data
def load_catalog(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path).rename(columns={
        "Food_Item":"food","Category":"category","Calories (kcal)":"calories_kcal",
        "Protein (g)":"protein_g","Carbohydrates (g)":"carbs_g",
        "Fats (g)":"fat_g","Fibre (g)":"fiber_g","Sugars (g)":"sugar_g","Sugars":"sugar_g"
    })
    for c in ["calories_kcal","protein_g","carbs_g","fat_g","fiber_g","sugar_g"]:
        df[c] = pd.to_numeric(df.get(c), errors="coerce")

    df = clean_fiber_outliers(df)
    df = clean_protein_outliers(df)
    df = clean_other_macros(df)

    df["protein_per_100kcal"] = df["protein_g"] / (df["calories_kcal"].replace(0, np.nan)/100.0)
    df["protein_per_100kcal"] = df["protein_per_100kcal"].replace([np.inf,-np.inf], np.nan).fillna(0)

    order = df["category"].value_counts().index.tolist()
    df["category"] = pd.Categorical(df["category"], categories=order, ordered=True)

    for c in ["calories_kcal","protein_g","carbs_g","fat_g","fiber_g","sugar_g","protein_per_100kcal"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).clip(lower=0)
    return df

# ---------- Load ----------
try:
    catalog = load_catalog(DATA_CSV)
except Exception as e:
    st.error(f"❌ FAILED TO LOAD {DATA_CSV}: {e}")
    st.stop()

st.set_page_config(page_title="🥗 Diet & Nutrition Dashboard", layout="wide")
alt.data_transformers.disable_max_rows()


st.caption("🔎 Explore category-level averages, macro % balance, and healthiest picks.")

# ---------- Average nutrients per category ----------
st.subheader("📦 Average nutrients per category")
avg = (catalog.groupby("category", as_index=False)
       .agg(avg_protein=("protein_g","mean"),
            avg_carbs=("carbs_g","mean"),
            avg_fat=("fat_g","mean"),
            avg_fiber=("fiber_g","mean"),
            avg_sugar=("sugar_g","mean")))
long = avg.melt(id_vars="category", var_name="nutrient", value_name="value")
long["nutrient"] = long["nutrient"].map({
    "avg_protein":"Protein (g)","avg_carbs":"Carbs (g)","avg_fat":"Fat (g)",
    "avg_fiber":"Fibre (g)","avg_sugar":"Sugar (g)"
})

chart = (
    alt.Chart(long)
       .mark_bar()
       .encode(
           x=alt.X("category:N", sort="-y", title="Category"),
           y=alt.Y("value:Q", title="Avg per 100 g"),
           color=alt.Color("nutrient:N", title="Nutrient", scale=alt.Scale(scheme="set2")),
           tooltip=["category","nutrient","value"]
       )
       .properties(height=500, width=900)
)
st.altair_chart(apply_theme(chart), use_container_width=True)

st.markdown("---")

# ---------- Macro distribution (horizontal) ----------
st.subheader("⚖️ Macro nutrient balance by category")
macro = (catalog.groupby("category", as_index=False)
         .agg(protein=("protein_g","mean"), carbs=("carbs_g","mean"), fat=("fat_g","mean")))
macro["total"] = macro[["protein","carbs","fat"]].sum(axis=1).replace(0, np.nan)
for c in ["protein","carbs","fat"]:
    macro[c] = (macro[c] / macro["total"] * 100).fillna(0).round(1)
long_macro = macro.melt(id_vars="category", value_vars=["protein","carbs","fat"], var_name="macro", value_name="pct")

macro_chart = (
    alt.Chart(long_macro)
       .mark_bar()
       .encode(
           y=alt.Y("category:N", sort="-x", title="Category"),
           x=alt.X("pct:Q", title="Macro %"),
           color=alt.Color("macro:N", title="Macro", scale=alt.Scale(scheme="set1")),
           tooltip=["category","macro","pct"]
       )
       .properties(height=600, width=900)
)
st.altair_chart(apply_theme(macro_chart), use_container_width=True)

st.markdown("---")

# ---------- Healthiest & Unhealthiest ----------
st.subheader("📈 Category health score (median)")

cat_med = (catalog.assign(
    health_score = (catalog["protein_g"] + catalog["fiber_g"] 
                    - catalog["sugar_g"] - catalog["fat_g"])
).groupby("category", as_index=False)
 .agg(median_health=("health_score","median"),
      median_protein=("protein_g","median"),
      median_fiber=("fiber_g","median"),
      median_sugar=("sugar_g","median"),
      median_fat=("fat_g","median"),
      count=("food","count"))
 .sort_values("median_health", ascending=False))

st.caption("Medians reduce the influence of extreme items (like pure oils/spices).")
st.dataframe(cat_med, use_container_width=True)

st.subheader("❤️‍🩹 Best picks within each category (health score)")
hide_spices = st.toggle("Hide spices/condiments & pure oils", value=True)

EXCLUDE_CATS = {"Spices", "Spices & Condiments", "Herbs & Spices", "Oils", "Oil"}
EXCLUDE_TERMS = ["yeast","powder","extract","seasoning","masala","essence","bouillon","stock","icing"]
MIN_KCAL, MAX_KCAL = 30, 700

def real_food_mask(df):
    name = df["food"].astype(str).str.lower()
    bad_term = name.str.contains("|".join(EXCLUDE_TERMS), na=False)
    bad_cat  = df["category"].isin(EXCLUDE_CATS)
    kcal_ok  = df["calories_kcal"].between(MIN_KCAL, MAX_KCAL)
    return (~bad_term) & (~bad_cat) & kcal_ok
cat3 = catalog.copy()
if hide_spices:
    cat3 = cat3[real_food_mask(cat3)]

cat3["health_score"] = (cat3["protein_g"] + cat3["fiber_g"] 
                        - cat3["sugar_g"] - cat3["fat_g"]).round(2)
best_in_cat = (cat3.sort_values(["category","health_score"], ascending=[True, False])
                  .groupby("category", as_index=False).head(1))
show_table(best_in_cat[["food","category","protein_g","fiber_g","sugar_g","fat_g","health_score"]].round(2))

