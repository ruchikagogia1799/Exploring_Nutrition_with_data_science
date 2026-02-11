import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Meal Planner", layout="wide")

#set_page_config()
#apply_custom_styles()

# -------------------- Load CLEANED USDA CSV (LOCAL) --------------------
DATA_PATH = "data_out/usda_food_clean.csv"

@st.cache_data(show_spinner="Loading USDA dataset…")
def load_data():
    df = pd.read_csv(DATA_PATH)

    # Clean column names (just in case)
    df.columns = [c.strip() for c in df.columns]

    # Ensure Food/Category are strings (avoids .str issues)
    if "Food" in df.columns:
        df["Food"] = df["Food"].astype(str)
    if "Category" in df.columns:
        df["Category"] = df["Category"].astype(str)

    # Convert nutrients to numeric
    for c in ["Calories (kcal)", "Protein (g)", "Carbs (g)", "Fat (g)", "Fiber (g)", "Sugar (g)"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    return df

catalog = load_data()

# -------------------- Safety checks --------------------
required_cols = {"Food", "Category", "Calories (kcal)", "Protein (g)", "Carbs (g)", "Fat (g)", "Fiber (g)", "Sugar (g)"}
missing = [c for c in required_cols if c not in catalog.columns]
if missing:
    st.error(f"Missing required columns in CSV: {missing}\n\nFound columns: {list(catalog.columns)}")
    st.stop()

# -------------------- Sidebar --------------------
st.sidebar.header("⚙️ Preferences")

diet_pref = st.sidebar.radio("🥗 Diet Type", ["Non-Vegetarian", "Vegetarian", "Vegan"], index=0)

# --- Calories: choose BMR or TDEE if available ---
bmr = st.session_state.get("bmr", 1800)
tdee = st.session_state.get("tdee", 2200)

calorie_basis = st.sidebar.radio("⚖️ Calorie Basis", ["BMR", "TDEE"], index=1)
daily_kcal = tdee if calorie_basis == "TDEE" else bmr
st.sidebar.metric("🔥 Daily Calorie Target", f"{int(daily_kcal)} kcal")

# Recommended macros (simple heuristic)
st.sidebar.markdown("### 🎯 Recommended Intake")
protein_target = int(daily_kcal * 0.25 / 4)
carb_target    = int(daily_kcal * 0.50 / 4)
fat_target     = int(daily_kcal * 0.25 / 9)
fiber_target   = int(14 * daily_kcal / 1000)
sugar_target   = int(daily_kcal * 0.10 / 4)

st.sidebar.write(f"💪 Protein: {protein_target} g/day")
st.sidebar.write(f"🍞 Carbs: {carb_target} g/day")
st.sidebar.write(f"🥑 Fat: {fat_target} g/day")
st.sidebar.write(f"🌾 Fiber: {fiber_target} g/day")
st.sidebar.write(f"🍭 Sugar: ≤ {sugar_target} g/day")

if "cart" not in st.session_state:
    st.session_state.cart = []

if st.sidebar.button("🧹 Clear My Plan"):
    st.session_state.cart = []
    st.rerun()

# -------------------- Filter diet type --------------------
filtered_catalog = catalog.copy()

if diet_pref in ["Vegetarian", "Vegan"]:
    nonveg_keywords = [
        "meat","fish","pork","chicken","beef","turkey","lamb","goat",
        "duck","veal","shellfish","crab","lobster","shrimp","oyster",
        "clam","anchovy","tuna","salmon","mackerel","sardine"
    ]
    pattern = "|".join(nonveg_keywords)
    filtered_catalog = filtered_catalog[
        ~filtered_catalog["Category"].str.contains(pattern, case=False, na=False) &
        ~filtered_catalog["Food"].str.contains(pattern, case=False, na=False)
    ]

if diet_pref == "Vegan":
    vegan_exclude = ["milk","cheese","butter","yogurt","cream","egg","whey","casein","honey"]
    pattern_vegan = "|".join(vegan_exclude)
    filtered_catalog = filtered_catalog[
        ~filtered_catalog["Category"].str.contains(pattern_vegan, case=False, na=False) &
        ~filtered_catalog["Food"].str.contains(pattern_vegan, case=False, na=False)
    ]

# -------------------- Main Page --------------------
st.title("🍽️ Meal Planner")
st.caption("Plan your meals, track macros, and discover healthy swaps. (All values per 100 g)")

colA, colB, colC, colD = st.columns([1.2, 1.2, 1.2, 1])

categories = sorted(filtered_catalog["Category"].dropna().unique().tolist())

with colA:
    pick_cats = st.multiselect("📂 Filter by Category", categories)
with colB:
    search = st.text_input("🔍 Search Food")
with colC:
    meal = st.selectbox("🍴 Assign to Meal", ["Breakfast", "Lunch", "Dinner", "Snack"])
with colD:
    grams = st.number_input("⚖️ Grams", 10, 1000, 100, step=10)

f = filtered_catalog.copy()
if pick_cats:
    f = f[f["Category"].isin(set(pick_cats))]
if search:
    f = f[f["Food"].str.contains(search, case=False, na=False)]

if f.empty:
    st.warning("No foods match your filters/search. Try removing filters or changing the search term.")
    sel = "(no items)"
else:
    sel = st.selectbox("🍲 Choose an Item", options=f["Food"].tolist(), index=0)

if st.button("➕ Add to Plan", width="stretch", disabled=(f.empty or sel == "(no items)")):
    row = f[f["Food"] == sel].iloc[0]

    row_out = {
        "Meal": meal,
        "Food": row["Food"],
        "Category": row["Category"],
        "Grams": grams,

        # Store PER 100g values; scale later
        "Calories_per100g": row["Calories (kcal)"],
        "Protein_per100g": row["Protein (g)"],
        "Carbs_per100g": row["Carbs (g)"],
        "Fat_per100g": row["Fat (g)"],
        "Fiber_per100g": row["Fiber (g)"],
        "Sugar_per100g": row["Sugar (g)"],
    }

    st.session_state.cart.append(row_out)
    st.success(f"✅ Added: {row_out['Food']} ({grams} g) to {meal}")
    st.rerun()

# -------------------- Current Plan --------------------
if st.session_state.cart:
    st.markdown("## 📋 Current Plan")
    df_plan = pd.DataFrame(st.session_state.cart)

    factor = df_plan["Grams"].astype(float) / 100.0

    # Scaled columns
    df_plan["Calories"] = pd.to_numeric(df_plan["Calories_per100g"], errors="coerce") * factor
    df_plan["Protein"]  = pd.to_numeric(df_plan["Protein_per100g"], errors="coerce") * factor
    df_plan["Carbs"]    = pd.to_numeric(df_plan["Carbs_per100g"], errors="coerce") * factor
    df_plan["Fat"]      = pd.to_numeric(df_plan["Fat_per100g"], errors="coerce") * factor
    df_plan["Fiber"]    = pd.to_numeric(df_plan["Fiber_per100g"], errors="coerce") * factor
    df_plan["Sugar"]    = pd.to_numeric(df_plan["Sugar_per100g"], errors="coerce") * factor

    show_cols = ["Meal", "Food", "Category", "Grams", "Calories", "Protein", "Carbs", "Fat", "Fiber", "Sugar"]
    st.dataframe(df_plan[show_cols], width="stretch")

    totals = df_plan[["Calories", "Protein", "Carbs", "Fat", "Fiber", "Sugar"]].sum(numeric_only=True)

    st.progress(
        min(float(totals["Calories"]) / float(daily_kcal), 1.0),
        text=f"🔥 {totals['Calories']:.0f} / {daily_kcal} kcal",
    )

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("💪 Protein (g)", f"{totals['Protein']:.1f}")
    c2.metric("🍞 Carbs (g)", f"{totals['Carbs']:.1f}")
    c3.metric("🥑 Fat (g)", f"{totals['Fat']:.1f}")
    c4.metric("🌾 Fiber (g)", f"{totals['Fiber']:.1f}")
    c5.metric("🍭 Sugar (g)", f"{totals['Sugar']:.1f}")

    # -------------------- Manage entries --------------------
    st.markdown("### 🛠️ Manage Entries")
    names = [f"{r['Meal']}: {r['Food']} ({r['Grams']} g)" for r in st.session_state.cart]
    sel_idx = st.selectbox("Select Item", options=list(range(len(names))), format_func=lambda i: names[i])

    colx, coly, colz = st.columns([1, 1, 1])

    with colx:
        new_g = st.number_input("Update Grams", 10, 1000, value=int(st.session_state.cart[sel_idx]["Grams"]), step=10)
        if st.button("🔄 Update Grams"):
            st.session_state.cart[sel_idx]["Grams"] = new_g
            st.rerun()

    with coly:
        new_meal = st.selectbox(
            "Move to Meal",
            ["Breakfast", "Lunch", "Dinner", "Snack"],
            index=["Breakfast", "Lunch", "Dinner", "Snack"].index(st.session_state.cart[sel_idx]["Meal"]),
        )
        if st.button("📌 Move"):
            st.session_state.cart[sel_idx]["Meal"] = new_meal
            st.rerun()

    with colz:
        if st.button("🗑️ Remove Item", type="secondary"):
            st.session_state.cart.pop(sel_idx)
            st.rerun()

    # -------------------- Healthy Swaps (per 100g basis) --------------------
    st.markdown("## 🥦 Healthy Swaps")
    swaps_found = False

    for _, chosen in df_plan.iterrows():
        chosen_food = chosen["Food"]
        chosen_kcal_100 = chosen.get("Calories_per100g", np.nan)
        chosen_protein_100 = chosen.get("Protein_per100g", np.nan)

        if pd.isna(chosen_kcal_100) or pd.isna(chosen_protein_100):
            continue

        better = filtered_catalog[
            (filtered_catalog["Calories (kcal)"] <= float(chosen_kcal_100)) &
            (filtered_catalog["Protein (g)"] >= float(chosen_protein_100)) &
            (filtered_catalog["Food"] != chosen_food)
        ].sort_values("Calories (kcal)", ascending=True).head(3)

        if not better.empty:
            swaps_found = True
            st.markdown(f"**💡 Alternatives to {chosen_food} (per 100 g):**")
            st.dataframe(
                better[["Food", "Category", "Calories (kcal)", "Protein (g)", "Fiber (g)", "Sugar (g)", "Fat (g)"]],
                width="stretch"
            )

    if not swaps_found:
        st.info("✅ No better swaps found based on your criteria (lower calories + higher/equal protein per 100g).")

else:
    st.info("Add foods to your plan to see totals and healthy swaps.")
