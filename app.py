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

# --- TIME-AWARE GREETING ---
def get_greeting():
    hour = datetime.now().hour
    if hour < 12:
        return "Good morning"
    elif hour < 17:
        return "Good arvo"
    else:
        return "Good evening"

# System prompt - more personality and smarts
SYSTEM_PROMPT = f"""You are SiteVoice, a friendly and efficient AI assistant for tradies (tradespeople like plumbers, electricians, builders, etc.) in Australia.

Current date and time: {datetime.now().strftime("%A, %d %B %Y, %I:%M %p")}

Your personality:
- You're like a reliable office manager who's also a mate
- Keep it casual but professional — use "mate", "no worries", "sorted", "legend" naturally
- Be brief — tradies are busy, don't waffle on
- If something's unclear, ask a quick clarifying question rather than guessing
- When you create a job, always confirm the details back
- When listing jobs, organize them by date
- If a tradie seems stressed, be encouraging

You help them manage their work day with voice commands. You can:
- Schedule and manage jobs (use the create_job function)
- View upcoming jobs (use the list_jobs function)
- Add notes to existing jobs (use the add_note function)
- Create quotes (use the create_quote function)
- Update job status (use the update_job_status function)
- Get a daily summary (use the daily_summary function)

IMPORTANT: When a tradie asks you to schedule/book/create a job, ALWAYS use the create_job function.
When they ask what jobs they have, ALWAYS use the list_jobs function.
When they want to add a note to a job, ALWAYS use the add_note function.
When they want a quote, ALWAYS use the create_quote function.
When they say a job is done/complete/finished, ALWAYS use the update_job_status function.
When they ask for a summary of their day or what's on, ALWAYS use the daily_summary function.

Keep responses short — aim for 1-3 sentences max. Use Australian English."""

