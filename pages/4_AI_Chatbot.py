# pages/4_AI_Chatbot.py
import streamlit as st
from openai import OpenAI
import os
from dotenv import load_dotenv
from common import set_page_config, apply_custom_styles

# --- Config ---
set_page_config()
apply_custom_styles()

load_dotenv()  # only needed locally
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ----------------- Config -----------------
st.set_page_config(page_title="AI Nutrition Chatbot", layout="wide")
st.markdown("<h1 style='text-align: center;'>🤖 AI Nutrition Assistant</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: gray;'>Chat naturally about your diet, nutrition & healthy swaps</p>", unsafe_allow_html=True)
st.markdown("---")

# ----------------- Check Login -----------------
if "logged_in" in st.session_state and st.session_state["logged_in"]:
    profile = st.session_state["user_profile"]
    username = profile.get("username", "User")

    user_context = f"""
    The user is {profile.get('age', 'N/A')} years old, weighs {profile.get('weight', 'N/A')} kg,
    is {profile.get('height', 'N/A')} cm tall, and identifies as {profile.get('gender', 'N/A')}.
    Their activity level is {profile.get('activity', 'N/A')}.
    """
    greeting = f"👋 Hello **{username}**! How can I help you with your nutrition and health today?"
else:
    profile = None
    user_context = "The user is not logged in, so no personal details are available."
    greeting = "👋 Hello! How can I help you with your nutrition and health today?"

# ----------------- Chat State -----------------
if "chat_history" not in st.session_state:
    # Initialize chat with greeting
    st.session_state["chat_history"] = [("Bot", greeting)]
else:
    # If user logged in and greeting is still generic → update with username greeting
    if st.session_state["chat_history"][0][1].startswith("👋 Hello!") and "logged_in" in st.session_state and st.session_state["logged_in"]:
        st.session_state["chat_history"][0] = ("Bot", greeting)

# ----------------- Show Chat -----------------
st.subheader("💬 Chat")

for sender, msg in st.session_state["chat_history"]:
    if sender == "You":
        st.markdown(
            f"<div style='background-color:#DCF8C6; padding:10px; border-radius:10px; margin:5px 0; text-align:right;'>"
            f"<b>🧑 You:</b> {msg}</div>",
            unsafe_allow_html=True
        )
    else:
        # Bot bubble with container
        st.markdown(
            "<div style='background-color:#F1F0F0; padding:10px; border-radius:10px; margin:5px 0; text-align:left;'>",
            unsafe_allow_html=True,
        )
        # ✅ Render bot message as Markdown so **bold**, _italic_, etc. work
        st.markdown(f"**🤖 Bot:** {msg}")
        st.markdown("</div>", unsafe_allow_html=True)



# ----------------- Input Field -----------------
user_input = st.chat_input("Type your message...")

if user_input:
    st.session_state["chat_history"].append(("You", user_input))

    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a friendly nutrition assistant."},
                {"role": "system", "content": user_context},
                *[
                    {"role": "user" if s == "You" else "assistant", "content": m}
                    for s, m in st.session_state["chat_history"]
                ],
            ]
        )
        answer = completion.choices[0].message.content
    except Exception as e:
        answer = f"⚠️ Error: {str(e)}"

    st.session_state["chat_history"].append(("Bot", answer))
    st.rerun()

# ----------------- Reset Option -----------------
if st.button("🧹 Clear Chat"):
    st.session_state["chat_history"] = [("Bot", greeting)]
    st.rerun()
