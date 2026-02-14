import streamlit as st
from openai import OpenAI

# Page config
st.set_page_config(
    page_title="SiteVoice",
    page_icon="🔧",
    layout="wide"
)

st.title("🔧 SiteVoice")
st.subheader("Voice-powered AI assistant for tradies")
st.write("Speak to manage your jobs, quotes, and schedule — hands-free.")
