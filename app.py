import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
import os
import tempfile
import json
from datetime import datetime

# Load API key
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Page config
st.set_page_config(
    page_title="SiteVoice",
    page_icon="🔧",
    layout="wide"
)

# System prompt
SYSTEM_PROMPT = """You are SiteVoice, a friendly and efficient AI assistant for tradies (tradespeople like plumbers, electricians, builders, etc.).

You help them manage their work day with voice commands. You can:
- Schedule and manage jobs (use the create_job function)
- View upcoming jobs (use the list_jobs function)
- Add notes to existing jobs (use the add_note function)
- Create quotes (use the create_quote function)

IMPORTANT: When a tradie asks you to schedule/book/create a job, ALWAYS use the create_job function.
When they ask what jobs they have, ALWAYS use the list_jobs function.
When they want to add a note to a job, ALWAYS use the add_note function.
When they want a quote, ALWAYS use the create_quote function.

Keep responses short and practical - tradies are busy. Talk like a helpful mate, not a robot. Use Australian English."""

# Define the tools/functions the AI can call
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_job",
            "description": "Schedule a new job for the tradie",
            "parameters": {
                "type": "object",
                "properties": {
                    "client_name": {"type": "string", "description": "Customer name"},
                    "description": {"type": "string", "description": "What the job is (e.g. fix leaky tap)"},
                    "date": {"type": "string", "description": "When the job is scheduled"},
                    "time": {"type": "string", "description": "Time of the job"},
                    "address": {"type": "string", "description": "Job location if mentioned"},
                },
                "required": ["client_name", "description", "date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_jobs",
            "description": "List all scheduled jobs",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_note",
            "description": "Add a note to an existing job",
            "parameters": {
                "type": "object",
                "properties": {
                    "client_name": {"type": "string", "description": "Which client's job to add the note to"},
                    "note": {"type": "string", "description": "The note to add"},
                },
                "required": ["client_name", "note"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_quote",
            "description": "Create a quote/estimate for a job",
            "parameters": {
                "type": "object",
                "properties": {
                    "client_name": {"type": "string", "description": "Customer name"},
                    "description": {"type": "string", "description": "What the job is"},
                    "amount": {"type": "number", "description": "Quote amount in dollars"},
                    "details": {"type": "string", "description": "Breakdown of costs if provided"},
                },
                "required": ["client_name", "description", "amount"]
            }
        }
    }
]

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "jobs" not in st.session_state:
    st.session_state.jobs = []
if "quotes" not in st.session_state:
    st.session_state.quotes = []

# --- FUNCTION HANDLERS ---
def handle_create_job(args):
    job = {
        "id": len(st.session_state.jobs) + 1,
        "client_name": args.get("client_name", "Unknown"),
        "description": args.get("description", ""),
        "date": args.get("date", "TBD"),
        "time": args.get("time", "TBD"),
        "address": args.get("address", "Not specified"),
        "notes": [],
        "status": "Scheduled",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    st.session_state.jobs.append(job)
    return f"Job created: {job['description']} for {job['client_name']} on {job['date']} at {job['time']}"

def handle_list_jobs(args):
    if not st.session_state.jobs:
        return "No jobs scheduled yet."
    job_list = []
    for job in st.session_state.jobs:
        job_list.append(f"- {job['description']} for {job['client_name']} on {job['date']} at {job['time']} [{job['status']}]")
    return "Here are your jobs:\n" + "\n".join(job_list)

def handle_add_note(args):
    client_name = args.get("client_name", "").lower()
    note = args.get("note", "")
    for job in st.session_state.jobs:
        if client_name in job["client_name"].lower():
            job["notes"].append(note)
            return f"Note added to {job['client_name']}'s job: {note}"
    return f"Couldn't find a job for {args.get('client_name')}. Try listing your jobs first."

def handle_create_quote(args):
    quote = {
        "id": len(st.session_state.quotes) + 1,
        "client_name": args.get("client_name", "Unknown"),
        "description": args.get("description", ""),
        "amount": args.get("amount", 0),
        "details": args.get("details", ""),
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    st.session_state.quotes.append(quote)
    return f"Quote created for {quote['client_name']}: ${quote['amount']:.2f} for {quote['description']}"

FUNCTION_MAP = {
    "create_job": handle_create_job,
    "list_jobs": handle_list_jobs,
    "add_note": handle_add_note,
    "create_quote": handle_create_quote,
}

def process_ai_response(messages):
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        tools=TOOLS,
    )
    message = response.choices[0].message

    # Check if AI wants to call a function
    if message.tool_calls:
        # Add the assistant message with tool calls
        messages.append(message)

        for tool_call in message.tool_calls:
            func_name = tool_call.function.name
            func_args = json.loads(tool_call.function.arguments)

            # Execute the function
            if func_name in FUNCTION_MAP:
                result = FUNCTION_MAP[func_name](func_args)
            else:
                result = "Unknown function"

            # Add function result to messages
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result
            })

        # Get final response after function execution
        final_response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
        )
        return final_response.choices[0].message.content
    else:
        return message.content


