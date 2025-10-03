# pages/1_Register_Login.py
import streamlit as st
import bcrypt
from db import register_user, login_user, user_exists
from common import set_page_config, apply_custom_styles

# --- Config ---
set_page_config()
apply_custom_styles()
st.set_page_config(page_title="Authentication", layout="wide")

st.title("🔐 Authentication")
tabs = st.tabs(["📝 Register", "🔑 Login"])

# -------------------- REGISTER TAB --------------------
with tabs[0]:
    st.subheader("Create a new account")

    with st.form("register_form"):
        username = st.text_input("Username")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        weight = st.number_input("Weight (kg)", min_value=20, max_value=200, step=1)
        height = st.number_input("Height (cm)", min_value=100, max_value=220, step=1)
        age = st.number_input("Age", min_value=10, max_value=100, step=1)
        gender = st.selectbox("Gender", ["Male", "Female"])
        activity = st.selectbox(
            "Activity Level",
            ["Sedentary", "Lightly Active", "Moderately Active", "Very Active", "Extra Active"]
        )

        submitted = st.form_submit_button("Register")

    if submitted:
        if not username or not email or not password:
            st.error("⚠️ Please fill in all required fields.")
        elif user_exists(username, email):
            st.error("⚠️ Username or email already exists.")
        else:
            hashed_pw = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
            success = register_user(username, email, hashed_pw, weight, height, age, gender, activity)
            if success:
                st.success("✅ Account created successfully! Please log in now.")
                st.balloons()
            else:
                st.error("❌ Error creating account. Try again later.")

# -------------------- LOGIN TAB --------------------
with tabs[1]:
    st.subheader("Login to your account")

    with st.form("login_form"):
        username_or_email = st.text_input("Username or Email")
        password_login = st.text_input("Password", type="password")
        login_btn = st.form_submit_button("Login")

    if login_btn:
        if not username_or_email or not password_login:
            st.error("⚠️ Please enter your credentials.")
        else:
            user = login_user(username_or_email, password_login)

            if user:
                # Always return dict
                if hasattr(user, "_mapping"):
                    user = dict(user._mapping)
                else:
                    user = dict(user)

                st.session_state["logged_in"] = True
                st.session_state["user_profile"] = user
                st.session_state["username"] = user.get("username", "User")

                # ✅ Show success message immediately
                st.success(f"✅ Successfully logged in as **{user['username']}**!")
                st.balloons()

                # Small navigation info
                st.info("➡️ Now go to **Body Metrics** or **Meal Planner** to continue.")
            else:
                st.error("❌ Invalid credentials. Please try again.")
