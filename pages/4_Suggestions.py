# pages/4_Suggestions.py — Healthier swaps & plan feedback
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
ALT_AXIS_KW = dict(labelLimit=10000, labelFontSize=12, titleFontSize=12,
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

# ---------- Config ----------
DATA_CSV = Path("./Final.csv")
st.set_page_config(page_title="Suggestions", layout="wide")

# ---------- Table helper ----------
def show_table(df: pd.DataFrame):
    d = df.reset_index(drop=True).copy()
    d.index = np.arange(1, len(d) + 1)
    d.index.name = "#"
    d = d.rename(columns={c: c.capitalize() for c in d.columns})  # capitalize headers
    st.dataframe(d, use_container_width=True)

# ---------- Load ----------
@st.cache_data
def load_catalog(p: Path) -> pd.DataFrame:
    df = pd.read_csv(p).rename(columns={
        "Food_Item": "food",
        "Category": "category",
        "Calories (kcal)": "calories_kcal",
        "Protein (g)": "protein_g",
        "Carbohydrates (g)": "carbs_g",
        "Fats (g)": "fat_g",
        "Fibre (g)": "fiber_g",
        "Sugars (g)": "sugar_g",
        "Sugars": "sugar_g",
    })

    for c in ["calories_kcal","protein_g","carbs_g","fat_g","fiber_g","sugar_g"]:
        df[c] = pd.to_numeric(df.get(c), errors="coerce")

    df = (
        df.sort_values(["food","protein_g"], ascending=[True, False])
          .drop_duplicates(subset=["food"], keep="first")
    )

    if "sugar_g" not in df.columns or df["sugar_g"].isna().all():
        if "carbs_g" in df.columns:
            carbs = pd.to_numeric(df["carbs_g"], errors="coerce")
            if "fiber_g" in df.columns:
                fiber = pd.to_numeric(df["fiber_g"], errors="coerce")
                df["sugar_g"] = (carbs - fiber).clip(lower=0)
            else:
                df["sugar_g"] = (0.5 * carbs).clip(lower=0)
        else:
            df["sugar_g"] = 0.0

    df["protein_per_100kcal"] = df["protein_g"] / (df["calories_kcal"].replace(0, np.nan) / 100.0)
    df["protein_per_100kcal"] = df["protein_per_100kcal"].replace([np.inf, -np.inf], np.nan).fillna(0)

    for c in ["food","category"]:
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip()

    return df.reset_index(drop=True)

try:
    catalog_raw = load_catalog(DATA_CSV)
except Exception as e:
    st.error(f"❌ Failed to load {DATA_CSV.name}: {e}")
    st.stop()

st.title("💡 Suggestions — Make Your Plan Healthier")

# ---------- Read plan ----------
cart = st.session_state.get("cart", [])
if not cart:
    st.warning("No items found in your plan. Go to **Meal Planner** and add foods first.")
    st.stop()

plan = pd.DataFrame(cart)

# Scale current plan
factor = plan["grams"].astype(float) / 100.0
for c in ["calories_kcal","protein_g","carbs_g","fat_g","fiber_g","sugar_g"]:
    plan[c] = pd.to_numeric(plan[c], errors="coerce")
scaled = plan.copy()
for c in ["calories_kcal","protein_g","carbs_g","fat_g","fiber_g","sugar_g"]:
    scaled[c] = scaled[c] * factor

# ---------- Plan health summary ----------
st.subheader("Plan Health Summary")
totals = scaled[["calories_kcal","protein_g","carbs_g","fat_g","fiber_g","sugar_g"]].sum(numeric_only=True).round(1)

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Protein density (g/100 kcal)", f"{(totals['protein_g'] / max(totals['calories_kcal']/100,1)):.2f}")
c2.metric("Fibre (g)", f"{totals['fiber_g']:.1f}")
c3.metric("Sugar (g)", f"{totals['sugar_g']:.1f}")
c4.metric("Fat (g)", f"{totals['fat_g']:.1f}")
c5.metric("Calories (kcal)", f"{totals['calories_kcal']:.0f}")

remarks = []
if totals["fiber_g"] < 25: remarks.append("Low fibre (<25 g/day).")
if totals["sugar_g"] > 50: remarks.append("High sugar (>50 g/day).")
if totals["fat_g"] > 80: remarks.append("High fat (>80 g/day).")
if (totals["protein_g"] / max(totals["calories_kcal"]/100,1)) < 8:
    remarks.append("Low protein density (<8 g per 100 kcal).")

if remarks:
    st.error(" • ".join(remarks))
else:
    st.success("Looks balanced overall. You can still improve a few items below.")

st.markdown("---")

# ---------- Suggestion engine ----------
st.subheader("Item-by-Item Healthier Swaps")

EXCLUDE_TERMS = [
    "yeast","baker","nutritional yeast","powder","extract","essence","seasoning","spice","masala",
    "premix","mix","bouillon","stock cube","color","flavour","raw dough","baking","icing",
]
EXCLUDE_CATEGORIES = {
    "Spices & Condiments","Spices","Herbs & Spices","Supplements","Baby Food","Ingredients","Additives",
}
MIN_KCAL_100G = 30
MAX_KCAL_100G = 700

def is_real_food(df: pd.DataFrame) -> pd.Series:
    name = df["food"].astype(str).str.lower()
    cat  = df["category"].astype(str).str.strip()
    bad_term = name.str.contains("|".join(EXCLUDE_TERMS), na=False)
    bad_cat  = cat.isin(EXCLUDE_CATEGORIES)
    kcal_ok  = df["calories_kcal"].between(MIN_KCAL_100G, MAX_KCAL_100G)
    return (~bad_term) & (~bad_cat) & kcal_ok

catalog = catalog_raw.copy()
catalog = catalog[is_real_food(catalog)].reset_index(drop=True)

def suggestion_score(sel_row, cand):
    return (
        1.5 * (cand["protein_per_100kcal"] - sel_row["protein_per_100kcal"]) +
        0.8 * (cand["fiber_g"] - sel_row["fiber_g"]) +
        0.6 * (sel_row["sugar_g"] - cand["sugar_g"]) +
        0.4 * (sel_row["fat_g"] - cand["fat_g"]) +
        0.02 * (sel_row["calories_kcal"] - cand["calories_kcal"])
    )

force_same_cat = st.toggle("Keep swaps in the same category", value=True)

all_suggestions = []
for _, r in plan.iterrows():
    if force_same_cat:
        pool = catalog[catalog["category"] == r["category"]].copy()
        if len(pool) < 5:
            pool = catalog.copy()
    else:
        pool = catalog.copy()

    pool = pool[pool["food"] != r["food"]].copy()
    if pool.empty:
        continue

    pool["__score"] = pool.apply(lambda c: suggestion_score(r, c), axis=1)
    top_cand = pool.sort_values("__score", ascending=False).head(3)

    for _, c in top_cand.iterrows():
        all_suggestions.append({
            "Meal": r.get("Meal", ""),
            "Chosen Food": r["food"],
            "Category": r["category"],
            "Suggested Swap": c["food"],
            "Δ Protein/100kcal": round(c["protein_per_100kcal"] - r["protein_per_100kcal"], 2),
            "Δ Fibre (g/100g)": round(c["fiber_g"] - r["fiber_g"], 1),
            "Δ Sugar (g/100g)": round(c["sugar_g"] - r["sugar_g"], 1),
            "Δ Fat (g/100g)": round(c["fat_g"] - r["fat_g"], 1),
            "Δ Kcal (per 100g)": round(c["calories_kcal"] - r["calories_kcal"], 0),
            "Score": round(c["__score"], 3),
        })

if not all_suggestions:
    st.info("No suggestions found. Try adding more items or relaxing the filters.")
    st.stop()

sug_df = pd.DataFrame(all_suggestions).sort_values(["Meal","Chosen Food","Score"], ascending=[True,True,False])
show_table(sug_df)

st.caption("— Higher **Score** means a generally healthier swap (↑ protein & fibre, ↓ sugar/fat/kcal).")

st.markdown("---")

# ---------- Apply a swap ----------
st.subheader("Apply a Swap")
if st.session_state.get("cart"):
    items = [f"{i+1}. {r['Meal']} — {r['food']}" for i, r in enumerate(st.session_state["cart"])]
    idx_to_replace = st.selectbox("Item to replace", options=list(range(len(items))), format_func=lambda i: items[i])

    target_row = st.session_state["cart"][idx_to_replace]
    target_name, target_cat = target_row["food"], target_row["category"]

    if force_same_cat:
        sug_for_item = sug_df[(sug_df["Chosen Food"] == target_name) & (sug_df["Category"] == target_cat)]
    else:
        sug_for_item = sug_df[sug_df["Chosen Food"] == target_name]

    choices = sug_for_item["Suggested Swap"].unique().tolist()
    if not choices:
        st.info("No swap candidates for this item. Pick another item above.")
    else:
        pick_swap = st.selectbox("Suggested replacement", options=choices)
        new_grams = st.number_input("Grams (keep same or change)", 10, 1000, value=int(target_row.get("grams", 100)), step=10)

        if st.button("Swap it"):
            cand = catalog_raw[catalog_raw["food"] == pick_swap].iloc[0].to_dict()
            st.session_state["cart"][idx_to_replace].update({
                "food": cand["food"], "category": cand.get("category",""),
                "calories_kcal": cand.get("calories_kcal", np.nan),
                "protein_g": cand.get("protein_g", np.nan),
                "carbs_g": cand.get("carbs_g", np.nan),
                "fat_g": cand.get("fat_g", np.nan),
                "fiber_g": cand.get("fiber_g", np.nan),
                "sugar_g": cand.get("sugar_g", np.nan),
                "protein_per_100kcal": cand.get("protein_per_100kcal", np.nan),
                "grams": new_grams,
            })
            st.success(f"✅ Swapped to: {pick_swap}")
            st.rerun()