# --- SIDEBAR: JOB BOARD ---
with st.sidebar:
    st.markdown("## 📋 Job Board")

    if st.session_state.jobs:
        for job in st.session_state.jobs:
            with st.expander(f"🔧 {job['client_name']} — {job['date']}"):
                st.write(f"**Job:** {job['description']}")
                st.write(f"**Time:** {job['time']}")
                st.write(f"**Address:** {job['address']}")
                st.write(f"**Status:** {job['status']}")
                if job['notes']:
                    st.write("**Notes:**")
                    for note in job['notes']:
                        st.write(f"  • {note}")
    else:
        st.write("No jobs yet. Tell SiteVoice to schedule one!")

    st.markdown("---")
    st.markdown("## 💰 Quotes")

    if st.session_state.quotes:
        for quote in st.session_state.quotes:
            with st.expander(f"💰 {quote['client_name']} — ${quote['amount']:.2f}"):
                st.write(f"**Job:** {quote['description']}")
                st.write(f"**Amount:** ${quote['amount']:.2f}")
                if quote['details']:
                    st.write(f"**Details:** {quote['details']}")
    else:
        st.write("No quotes yet. Ask SiteVoice to create one!")


# --- MAIN CHAT AREA ---
st.title("🔧 SiteVoice")
st.subheader("Voice-powered AI assistant for tradies")
st.write("Speak to manage your jobs, quotes, and schedule — hands-free.")

# Voice recording
st.markdown("### 🎤 Tap to speak")
audio_data = st.audio_input("Record your message")

# Process voice input
# Process voice input
voice_text = None
if "last_audio" not in st.session_state:
    st.session_state.last_audio = None

if audio_data is not None:
    audio_bytes = audio_data.getvalue()
    if audio_bytes != st.session_state.last_audio:
        st.session_state.last_audio = audio_bytes
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio_bytes)
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
    if isinstance(message, dict) and message.get("role") in ["user", "assistant"]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# Handle input
prompt = voice_text if voice_text else st.chat_input("Or type your message here...")

if prompt:
    if voice_text:
        st.info(f'🎤 Heard: "{voice_text}"')

    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Build messages for API
    api_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in st.session_state.messages:
        if isinstance(msg, dict) and msg.get("role") in ["user", "assistant"]:
            api_messages.append(msg)

    # Get AI response with function calling
    with st.chat_message("assistant"):
        reply = process_ai_response(api_messages)
        st.markdown(reply)

        # Voice output
        speech_response = client.audio.speech.create(
            model="tts-1",
            voice="onyx",
            input=reply
        )
        st.audio(speech_response.content, format="audio/mp3", autoplay=True)

    # Save assistant response
    st.session_state.messages.append({"role": "assistant", "content": reply})
    st.rerun()