# Define the tools/functions
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
                    "description": {"type": "string", "description": "What the job is"},
                    "date": {"type": "string", "description": "When the job is scheduled"},
                    "time": {"type": "string", "description": "Time of the job"},
                    "address": {"type": "string", "description": "Job location if mentioned"},
                    "priority": {"type": "string", "enum": ["low", "normal", "urgent"], "description": "Job priority level"},
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
    },
    {
        "type": "function",
        "function": {
            "name": "update_job_status",
            "description": "Update the status of a job (e.g. mark as complete, in progress)",
            "parameters": {
                "type": "object",
                "properties": {
                    "client_name": {"type": "string", "description": "Which client's job to update"},
                    "status": {"type": "string", "enum": ["Scheduled", "In Progress", "Complete", "Cancelled"], "description": "New status"},
                },
                "required": ["client_name", "status"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "daily_summary",
            "description": "Get a summary of today's jobs and upcoming work",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
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
if "last_audio" not in st.session_state:
    st.session_state.last_audio = None

# --- FUNCTION HANDLERS ---
def handle_create_job(args):
    priority = args.get("priority", "normal")
    job = {
        "id": len(st.session_state.jobs) + 1,
        "client_name": args.get("client_name", "Unknown"),
        "description": args.get("description", ""),
        "date": args.get("date", "TBD"),
        "time": args.get("time", "TBD"),
        "address": args.get("address", "Not specified"),
        "priority": priority,
        "notes": [],
        "status": "Scheduled",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    st.session_state.jobs.append(job)
    return f"Job created: {job['description']} for {job['client_name']} on {job['date']} at {job['time']} (Priority: {priority})"

def handle_list_jobs(args):
    if not st.session_state.jobs:
        return "No jobs scheduled yet. Your calendar is clear, mate!"
    job_list = []
    for job in st.session_state.jobs:
        status_emoji = {"Scheduled": "📅", "In Progress": "🔨", "Complete": "✅", "Cancelled": "❌"}.get(job["status"], "📅")
        priority_flag = " 🚨 URGENT" if job["priority"] == "urgent" else ""
        job_list.append(f"- {status_emoji} {job['description']} for {job['client_name']} on {job['date']} at {job['time']} [{job['status']}]{priority_flag}")
    return "Here are your jobs:\n" + "\n".join(job_list)

def handle_add_note(args):
    client_name = args.get("client_name", "").lower()
    note = args.get("note", "")
    for job in st.session_state.jobs:
        if client_name in job["client_name"].lower():
            job["notes"].append({"text": note, "time": datetime.now().strftime("%I:%M %p")})
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

def handle_update_job_status(args):
    client_name = args.get("client_name", "").lower()
    new_status = args.get("status", "Scheduled")
    for job in st.session_state.jobs:
        if client_name in job["client_name"].lower():
            job["status"] = new_status
            return f"Job for {job['client_name']} updated to: {new_status}"
    return f"Couldn't find a job for {args.get('client_name')}."

def handle_daily_summary(args):
    total = len(st.session_state.jobs)
    scheduled = len([j for j in st.session_state.jobs if j["status"] == "Scheduled"])
    in_progress = len([j for j in st.session_state.jobs if j["status"] == "In Progress"])
    complete = len([j for j in st.session_state.jobs if j["status"] == "Complete"])
    urgent = len([j for j in st.session_state.jobs if j["priority"] == "urgent"])
    total_quotes = len(st.session_state.quotes)
    quote_value = sum(q["amount"] for q in st.session_state.quotes)

    summary = f"Here's your day at a glance:\n"
    summary += f"- Total jobs: {total}\n"
    summary += f"- Scheduled: {scheduled}\n"
    summary += f"- In progress: {in_progress}\n"
    summary += f"- Complete: {complete}\n"
    if urgent > 0:
        summary += f"- 🚨 Urgent jobs: {urgent}\n"
    summary += f"- Quotes sent: {total_quotes} (${quote_value:.2f} total value)\n"
    return summary

FUNCTION_MAP = {
    "create_job": handle_create_job,
    "list_jobs": handle_list_jobs,
    "add_note": handle_add_note,
    "create_quote": handle_create_quote,
    "update_job_status": handle_update_job_status,
    "daily_summary": handle_daily_summary,
}

def process_ai_response(messages):
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        tools=TOOLS,
    )
    message = response.choices[0].message

    if message.tool_calls:
        messages.append(message)
        for tool_call in message.tool_calls:
            func_name = tool_call.function.name
            func_args = json.loads(tool_call.function.arguments)
            if func_name in FUNCTION_MAP:
                result = FUNCTION_MAP[func_name](func_args)
            else:
                result = "Unknown function"
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result
            })
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
            status_emoji = {"Scheduled": "📅", "In Progress": "🔨", "Complete": "✅", "Cancelled": "❌"}.get(job["status"], "📅")
            priority_color = "🔴" if job["priority"] == "urgent" else "🟡" if job["priority"] == "normal" else "🟢"

            with st.expander(f"{status_emoji} {job['client_name']} — {job['date']}"):
                st.write(f"**Job:** {job['description']}")
                st.write(f"**Time:** {job['time']}")
                st.write(f"**Address:** {job['address']}")
                st.write(f"**Priority:** {priority_color} {job['priority'].title()}")
                st.write(f"**Status:** {job['status']}")
                if job['notes']:
                    st.write("**Notes:**")
                    for note in job['notes']:
                        if isinstance(note, dict):
                            st.write(f"  • [{note['time']}] {note['text']}")
                        else:
                            st.write(f"  • {note}")
    else:
        st.info("No jobs yet — tell SiteVoice to schedule one!")

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
        st.info("No quotes yet — ask SiteVoice to create one!")

    # Quick stats at the bottom of sidebar
    st.markdown("---")
    st.markdown("## 📊 Quick Stats")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Jobs", len(st.session_state.jobs))
    with col2:
        st.metric("Quotes", len(st.session_state.quotes))

    if st.session_state.quotes:
        total_value = sum(q["amount"] for q in st.session_state.quotes)
        st.metric("Quote Value", f"${total_value:,.2f}")

    complete_jobs = len([j for j in st.session_state.jobs if j["status"] == "Complete"])
    if st.session_state.jobs:
        completion_rate = int((complete_jobs / len(st.session_state.jobs)) * 100)
        
        # Color based on completion: red -> yellow -> green
        if completion_rate < 33:
            bar_color = "#e74c3c"  # Red
        elif completion_rate < 66:
            bar_color = "#f39c12"  # Yellow/Orange
        else:
            bar_color = "#2ecc71"  # Green
        
        st.markdown(f"**Completion: {completion_rate}%**")
        st.markdown(
            f"""
            <div style="background-color: #ddd; border-radius: 10px; height: 20px; width: 100%;">
                <div style="background-color: {bar_color}; width: {completion_rate}%; height: 20px; border-radius: 10px; transition: width 0.5s;"></div>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.markdown("**Completion: N/A**")


# --- MAIN CHAT AREA ---
st.title("🔧 SiteVoice")
st.subheader("Voice-powered AI assistant for tradies")
st.caption(f"{get_greeting()}, mate! Speak or type to manage your day.")

# Quick action buttons
st.markdown("### ⚡ Quick Actions")
col1, col2, col3, col4 = st.columns(4)

quick_prompt = None
with col1:
    if st.button("📋 My Jobs", use_container_width=True):
        quick_prompt = "What jobs do I have?"
with col2:
    if st.button("📊 Day Summary", use_container_width=True):
        quick_prompt = "Give me a summary of my day"
with col3:
    if st.button("➕ New Job", use_container_width=True):
        quick_prompt = "I need to schedule a new job"
with col4:
    if st.button("💰 New Quote", use_container_width=True):
        quick_prompt = "I need to create a new quote"





# Display chat history
for message in st.session_state.messages:
    if isinstance(message, dict) and message.get("role") in ["user", "assistant"]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# Voice recording - placed near the bottom so it's always accessible
st.markdown("### 🎤 Tap to speak")
audio_data = st.audio_input("Record your message")

# Process voice input
voice_text = None
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

# Handle input - voice, quick action buttons, or text
prompt = voice_text or quick_prompt or st.chat_input("Or type your message here...")

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

    # Get AI response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
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

