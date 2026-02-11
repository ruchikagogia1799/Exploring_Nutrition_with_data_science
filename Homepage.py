# Homepage.py — USDA Food Dashboard (fixed bars = no aggregation)

import streamlit as st
import pandas as pd
import altair as alt
#from common import set_page_config, apply_custom_styles

# --- Page Config ---
# IMPORTANT: st.set_page_config must be called exactly once and before any other Streamlit command.
# If your common.set_page_config() already calls st.set_page_config(), remove the line below and keep only set_page_config().
st.set_page_config(page_title="🍽️ USDA Food Dashboard", layout="wide")

# If common.set_page_config() does NOT call st.set_page_config(), you can keep this.
# Otherwise, delete this call to avoid calling set_page_config twice.
#set_page_config()
#apply_custom_styles()

# ----------------- Load CLEANED USDA dataset -----------------
DATA_PATH = "data_out/usda_food_clean.csv"

@st.cache_data(show_spinner="Loading USDA dataset…")
def load_data():
    df = pd.read_csv(DATA_PATH)

    # Clean column names (just in case)
    df.columns = [c.strip() for c in df.columns]

    # Ensure Food is a string (avoids rare contains issues)
    if "Food" in df.columns:
        df["Food"] = df["Food"].astype(str)

    # Convert key nutrient columns to numeric
    for c in ["Calories (kcal)", "Protein (g)", "Carbs (g)", "Fat (g)", "Fiber (g)", "Sugar (g)"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    return df

df = load_data()

# ----------------- Sidebar Filters -----------------
st.sidebar.header("🔍 Filters")

# Safety checks (helps if file path wrong or columns missing)
required_cols = {"Food", "Category"}
missing = [c for c in required_cols if c not in df.columns]
if missing:
    st.error(f"Missing required columns in CSV: {missing}\n\nFound columns: {list(df.columns)}")
    st.stop()

categories = sorted(df["Category"].dropna().unique())
selected_category = st.sidebar.selectbox("Select Category", ["All"] + categories)
search_term = st.sidebar.text_input("Search Food by Name")
top_n = st.sidebar.slider("Show Top N", 5, 30, 10)

# Filter dataframe
filtered = df.copy()
if selected_category != "All":
    filtered = filtered[filtered["Category"] == selected_category]
if search_term:
    filtered = filtered[filtered["Food"].str.contains(search_term, case=False, na=False)]

# Stop early if no results after filtering (better UX)
if filtered.empty:
    st.title("🍽️ USDA Food Nutrient Dashboard")
    st.caption("📌 All nutrient values are expressed per 100 g of food.")
    st.warning("No foods match your filters. Try another category or search term.")
    st.stop()

# ----------------- Helpers -----------------
palette = alt.Scale(scheme="category20")

def prep_top(data: pd.DataFrame, nutrient: str, k: int) -> pd.DataFrame:
    """Make sure we have exactly one row per food for the chart."""
    d = data.copy()
    if nutrient not in d.columns:
        return d.head(0)

    d = d.dropna(subset=[nutrient])

    # If a food appears multiple times, keep the row with the highest nutrient value
    d = (
        d.sort_values(["Food", nutrient], ascending=[True, False])
         .drop_duplicates(subset="Food", keep="first")
         .sort_values(nutrient, ascending=False)
         .head(k)
    )
    return d

def make_chart(data: pd.DataFrame, nutrient: str, title: str):
    """Safe chart builder that won't break if max is NaN."""
    if data.empty or nutrient not in data.columns:
        empty_df = pd.DataFrame({"Food": [], nutrient: [], "Category": []})
        return alt.Chart(empty_df).mark_bar().encode(
            x=alt.X(f"{nutrient}:Q", title=f"{nutrient} (per 100 g)"),
            y=alt.Y("Food:N", title=None),
        ).properties(title=title, width=700, height=360)

    xmax = data[nutrient].max()
    xmax = 0 if pd.isna(xmax) else float(xmax)
    xmax_for_domain = xmax * 1.05 if xmax > 0 else 1

    chart = (
        alt.Chart(data)
        .mark_bar()
        .encode(
            x=alt.X(
                f"{nutrient}:Q",
                title=f"{nutrient} (per 100 g)",
                scale=alt.Scale(domain=[0, xmax_for_domain]),
                axis=alt.Axis(labelAngle=0),
            ),
            y=alt.Y("Food:N", sort="-x", axis=alt.Axis(labelLimit=650, title=None)),
            color=alt.Color(
                "Category:N",
                scale=palette,
                legend=alt.Legend(title="Category", orient="right"),
            ),
            tooltip=[
                alt.Tooltip("Food:N", title="Food"),
                alt.Tooltip(f"{nutrient}:Q", title=nutrient, format=".2f"),
                alt.Tooltip("Calories (kcal):Q", title="Calories (kcal)", format=".0f"),
                alt.Tooltip("Category:N", title="Category"),
            ],
        )
        .properties(title=title, width=700, height=360)
    )
    return chart

# ----------------- Main Dashboard -----------------
st.title("🍽️ USDA Food Nutrient Dashboard")
st.caption("📌 All nutrient values are expressed per 100 g of food.")

# Top Protein
top_protein = prep_top(filtered, "Protein (g)", top_n)
st.subheader("🥩 Top Protein Foods (per 100 g)")
st.altair_chart(make_chart(top_protein, "Protein (g)", "Top Protein Foods"), width="stretch")
st.dataframe(top_protein, width="stretch")

# Top Fiber
top_fiber = prep_top(filtered, "Fiber (g)", top_n)
st.subheader("🌾 Top Fiber Foods (per 100 g)")
st.altair_chart(make_chart(top_fiber, "Fiber (g)", "Top Fiber Foods"), width="stretch")
st.dataframe(top_fiber, width="stretch")

# Top Sugar & Fat (tabs)
tab1, tab2 = st.tabs(["🍭 Top Sugary Foods", "🍟 Top Fatty Foods"])

with tab1:
    top_sugar = prep_top(filtered, "Sugar (g)", top_n)
    st.subheader("🍭 Top Sugary Foods (per 100 g)")
    st.altair_chart(make_chart(top_sugar, "Sugar (g)", "Top Sugary Foods"), width="stretch")
    st.dataframe(top_sugar, width="stretch")

with tab2:
    top_fat = prep_top(filtered, "Fat (g)", top_n)
    st.subheader("🍟 Top Fatty Foods (per 100 g)")
    st.altair_chart(make_chart(top_fat, "Fat (g)", "Top Fatty Foods"), width="stretch")
    st.dataframe(top_fat, width="stretch")

# Optional: quick sanity note if anything looks impossible
if "Protein (g)" in df.columns and (df["Protein (g)"] > 120).any():
    st.info(
        "ℹ️ Charts de-duplicate by food name to prevent sums; "
        "if you still see extreme values, they come from the source CSV."
    )
