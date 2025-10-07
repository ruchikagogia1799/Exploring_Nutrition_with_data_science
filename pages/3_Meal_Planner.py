import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Meal Planner", layout="wide")

# -------------------- Load Data --------------------
DATA_URL = "https://drive.google.com/uc?export=download&id=1SjGNAij9o5q4V_62qfMkcjFegQvj5Ij2"

@st.cache_data
def load_data():
    df = pd.read_csv(DATA_URL)
    # Convert key nutrient columns to numeric
    for c in ["Calories (kcal)", "Protein (g)", "Carbs (g)", "Fat (g)", "Fiber (g)", "Sugar (g)"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

df = load_data()

catalog = load_data()

# normalize column names (lowercase)
catalog.columns = [c.strip().lower() for c in catalog.columns]

# Map columns dynamically
colmap = {
    "food": [c for c in catalog.columns if "food" in c][0],
    "category": [c for c in catalog.columns if "category" in c][0],
    "calories": [c for c in catalog.columns if "calorie" in c][0],
    "protein": [c for c in catalog.columns if "protein" in c][0],
    "carbs": [c for c in catalog.columns if "carb" in c][0],
    "fat": [c for c in catalog.columns if "fat" in c][0],
    "fiber": [c for c in catalog.columns if "fiber" in c][0],
    "sugar": [c for c in catalog.columns if "sugar" in c][0],
}

# -------------------- Sidebar --------------------
st.sidebar.header("⚙️ Preferences")

diet_pref = st.sidebar.radio("🥗 Diet Type", ["Non-Vegetarian", "Vegetarian", "Vegan"], index=0)

# --- Calories: choose BMR or TDEE if available ---
bmr = st.session_state.get("bmr", 1800)
tdee = st.session_state.get("tdee", 2200)

calorie_basis = st.sidebar.radio("⚖️ Calorie Basis", ["BMR", "TDEE"], index=1)
daily_kcal = tdee if calorie_basis == "TDEE" else bmr

st.sidebar.metric("🔥 Daily Calorie Target", f"{int(daily_kcal)} kcal")

# Recommended macros
st.sidebar.markdown("### 🎯 Recommended Intake")
protein_target = int(daily_kcal * 0.25 / 4)
carb_target = int(daily_kcal * 0.50 / 4)
fat_target = int(daily_kcal * 0.25 / 9)
fiber_target = int(14 * daily_kcal / 1000)
sugar_target = int(daily_kcal * 0.10 / 4)

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
        ~filtered_catalog[colmap["category"]].str.contains(pattern, case=False, na=False) &
        ~filtered_catalog[colmap["food"]].str.contains(pattern, case=False, na=False)
    ]

if diet_pref == "Vegan":
    vegan_exclude = ["milk","cheese","butter","yogurt","cream","egg"]
    pattern_vegan = "|".join(vegan_exclude)
    filtered_catalog = filtered_catalog[
        ~filtered_catalog[colmap["category"]].str.contains(pattern_vegan, case=False, na=False) &
        ~filtered_catalog[colmap["food"]].str.contains(pattern_vegan, case=False, na=False)
    ]

# -------------------- Main Page --------------------
st.title("🍽️ Meal Planner")
st.caption("Plan your meals, track macros, and discover healthy swaps.")

colA, colB, colC, colD = st.columns([1.2, 1.2, 1.2, 1])
categories = sorted(filtered_catalog[colmap["category"]].dropna().unique().tolist())

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
    f = f[f[colmap["category"]].isin(set(pick_cats))]
if search:
    f = f[f[colmap["food"]].str.contains(search, case=False, na=False)]

sel = st.selectbox("🍲 Choose an Item", options=f[colmap["food"]] if not f.empty else ["(no items)"], index=0)

