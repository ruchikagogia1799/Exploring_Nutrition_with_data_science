# pages/1_Register_or_Login.py
import streamlit as st
from db import register_user, login_user, user_exists


st.title("🔐 Authentication")
tabs = st.tabs(["📝 Register", "🔑 Login"])

# -------------------- REGISTER TAB --------------------
with tabs[0]:
    st.subheader("Create a new account")

    with st.form("register_form"):
        username = st.text_input("Username", placeholder="Enter your username")
        email = st.text_input("Email", placeholder="Enter your email")
        password = st.text_input("Password", type="password", placeholder="Enter your password")

        weight_str = st.text_input("Weight (kg)", placeholder="Enter your weight")
        height_str = st.text_input("Height (cm)", placeholder="Enter your height")
        age_str = st.text_input("Age", placeholder="Enter your age")

        gender = st.selectbox("Gender", ["Male", "Female", "Other"])
        activity = st.selectbox(
            "Activity Level",
            ["Sedentary", "Lightly Active", "Moderately Active", "Very Active", "Extra Active"]
        )

        submitted = st.form_submit_button("Register")

    if submitted:
        # Validate required fields
        if not username or not email or not password:
            st.error("⚠️ Please fill in all required fields.")
            st.stop()

        # Validate numeric fields
        try:
            weight = float(weight_str)
            height = float(height_str)
            age = int(age_str)
        except ValueError:
            st.error("⚠️ Please enter valid numeric values for weight, height, and age.")
            st.stop()

        # Check duplicates
        if user_exists(username, email):
            st.error("⚠️ Username or email already exists.")
        else:
            success = register_user(username, email, password, weight, height, age, gender, activity)
            if success:
                st.success("✅ Account created successfully! Please log in now.")
                st.balloons()
                st.rerun()
            else:
                st.error("❌ Error creating account. Try again later.")

# -------------------- LOGIN TAB --------------------
with tabs[1]:
    st.subheader("Login to your account")

    with st.form("login_form"):
        username_or_email = st.text_input("Username or Email", placeholder="Enter your username or email")
        password_login = st.text_input("Password", type="password", placeholder="Enter your password")
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

                st.success(f"✅ Successfully logged in as **{user['username']}**!")
                st.balloons()
                st.info("➡️ Now go to **Body Metrics** or **Meal Planner** to continue.")
            else:
                st.error("❌ Invalid credentials. Please try again.")
