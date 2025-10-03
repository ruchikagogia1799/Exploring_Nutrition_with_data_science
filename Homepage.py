# Homepage.py — USDA Food Dashboard (fixed bars = no aggregation)
import streamlit as st
import pandas as pd
import altair as alt
from common import set_page_config, apply_custom_styles

# --- Config ---
set_page_config()
apply_custom_styles()
st.set_page_config(page_title="🍽️ USDA Food Dashboard", layout="wide")

# ----------------- Load USDA dataset -----------------


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

# ----------------- Sidebar Filters -----------------
st.sidebar.header("🔍 Filters")

categories = sorted(df["Category"].dropna().unique())


#categories = sorted(df["Category"].dropna().unique())
selected_category = st.sidebar.selectbox("Select Category", ["All"] + categories)
search_term = st.sidebar.text_input("Search Food by Name")
top_n = st.sidebar.slider("Show Top N", 5, 30, 10)

# Filter dataframe
filtered = df.copy()
if selected_category != "All":
    filtered = filtered[filtered["Category"] == selected_category]
if search_term:
    filtered = filtered[filtered["Food"].str.contains(search_term, case=False, na=False)]

# ----------------- Helpers -----------------
palette = alt.Scale(scheme="category20")

def prep_top(data: pd.DataFrame, nutrient: str, k: int) -> pd.DataFrame:
    """Make sure we have exactly one row per food for the chart."""
    d = data.copy()
    d = d.dropna(subset=[nutrient])
    # If a food appears multiple times, keep the row with the highest nutrient value
    d = (
        d.sort_values([ "Food", nutrient ], ascending=[ True, False ])
         .drop_duplicates(subset="Food", keep="first")
         .sort_values(nutrient, ascending=False)
         .head(k)
    )
    return d

def make_chart(data: pd.DataFrame, nutrient: str, title: str):
    # Domain to avoid autosum illusions and keep axis tidy
    xmax = float(data[nutrient].max()) if not data.empty else 0
    chart = (
        alt.Chart(data)
        .mark_bar()
        .encode(
            x=alt.X(f"{nutrient}:Q",
                    title=f"{nutrient} (per 100 g)",
                    scale=alt.Scale(domain=[0, xmax * 1.05]),
                    axis=alt.Axis(labelAngle=0)),
            y=alt.Y("Food:N", sort="-x", axis=alt.Axis(labelLimit=650, title=None)),
            color=alt.Color("Category:N", scale=palette,
                            legend=alt.Legend(title="Category", orient="right")),
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

# Top Protein
top_protein = prep_top(filtered, "Protein (g)", top_n)
st.subheader("🥩 Top Protein Foods (per 100 g)")
st.altair_chart(make_chart(top_protein, "Protein (g)", "Top Protein Foods"), use_container_width=True)
st.caption("📌 All nutrient values are expressed per 100 g of food.")
st.dataframe(top_protein, use_container_width=True)

# Top Fiber
top_fiber = prep_top(filtered, "Fiber (g)", top_n)
st.subheader("🌾 Top Fiber Foods (per 100 g)")
st.altair_chart(make_chart(top_fiber, "Fiber (g)", "Top Fiber Foods"), use_container_width=True)
st.caption("📌 All nutrient values are expressed per 100 g of food.")
st.dataframe(top_fiber, use_container_width=True)

# Top Sugar & Fat (tabs)
tab1, tab2 = st.tabs(["🍭 Top Sugary Foods", "🍟 Top Fatty Foods"])

with tab1:
    top_sugar = prep_top(filtered, "Sugar (g)", top_n)
    st.subheader("🍭 Top Sugary Foods (per 100 g)")
    st.altair_chart(make_chart(top_sugar, "Sugar (g)", "Top Sugary Foods"), use_container_width=True)
    st.caption("📌 All nutrient values are expressed per 100 g of food.")
    st.dataframe(top_sugar, use_container_width=True)

with tab2:
    top_fat = prep_top(filtered, "Fat (g)", top_n)
    st.subheader("🍟 Top Fatty Foods (per 100 g)")
    st.altair_chart(make_chart(top_fat, "Fat (g)", "Top Fatty Foods"), use_container_width=True)
    st.caption("📌 All nutrient values are expressed per 100 g of food.")
    st.dataframe(top_fat, use_container_width=True)

# Optional: quick sanity note if anything looks impossible
if (df["Protein (g)"] > 120).any():
    st.info("ℹ️ Charts now de-duplicate by food name to prevent sums; "
            "if you still see extreme values, they come from the source CSV.")
