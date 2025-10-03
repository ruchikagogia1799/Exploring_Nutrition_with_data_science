# pages/2_Body_Metrics.py
import streamlit as st
from db import update_user
from common import set_page_config, apply_custom_styles

# --- Config ---
set_page_config()
apply_custom_styles()
st.set_page_config(page_title="Body Metrics", layout="wide")

# ---------------- Ensure Login ----------------
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.warning("⚠️ Please log in first from the Auth page.")
    st.stop()

profile = st.session_state["user_profile"]

# ---------------- Helper Functions ----------------
def calculate_bmr(weight, height, age, gender):
    """Mifflin-St Jeor formula"""
    if gender.lower() == "male":
        return 10*weight + 6.25*height - 5*age + 5
    else:
        return 10*weight + 6.25*height - 5*age - 161

def activity_multiplier(activity):
    return {
        "Sedentary": 1.2,
        "Lightly Active": 1.375,
        "Moderately Active": 1.55,
        "Very Active": 1.725,
        "Extra Active": 1.9
    }.get(activity, 1.2)

def calculate_macros(tdee):
    return {
        "Protein": f"{int(tdee*0.25/4)} g/day",
        "Carbs": f"{int(tdee*0.50/4)} g/day",
        "Fat": f"{int(tdee*0.25/9)} g/day",
        "Fiber": f"{int(14 * tdee / 1000)} g/day",
        "Sugar (limit)": f"{int(tdee*0.10/4)} g/day"
    }

# ---------------- Main UI ----------------
st.title("📊 Body Metrics & Calorie Needs")

# Collapsible edit form
edit_mode = st.checkbox("✏️ Edit my details")

if edit_mode:
    with st.form("edit_form"):
        new_weight = st.number_input(
            "Weight (kg)", 
            min_value=20.0, max_value=200.0, value=float(profile["weight"]), step=0.5
        )
        new_height = st.number_input(
            "Height (cm)", 
            min_value=100.0, max_value=220.0, value=float(profile["height"]), step=0.5
        )
        new_age = st.number_input(
            "Age", 
            min_value=10, max_value=100, value=int(profile["age"]), step=1
        )
        new_gender = st.selectbox(
            "Gender", ["Male", "Female"], 
            index=0 if profile["gender"].lower() == "male" else 1
        )
        new_activity = st.selectbox(
            "Activity Level",
            ["Sedentary", "Lightly Active", "Moderately Active", "Very Active", "Extra Active"],
            index=["Sedentary", "Lightly Active", "Moderately Active", "Very Active", "Extra Active"].index(profile.get("activity", "Sedentary"))
        )

        submitted = st.form_submit_button("💾 Save Changes")

    if submitted:
        updates = {
            "weight": new_weight,
            "height": new_height,
            "age": new_age,
            "gender": new_gender,
            "activity": new_activity
        }
        if update_user(profile["id"], updates):
            st.success("✅ Profile updated successfully!")
            st.session_state["user_profile"].update(updates)
        else:
            st.error("❌ Failed to update profile.")

# ---------------- Display Profile ----------------
st.markdown(f"### 👋 Hello **{profile['username']}**")

col1, col2 = st.columns([1.2, 1])

with col1:
    st.markdown("#### 📋 Personal Details")
    st.write(f"- **Age:** {profile['age']} years")
    st.write(f"- **Weight:** {profile['weight']} kg")
    st.write(f"- **Height:** {profile['height']} cm")
    st.write(f"- **Gender:** {profile['gender']}")
    st.write(f"- **Activity Level:** {profile['activity']}")

    # Calculate BMR and TDEE
    bmr = calculate_bmr(profile["weight"], profile["height"], profile["age"], profile["gender"])
    tdee = bmr * activity_multiplier(profile["activity"])

    st.markdown("#### 🔥 Calorie Needs")
    st.metric("BMR", f"{bmr:.0f} kcal/day")
    st.metric("TDEE", f"{tdee:.0f} kcal/day")

with col2:
    st.markdown("#### 🍎 Recommended Macros (per day)")
    macros = calculate_macros(tdee)
    for k, v in macros.items():
        st.write(f"- **{k}:** {v}")

    st.info("📌 Use these numbers to guide your Meal Planner & Diet Tracker.")

# ---------------- Store in Session ----------------
st.session_state["bmr"] = bmr
st.session_state["tdee"] = tdee
st.session_state["macros"] = macros
