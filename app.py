import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
import os

# Load API key
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Page config
st.set_page_config(
    page_title="SiteVoice",
    page_icon="🔧",
    layout="wide"
)

st.title("🔧 SiteVoice")
st.subheader("Voice-powered AI assistant for tradies")

# System prompt - this is what makes our agent a tradie assistant
SYSTEM_PROMPT = """You are SiteVoice, a friendly and efficient AI assistant for tradies (tradespeople like plumbers, electricians, builders, etc.).

You help them manage their work day with voice commands. You can:
- Schedule and manage jobs
- Create quotes and invoices
- Take job notes
- Track materials and costs
- Answer trade-related questions

Keep responses short and practical - tradies are busy. Talk like a helpful mate, not a robot. Use Australian English."""

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Type or speak your message..."):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Get AI response
    with st.chat_message("assistant"):
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                *st.session_state.messages
            ]
        )
        reply = response.choices[0].message.content
        st.markdown(reply)

    # Save assistant response
    st.session_state.messages.append({"role": "assistant", "content": reply})