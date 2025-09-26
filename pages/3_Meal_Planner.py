# pages/3_Meal_Tracker.py — 🍽️ Build-your-own meal plan & track calories
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

# ---------- Config ----------
DATA_CSV = Path("./Final.csv")
st.set_page_config(page_title="🍽️ Meal Tracker", layout="wide")

# ---------- Table helper ----------
def show_table(df: pd.DataFrame):
    d = df.reset_index(drop=True).copy()
    d.index = np.arange(1, len(d) + 1)
    d.index.name = "#"
    d = d.rename(columns={c: c.capitalize() for c in d.columns})  # capitalize headers
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

# ---------- Load & prepare ----------
@st.cache_data
def load_catalog(p: Path) -> pd.DataFrame:
    df = pd.read_csv(p).rename(columns={
        "Food_Item": "food","Category": "category","Calories (kcal)": "calories_kcal",
        "Protein (g)": "protein_g","Carbohydrates (g)": "carbs_g",
        "Fats (g)": "fat_g","Fibre (g)": "fiber_g","Sugars (g)": "sugar_g","Sugars": "sugar_g",
    })
    for c in ["calories_kcal","protein_g","carbs_g","fat_g","fiber_g","sugar_g"]:
        df[c] = pd.to_numeric(df.get(c), errors="coerce")

    df = clean_fiber_outliers(df)
    df = clean_protein_outliers(df)
    df = clean_other_macros(df)

    df = (df.sort_values(["food","protein_g"], ascending=[True, False])
            .drop_duplicates(subset=["food"], keep="first"))

    df["protein_per_100kcal"] = df["protein_g"] / (df["calories_kcal"].replace(0, np.nan)/100.0)
    df["protein_per_100kcal"] = df["protein_per_100kcal"].replace([np.inf,-np.inf], np.nan).fillna(0)

    return df.reset_index(drop=True)

try:
    catalog = load_catalog(DATA_CSV)
except Exception as e:
    st.error(f"❌ Failed to load {DATA_CSV.name}: {e}")
    st.stop()

# ---------- Session cart ----------
if "cart" not in st.session_state:
    st.session_state.cart = []

# ---------- Sidebar ----------
with st.sidebar:
    st.header("🎯 Daily Goal")
    daily_kcal = st.number_input("Daily Calorie Target (kcal)", 800, 5000, 1500, step=50)
    default_serving = st.number_input("Default Serving Size (g)", 50, 300, 200, step=10)
    st.markdown("---")
    if st.button("🧹 Clear My Plan"):
        st.session_state.cart = []
        st.success("✨ Cleared current plan.")
        st.rerun()

st.title("🍽️ Meal Tracker — Choose Your Foods & Track Totals")
st.caption("➕ Add items below. We’ll total calories/macros and show progress vs your daily target.")

# ---------- Add items UI ----------
categories = sorted(catalog["category"].dropna().unique().tolist())
colA, colB, colC, colD = st.columns([1.2, 1.2, 1.2, 1])

with colA:
    pick_cats = st.multiselect("📂 Filter by Category", categories)
with colB:
    search = st.text_input("🔍 Search Food")
with colC:
    meal = st.selectbox("🍴 Assign to Meal", ["Breakfast", "Lunch", "Dinner", "Snack"])
with colD:
    grams = st.number_input("⚖️ Grams", 10, 1000, default_serving, step=10)

f = catalog.copy()
if pick_cats:
    f = f[f["category"].isin(set(pick_cats))]
if search:
    f = f[f["food"].str.contains(search, case=False, na=False)]

sel = st.selectbox("🍲 Choose an Item to Add", options=f["food"] if not f.empty else ["(no items)"], index=0)

if st.button("➕ Add to Plan", use_container_width=True, disabled=(f.empty or sel == "(no items)")):
    row = catalog[catalog["food"] == sel].iloc[0].to_dict()
    row_out = {
        "Meal": meal, "food": row["food"], "category": row.get("category", ""), "grams": grams,
        "calories_kcal": row.get("calories_kcal", np.nan), "protein_g": row.get("protein_g", np.nan),
        "carbs_g": row.get("carbs_g", np.nan), "fat_g": row.get("fat_g", np.nan),
        "fiber_g": row.get("fiber_g", np.nan), "sugar_g": row.get("sugar_g", np.nan),
        "protein_per_100kcal": row.get("protein_per_100kcal", np.nan),
    }
    st.session_state.cart.append(row_out)
    st.success(f"✅ Added: {row_out['food']} ({grams} g) to {meal}")
    st.rerun()

if st.session_state.cart:
    st.markdown("### 📋 Current Plan")
    df_plan = pd.DataFrame(st.session_state.cart)

    factor = df_plan["grams"].astype(float) / 100.0
    cols = ["calories_kcal","protein_g","carbs_g","fat_g","fiber_g","sugar_g"]
    df_scaled = df_plan.copy()
    for c in cols:
        df_scaled[c] = pd.to_numeric(df_scaled[c], errors="coerce") * factor

    show_cols = ["Meal","food","category","grams","calories_kcal","protein_g","carbs_g","fat_g","fiber_g","sugar_g"]
    show_table(df_scaled[show_cols].round(1))

    totals = df_scaled[cols].sum(numeric_only=True)
    kcal_pct = float(np.clip(totals["calories_kcal"] / max(daily_kcal,1), 0, 1))
    st.progress(kcal_pct, text=f"🔥 Calories: {totals['calories_kcal']:.0f} / {daily_kcal} kcal")

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("💪 Protein (g)", f"{totals['protein_g']:.1f}")
    m2.metric("🍞 Carbs (g)",   f"{totals['carbs_g']:.1f}")
    m3.metric("🥑 Fat (g)",     f"{totals['fat_g']:.1f}")
    m4.metric("🌾 Fibre (g)",   f"{totals['fiber_g']:.1f}")
    m5.metric("🍭 Sugar (g)",   f"{totals['sugar_g']:.1f}")

    # Manage items
    st.markdown("#### 🛠️ Manage Items")
    names = [f"{r['Meal']}: {r['food']} ({r['grams']} g)" for r in st.session_state.cart]
    sel_idx = st.selectbox("Select Item", options=list(range(len(names))), format_func=lambda i: names[i])

    colx, coly, colz = st.columns([1,1,1])
    with colx:
        new_g = st.number_input("Update Grams", 10, 1000, value=int(st.session_state.cart[sel_idx]["grams"]), step=10)
        if st.button("🔄 Update Grams"):
            st.session_state.cart[sel_idx]["grams"] = new_g
            st.rerun()
    with coly:
        new_meal = st.selectbox("Move to Meal", ["Breakfast","Lunch","Dinner","Snack"],
                                index=["Breakfast","Lunch","Dinner","Snack"].index(st.session_state.cart[sel_idx]["Meal"]))
        if st.button("📌 Move"):
            st.session_state.cart[sel_idx]["Meal"] = new_meal
            st.rerun()
    with colz:
        if st.button("🗑️ Remove Item", type="secondary"):
            st.session_state.cart.pop(sel_idx)
            st.rerun()
else:
    st.info("ℹ️ Your plan is empty. Use the controls above to add items.")
