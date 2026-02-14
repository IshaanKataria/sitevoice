import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
import os
import tempfile

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
st.write("Speak to manage your jobs, quotes, and schedule — hands-free.")

# System prompt
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

# Voice recording section
st.markdown("### 🎤 Tap to speak")
audio_data = st.audio_input("Record your message")

# Process voice input
voice_text = None
if audio_data is not None:
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(audio_data.getvalue())
        f.flush()
        with open(f.name, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="en"
            )
            voice_text = transcript.text
    os.unlink(f.name)

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Handle voice or text input
prompt = voice_text if voice_text else st.chat_input("Or type your message here...")

if prompt:
    if voice_text:
        st.info(f'🎤 Heard: "{voice_text}"')

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

        # Generate voice response
        speech_response = client.audio.speech.create(
            model="tts-1",
            voice="onyx",
            input=reply
        )
        audio_bytes = speech_response.content
        st.audio(audio_bytes, format="audio/mp3", autoplay=True)

    # Save assistant response
    st.session_state.messages.append({"role": "assistant", "content": reply})
    