if st.button("➕ Add to Plan", use_container_width=True, disabled=(f.empty or sel == "(no items)")):
    row = catalog[catalog[colmap["food"]] == sel].iloc[0].to_dict()
    row_out = {
        "Meal": meal,
        "Food": row[colmap["food"]],
        "Category": row.get(colmap["category"], ""),
        "Grams": grams,
        "Calories": row.get(colmap["calories"], np.nan),
        "Protein": row.get(colmap["protein"], np.nan),
        "Carbs": row.get(colmap["carbs"], np.nan),
        "Fat": row.get(colmap["fat"], np.nan),
        "Fiber": row.get(colmap["fiber"], np.nan),
        "Sugar": row.get(colmap["sugar"], np.nan),
    }
    st.session_state.cart.append(row_out)
    st.success(f"✅ Added: {row_out['Food']} ({grams} g) to {meal}")
    st.rerun()

# -------------------- Current Plan --------------------
if st.session_state.cart:
    st.markdown("## 📋 Current Plan")
    df_plan = pd.DataFrame(st.session_state.cart)

    # scale nutrients
    factor = df_plan["Grams"].astype(float) / 100.0
    for c in ["Calories","Protein","Carbs","Fat","Fiber","Sugar"]:
        df_plan[c] = pd.to_numeric(df_plan[c], errors="coerce") * factor

    st.dataframe(df_plan, use_container_width=True)

    totals = df_plan[["Calories","Protein","Carbs","Fat","Fiber","Sugar"]].sum()

    st.progress(min(totals["Calories"]/daily_kcal, 1.0),
                text=f"🔥 {totals['Calories']:.0f} / {daily_kcal} kcal")

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("💪 Protein (g)", f"{totals['Protein']:.1f}")
    c2.metric("🍞 Carbs (g)", f"{totals['Carbs']:.1f}")
    c3.metric("🥑 Fat (g)", f"{totals['Fat']:.1f}")
    c4.metric("🌾 Fiber (g)", f"{totals['Fiber']:.1f}")
    c5.metric("🍭 Sugar (g)", f"{totals['Sugar']:.1f}")

    # Manage entries
    st.markdown("### 🛠️ Manage Entries")
    names = [f"{r['Meal']}: {r['Food']} ({r['Grams']} g)" for r in st.session_state.cart]
    sel_idx = st.selectbox("Select Item", options=list(range(len(names))), format_func=lambda i: names[i])

    colx, coly, colz = st.columns([1,1,1])
    with colx:
        new_g = st.number_input("Update Grams", 10, 1000, value=int(st.session_state.cart[sel_idx]["Grams"]), step=10)
        if st.button("🔄 Update Grams"):
            st.session_state.cart[sel_idx]["Grams"] = new_g
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

        # -------------------- Healthy Swaps --------------------
    st.markdown("## 🥦 Healthy Swaps")

    swaps_found = False

    for i, chosen in df_plan.iterrows():
        chosen_food = chosen["Food"]
        chosen_kcal = chosen.get("Calories", 0)
        chosen_protein = chosen.get("Protein", 0)

        better = filtered_catalog[
    (filtered_catalog[colmap["calories"]] <= chosen_kcal) &
    (filtered_catalog[colmap["protein"]] >= chosen_protein)
].sort_values(colmap["calories"]).head(3)


        if not better.empty:
            swaps_found = True
            st.markdown(f"**💡 Alternatives to {chosen_food} ({chosen_kcal:.0f} kcal):**")
            st.dataframe(
                better[[colmap["food"], colmap["category"], colmap["calories"], 
                        colmap["protein"], colmap["fiber"], colmap["sugar"], colmap["fat"]]]
                .rename(columns={
                    colmap["food"]: "Food",
                    colmap["category"]: "Category",
                    colmap["calories"]: "Calories",
                    colmap["protein"]: "Protein",
                    colmap["fiber"]: "Fiber",
                    colmap["sugar"]: "Sugar",
                    colmap["fat"]: "Fat",
                }),
                use_container_width=True
            )

    if not swaps_found:
        st.info("✅ All your chosen foods are already healthy choices!")

