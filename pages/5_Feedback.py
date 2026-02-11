# pages/Feedback.py — Feedback & Support page for Streamlit Nutrition App
import streamlit as st
import psycopg2
import os
from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path

st.set_page_config(page_title="💬 Feedback & Support", layout="wide")
st.title("💬 Feedback & Support")
st.write("Share your thoughts, feature requests, or report any issues below. Your feedback helps improve the app!")

# ---------------------------------------------------------
# LOAD ENVIRONMENT VARIABLES
# ---------------------------------------------------------
# Always load .env manually from project root
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

def get_env_var(name: str) -> str:
    """
    Return variable from .env locally or st.secrets on Streamlit Cloud.
    This version avoids errors when secrets.toml does not exist.
    """
    try:
        if "NEON_HOST" in st.secrets:  # only true on Streamlit Cloud
            return st.secrets.get(name, "")
    except Exception:
        pass  # ignore if secrets.toml doesn't exist locally
    return os.getenv(name)

# ---------------------------------------------------------
# DATABASE CONNECTION
# ---------------------------------------------------------
@st.cache_resource
def get_conn():
    return psycopg2.connect(
        host=get_env_var("NEON_HOST"),
        dbname=get_env_var("NEON_DBNAME"),
        user=get_env_var("NEON_USER"),
        password=get_env_var("NEON_PASSWORD"),
        sslmode=get_env_var("NEON_SSLMODE") or "require"
    )

# ---------------------------------------------------------
# FEEDBACK FORM
# ---------------------------------------------------------
with st.form("feedback_form", clear_on_submit=True):
    st.subheader("📝 Submit Your Feedback or Query")
    name = st.text_input("Your Name")
    email = st.text_input("Your Email (used in login)")
    subject = st.text_input("Subject")
    message = st.text_area("Your Feedback / Query", height=150)
    submitted = st.form_submit_button("Submit Feedback")

    if submitted:
        if not (name and email and message):
            st.warning("⚠️ Please fill out all required fields.")
        else:
            try:
                conn = get_conn()
                cur = conn.cursor()
                # Create feedback table if it doesn't exist
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS feedback (
                        id SERIAL PRIMARY KEY,
                        name TEXT,
                        email TEXT,
                        subject TEXT,
                        message TEXT,
                        submitted_at TIMESTAMP
                    )
                """)
                # Insert feedback
                cur.execute("""
                    INSERT INTO feedback (name, email, subject, message, submitted_at)
                    VALUES (%s, %s, %s, %s, %s)
                """, (name, email, subject, message, datetime.now()))
                conn.commit()
                cur.close()
                conn.close()
                st.success("✅ Thank you! Your feedback has been recorded successfully.")
            except Exception as e:
                st.error(f"❌ Something went wrong while submitting feedback: {e}")

# ---------------------------------------------------------
# OPTIONAL CONTACT INFO
# ---------------------------------------------------------
st.markdown("---")
st.info("📩 For direct support or collaboration, you can also reach out via email at **ruchikagogia17@gmail.com**")
