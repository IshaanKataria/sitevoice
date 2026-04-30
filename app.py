import streamlit as st
import streamlit.components.v1 as components
from openai import OpenAI
from dotenv import load_dotenv
import os
import tempfile
import json
import base64
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

# Pin to Australian Eastern time so greetings + AI's "current time" reflect the user,
# not the cloud server's UTC. Sydney handles DST automatically.
APP_TZ = ZoneInfo("Australia/Sydney")


def now_local() -> datetime:
    return datetime.now(APP_TZ)
from plumbing_data import (
    PLUMBING_MATERIALS, LABOR_RATES, JOB_TEMPLATES,
    lookup_material, search_materials, get_job_template,
    get_all_categories, get_labor_rates_text
)
import db

# Load API key
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Page config
st.set_page_config(
    page_title="SiteVoice",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- WORKSPACE SETUP ---
# Tenant isolation via unguessable UUID in URL (?ws=...). No auth needed.
# Same pattern as Google Docs share links: knowing the URL = access.
_raw_ws = st.query_params.get("ws")
try:
    _ws_id = str(uuid.UUID(_raw_ws)) if _raw_ws else None
except (ValueError, AttributeError):
    _ws_id = None  # invalid UUID — silently mint a fresh one

if not _ws_id:
    _ws_id = str(uuid.uuid4())
    st.query_params["ws"] = _ws_id
    db.ensure_workspace(_ws_id)
elif "workspace_initialised" not in st.session_state:
    db.ensure_workspace(_ws_id)
    st.session_state.workspace_initialised = True
st.session_state.workspace_id = _ws_id

# --- CUSTOM CSS ---
st.markdown("""
<style>
    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
    }

    /* Sidebar text colors — readable on dark background */
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] .stMarkdown,
    section[data-testid="stSidebar"] [data-testid="stText"],
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
        color: #e2e8f0 !important;
    }
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        color: #f1f5f9 !important;
    }
    section[data-testid="stSidebar"] [data-testid="stMetricValue"] {
        color: #f1f5f9 !important;
    }
    section[data-testid="stSidebar"] [data-testid="stMetricLabel"] p {
        color: #94a3b8 !important;
    }
    section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {
        color: #94a3b8 !important;
    }
    section[data-testid="stSidebar"] .stExpander summary span {
        color: #e2e8f0 !important;
    }

    /* Sidebar expander — more visible border */
    section[data-testid="stSidebar"] .stExpander {
        border: 1px solid #334155 !important;
        border-radius: 8px !important;
        background: rgba(30, 41, 59, 0.5) !important;
    }

    /* Sidebar delete button — red tint so it's clearly visible (only target stButton, not expander toggles) */
    section[data-testid="stSidebar"] .stExpander [data-testid="stBaseButton-secondary"] {
        background: rgba(239, 68, 68, 0.15) !important;
        border: 1px solid rgba(239, 68, 68, 0.4) !important;
        color: #fca5a5 !important;
    }
    section[data-testid="stSidebar"] .stExpander [data-testid="stBaseButton-secondary"]:hover {
        background: rgba(239, 68, 68, 0.3) !important;
        border: 1px solid rgba(239, 68, 68, 0.6) !important;
        color: #fef2f2 !important;
    }

    /* Smaller font in sidebar for prices to prevent wrapping */
    section[data-testid="stSidebar"] .stExpander code {
        font-size: 11px !important;
    }

    /* Hide default streamlit elements for cleaner look */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    /* Keep header visible so sidebar toggle works, but hide inner content */
    header[data-testid="stHeader"] {
        background: transparent !important;
        backdrop-filter: none !important;
    }

    /* Sidebar width when open */
    section[data-testid="stSidebar"][aria-expanded="true"] {
        min-width: 340px !important;
        width: 340px !important;
    }

    /* Main content fills full width when sidebar is closed */
    .main .block-container {
        max-width: 100% !important;
        transition: padding 0.3s ease;
    }

    /* Hide audio recorder error message — functionally still works */
    [data-testid="stAudioInput"] [data-testid="stNotification"],
    [data-testid="stAudioInput"] .stAlert {
        display: none !important;
    }
    /* Hide the "An error has occurred" text inside audio widget */
    [data-testid="stAudioInput"] iframe + div,
    .stException, .element-container:has(.stException) {
        display: none !important;
    }

    /* Chat input at bottom */
    .stChatInput {
        position: sticky;
        bottom: 0;
        z-index: 998;
        background: #0e1117;
    }

    /* Quick action buttons — subtle styling */
    div[data-testid="stHorizontalBlock"] > div > div > button {
        font-size: 13px !important;
    }
</style>
""", unsafe_allow_html=True)


# --- TIME-AWARE GREETING ---
def get_greeting():
    hour = now_local().hour
    if 5 <= hour < 12:
        return "Good morning"
    elif 12 <= hour < 17:
        return "Good arvo"
    else:
        return "Good evening"


# --- PLUMBING KNOWLEDGE FOR AI ---
PLUMBING_KNOWLEDGE = f"""
You have access to a plumbing materials database with Australian pricing.

Available materials and prices:
{get_all_categories()}

Labor rates:
{get_labor_rates_text()}

Common job templates you know about:
- Hot water system replacement (electric): ~4 hours
- Hot water system replacement (gas continuous flow): ~5 hours
- Tap/mixer replacement: ~1 hour
- Toilet cistern repair: ~1 hour
- Full toilet replacement: ~2.5 hours
- Blocked drain clearing: ~1.5 hours
- Leaking pipe repair: ~1.5 hours
- Shower mixer installation: ~2 hours
"""

# System prompt
SYSTEM_PROMPT = f"""You are SiteVoice, a friendly and efficient AI assistant for plumbers in Australia.

Current date and time: {now_local().strftime("%A, %d %B %Y, %I:%M %p")} (AEST/AEDT, Sydney)

Your personality:
- You're like a reliable office manager who's also a mate
- Keep it casual but professional — use "mate", "no worries", "sorted", "legend" naturally
- Be brief — tradies are busy, don't waffle on
- If something's unclear, ask a quick clarifying question rather than guessing
- When you create a job, always confirm the details back
- If a tradie seems stressed, be encouraging

{PLUMBING_KNOWLEDGE}

You help plumbers manage their work day with voice commands. You can:
- Schedule and manage jobs (use the create_job function)
- View upcoming jobs (use the list_jobs function)
- Add notes to existing jobs (use the add_note function)
- Build interactive quotes with line items (use add_quote_line_item to add items one at a time)
- Look up material prices (use lookup_price function)
- Finalise a quote when done (use finalise_quote function)
- Update job status (use the update_job_status function)
- Get a daily summary (use the daily_summary function)
- Search for jobs by client name (use the search_jobs function)

QUOTING WORKFLOW — THIS IS CRITICAL:
When a tradie wants to create a quote, follow this interactive process:
1. Ask who the quote is for (client name) and what the job is
2. Start a new quote with start_quote
3. Ask about the specifics — what parts, materials, access issues, etc.
4. Add line items one at a time using add_quote_line_item as details emerge
5. Suggest materials and prices from your database when relevant
6. Ask if there's anything else to add
7. When they're happy, ALWAYS call finalise_quote to lock it in
8. Keep the conversation natural — you're building the quote WITH them, not interrogating them

CRITICAL FINALISATION RULE:
- When the tradie says ANYTHING like "that's it", "lock it in", "done", "finalise it", "wrap it up", "finish it", "that's all", "good to go", "send it", "looks good" → you MUST call finalise_quote immediately
- You MUST call the finalise_quote function tool — do NOT just say "the quote is done" without actually calling the function
- If you add the last items and the tradie wants to finish, call add_quote_line_item AND finalise_quote in the same response
- NEVER leave a quote in draft status if the tradie has indicated they want to finish

For example, if a plumber says "I need a quote for Karen, hot water replacement":
- Start the quote, ask what model/brand they're looking at
- Add the HWS unit as a line item
- Ask about pipework condition, valves needed
- Add those as line items
- Add labor based on estimated hours
- Suggest the callout fee
- Total it up and call finalise_quote

IMPORTANT RULES:
- When a tradie asks to schedule/book/create a job → use create_job
- When they ask what jobs they have → use list_jobs
- When they want to add a note → use add_note
- When they want a quote → start the interactive quoting workflow
- When they say a job is done/complete/finished → use update_job_status
- When they ask for a summary → use daily_summary
- When they ask about a specific client's jobs → use search_jobs
- When they ask about a material price → use lookup_price

Keep responses short — aim for 1-3 sentences max. Use Australian English."""

# Define tools/functions
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
            "name": "start_quote",
            "description": "Start building a new interactive quote. Call this when a tradie wants to create a quote.",
            "parameters": {
                "type": "object",
                "properties": {
                    "client_name": {"type": "string", "description": "Customer name"},
                    "job_description": {"type": "string", "description": "Brief description of the job"},
                    "address": {"type": "string", "description": "Job site address if known"},
                },
                "required": ["client_name", "job_description"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_quote_line_item",
            "description": "Add a line item to the current quote being built. Can be a material from the database or a custom item.",
            "parameters": {
                "type": "object",
                "properties": {
                    "item_name": {"type": "string", "description": "Name of the item (material name or custom description)"},
                    "category": {"type": "string", "enum": ["materials", "labor", "callout", "other"], "description": "Type of line item"},
                    "unit_price": {"type": "number", "description": "Price per unit in AUD"},
                    "quantity": {"type": "number", "description": "Quantity of items"},
                    "unit": {"type": "string", "description": "Unit of measurement (each, metre, hour, etc.)"},
                },
                "required": ["item_name", "category", "unit_price", "quantity"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "remove_quote_line_item",
            "description": "Remove a line item from the current quote by its index (1-based).",
            "parameters": {
                "type": "object",
                "properties": {
                    "item_index": {"type": "integer", "description": "The 1-based index of the item to remove"},
                },
                "required": ["item_index"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "finalise_quote",
            "description": "Finalise the current quote. Call this when the tradie is happy with all line items.",
            "parameters": {
                "type": "object",
                "properties": {
                    "notes": {"type": "string", "description": "Any additional notes for the quote"},
                    "include_gst": {"type": "boolean", "description": "Whether to include GST (default true)"},
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "lookup_price",
            "description": "Look up the price of a plumbing material from the database.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Material name or keyword to search for"},
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_job_status",
            "description": "Update the status of a job",
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
    },
    {
        "type": "function",
        "function": {
            "name": "search_jobs",
            "description": "Search for jobs by client name",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Client name or keyword to search for"},
                },
                "required": ["query"]
            }
        }
    },
]

# Initialize session state
# Jobs / quotes / active_quote are persisted in Supabase (see db.py).
# Only ephemeral UI state lives here.
if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_audio" not in st.session_state:
    st.session_state.last_audio = None
if "greeted" not in st.session_state:
    st.session_state.greeted = False
if "pending_audio" not in st.session_state:
    st.session_state.pending_audio = None
if "audio_played" not in st.session_state:
    st.session_state.audio_played = False
if "should_auto_listen" not in st.session_state:
    st.session_state.should_auto_listen = False


# --- FUNCTION HANDLERS ---
# All handlers persist via db.py (Supabase) instead of session_state.
# Workspace ID is read from session_state on each call.

STATUS_EMOJI = {"Scheduled": "📅", "In Progress": "🔨", "Complete": "✅", "Cancelled": "❌"}


def _job_line(job: dict) -> str:
    emoji = STATUS_EMOJI.get(job["status"], "📅")
    return f"- {emoji} {job['description']} for {job['client_name']} on {job.get('job_date') or 'TBD'} at {job.get('job_time') or 'TBD'} [{job['status']}]"


def handle_create_job(args):
    ws = st.session_state.workspace_id
    job = db.create_job(
        ws,
        client_name=args.get("client_name", "Unknown"),
        description=args.get("description", ""),
        job_date=args.get("date", "TBD"),
        job_time=args.get("time", "TBD"),
        address=args.get("address", "Not specified"),
        priority=args.get("priority", "normal"),
    )
    return f"Job created: {job['description']} for {job['client_name']} on {job['job_date']} at {job['job_time']} (Priority: {job['priority']})"


def handle_list_jobs(args):
    jobs = db.list_jobs(st.session_state.workspace_id)
    if not jobs:
        return "No jobs scheduled yet. Your calendar is clear, mate!"
    lines = []
    for job in jobs:
        urgent = " URGENT" if job["priority"] == "urgent" else ""
        lines.append(_job_line(job) + urgent)
    return "Here are your jobs:\n" + "\n".join(lines)


def handle_add_note(args):
    ws = st.session_state.workspace_id
    client_name = args.get("client_name", "")
    note_text = args.get("note", "")
    job = db.add_note_to_job(ws, client_name, note_text, now_local().strftime("%I:%M %p"))
    if job:
        return f"Note added to {job['client_name']}'s job: {note_text}"
    return f"Couldn't find a job for {client_name}. Try listing your jobs first."


def handle_start_quote(args):
    ws = st.session_state.workspace_id
    quote = db.start_quote(
        ws,
        client_name=args.get("client_name", "Unknown"),
        job_description=args.get("job_description", ""),
        address=args.get("address", ""),
    )
    return f"Quote started for {quote['client_name']} — {quote['job_description']}. I'm ready to add line items. What materials and work are needed?"


def handle_add_quote_line_item(args):
    ws = st.session_state.workspace_id
    active = db.get_active_quote(ws)
    if active is None:
        return "No active quote. Start a quote first with start_quote."
    item = db.add_line_item(
        active["id"],
        item_name=args.get("item_name", "Unknown item"),
        category=args.get("category", "other"),
        unit_price=float(args.get("unit_price", 0)),
        quantity=float(args.get("quantity", 1)),
        unit=args.get("unit", "each"),
    )
    running_total = sum(li["line_total"] for li in db._list_line_items(active["id"]))
    return (
        f"Added: {item['item_name']} — {item['quantity']} x ${item['unit_price']:.2f} = ${item['line_total']:.2f}. "
        f"Running total: ${running_total:.2f} (ex GST). "
        f"What else do we need to add?"
    )


def handle_remove_quote_line_item(args):
    ws = st.session_state.workspace_id
    active = db.get_active_quote(ws)
    if active is None:
        return "No active quote."
    pos = int(args.get("item_index", 0))
    removed = db.remove_line_item_at_position(active["id"], pos)
    if removed is None:
        return "Invalid item number. Check the quote and try again."
    running_total = sum(li["line_total"] for li in db._list_line_items(active["id"]))
    return f"Removed: {removed['item_name']}. Running total now: ${running_total:.2f} (ex GST)."


def handle_finalise_quote(args):
    ws = st.session_state.workspace_id
    active = db.get_active_quote(ws)
    if active is None:
        return "No active quote to finalise."
    quote = db.finalise_quote(
        active["id"],
        notes=args.get("notes", ""),
        include_gst=args.get("include_gst", True),
    )
    materials_count = sum(1 for li in quote["line_items"] if li["category"] == "materials")
    labor_count = sum(1 for li in quote["line_items"] if li["category"] == "labor")
    return (
        f"Quote finalised for {quote['client_name']}! "
        f"{materials_count} material items, {labor_count} labor items. "
        f"Subtotal: ${quote['subtotal']:.2f} + GST ${quote['gst']:.2f} = Total: ${quote['total']:.2f}. "
        f"Quote is ready to send to the customer."
    )


def handle_lookup_price(args):
    query = args.get("query", "")
    results = search_materials(query)
    if not results:
        return f"No materials found matching '{query}'. Try a different search term."
    lines = [f"Found {len(results)} result(s) for '{query}':"]
    for key, item, category in results[:8]:
        lines.append(f"  - {item['name']}: ${item['unit_price']:.2f}/{item['unit']} ({category})")
    return "\n".join(lines)


def handle_update_job_status(args):
    ws = st.session_state.workspace_id
    job = db.update_job_status(
        ws,
        client_name=args.get("client_name", ""),
        status=args.get("status", "Scheduled"),
    )
    if job:
        return f"Job for {job['client_name']} updated to: {job['status']}"
    return f"Couldn't find a job for {args.get('client_name')}."


def handle_daily_summary(args):
    ws = st.session_state.workspace_id
    jobs = db.list_jobs(ws)
    completed = db.list_completed_quotes(ws)
    active = db.get_active_quote(ws)
    total = len(jobs)
    scheduled = sum(1 for j in jobs if j["status"] == "Scheduled")
    in_progress = sum(1 for j in jobs if j["status"] == "In Progress")
    complete = sum(1 for j in jobs if j["status"] == "Complete")
    urgent = sum(1 for j in jobs if j["priority"] == "urgent")
    quote_value = sum(float(q.get("total") or 0) for q in completed)
    summary = "Here's your day at a glance:\n"
    summary += f"- Total jobs: {total}\n"
    summary += f"- Scheduled: {scheduled}\n"
    summary += f"- In progress: {in_progress}\n"
    summary += f"- Complete: {complete}\n"
    if urgent > 0:
        summary += f"- Urgent jobs: {urgent}\n"
    summary += f"- Quotes sent: {len(completed)} (${quote_value:.2f} total value)\n"
    if active:
        summary += f"- Quote in progress for: {active['client_name']}\n"
    return summary


def handle_search_jobs(args):
    ws = st.session_state.workspace_id
    query = args.get("query", "")
    found = db.search_jobs(ws, query)
    if not found:
        return f"No jobs found matching '{query}'."
    return f"Found {len(found)} job(s) matching '{query}':\n" + "\n".join(_job_line(j) for j in found)


FUNCTION_MAP = {
    "create_job": handle_create_job,
    "list_jobs": handle_list_jobs,
    "add_note": handle_add_note,
    "start_quote": handle_start_quote,
    "add_quote_line_item": handle_add_quote_line_item,
    "remove_quote_line_item": handle_remove_quote_line_item,
    "finalise_quote": handle_finalise_quote,
    "lookup_price": handle_lookup_price,
    "update_job_status": handle_update_job_status,
    "daily_summary": handle_daily_summary,
    "search_jobs": handle_search_jobs,
}


MAX_TOOL_ROUNDS = 5


def process_ai_response(messages):
    """Process AI response, handling multiple rounds of tool calls.

    Logs one telemetry row per turn to tool_call_events so we can measure
    rounds-used, hit-cap rate, and latency over time.
    """
    import time
    turn_id = str(uuid.uuid4())
    t0 = time.perf_counter()
    tools_called: list[str] = []
    rounds = 0
    prompt_tokens_sum = 0
    completion_tokens_sum = 0
    error: str | None = None
    final_text = ""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=TOOLS,
        )
        if response.usage:
            prompt_tokens_sum += response.usage.prompt_tokens
            completion_tokens_sum += response.usage.completion_tokens
        message = response.choices[0].message

        while message.tool_calls and rounds < MAX_TOOL_ROUNDS:
            rounds += 1
            messages.append({
                "role": "assistant",
                "content": message.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        }
                    }
                    for tc in message.tool_calls
                ]
            })
            for tool_call in message.tool_calls:
                func_name = tool_call.function.name
                tools_called.append(func_name)
                func_args = json.loads(tool_call.function.arguments)
                if func_name in FUNCTION_MAP:
                    result = FUNCTION_MAP[func_name](func_args)
                else:
                    result = f"Unknown function: {func_name}"
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": str(result)
                })

            response = client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                tools=TOOLS,
            )
            if response.usage:
                prompt_tokens_sum += response.usage.prompt_tokens
                completion_tokens_sum += response.usage.completion_tokens
            message = response.choices[0].message

        final_text = message.content or "Done, mate! Anything else?"
        # Hit the cap if we still have pending tool calls after MAX_TOOL_ROUNDS
        hit_cap = bool(message.tool_calls) and rounds >= MAX_TOOL_ROUNDS
    except Exception as e:
        error = str(e)
        final_text = f"Sorry mate, hit a snag: {error}"
        hit_cap = False

    # Telemetry — fire-and-forget; never let logging break the user flow
    try:
        db.log_tool_call_event(
            workspace_id=st.session_state.get("workspace_id"),
            turn_id=turn_id,
            rounds_used=rounds,
            hit_cap=hit_cap,
            tools_called=tools_called,
            total_latency_ms=int((time.perf_counter() - t0) * 1000),
            prompt_tokens=prompt_tokens_sum or None,
            completion_tokens=completion_tokens_sum or None,
            error=error,
        )
    except Exception:
        pass

    return final_text


def render_quote_card(quote, mode="completed"):
    """
    Render a self-contained quote card with inline styles (works in st.html iframe).
    mode:
      - "active": amber border + glow, for the quote currently being built
      - "completed": neutral border, for finalised quotes in the sidebar list
    """
    is_active = mode == "active"
    line_items_html = ""

    # Group items by category
    materials = [li for li in quote.get("line_items", []) if li["category"] == "materials"]
    labor = [li for li in quote.get("line_items", []) if li["category"] == "labor"]
    callout = [li for li in quote.get("line_items", []) if li["category"] == "callout"]
    other = [li for li in quote.get("line_items", []) if li["category"] == "other"]

    def render_items(items, section_label):
        html = ""
        if items:
            html += f'<div style="font-size:11px;text-transform:uppercase;letter-spacing:1.5px;color:#64748b;margin-top:14px;margin-bottom:6px;font-weight:600;">{section_label}</div>'
            for item in items:
                html += f'''<div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.06);font-size:13px;color:#e2e8f0;">
                    <div>
                        <div>{item["item_name"]}</div>
                        <div style="color:#94a3b8;font-size:12px;">{item["quantity"]} x ${item["unit_price"]:.2f}/{item.get("unit", "each")}</div>
                    </div>
                    <div style="font-weight:600;color:#60a5fa;">${item["line_total"]:.2f}</div>
                </div>'''
        return html

    line_items_html += render_items(materials, "Materials")
    line_items_html += render_items(labor, "Labour")
    line_items_html += render_items(callout, "Callout")
    line_items_html += render_items(other, "Other")

    subtotal = sum(li["line_total"] for li in quote.get("line_items", []))
    gst = quote.get("gst", subtotal * 0.1)
    total = quote.get("total", subtotal + gst)

    status_label = quote.get("status", "draft").upper()
    border_color = "#f59e0b" if is_active else "#3d4f7c"
    glow = "box-shadow: 0 0 20px rgba(245, 158, 11, 0.15);" if is_active else ""

    # Status badge colors
    status = quote.get("status", "draft")
    if status == "sent":
        badge_style = "background:#172554;color:#60a5fa;border:1px solid #1e40af;"
    elif status == "accepted":
        badge_style = "background:#052e16;color:#34d399;border:1px solid #166534;"
    else:
        badge_style = "background:#1e293b;color:#94a3b8;border:1px solid #334155;"

    no_items_msg = ""
    if not quote.get("line_items"):
        no_items_msg = '<div style="text-align:center;color:#475569;padding:16px 0;font-size:13px;">No items yet — keep talking to add materials and labour</div>'

    card_html = f'''
    <div style="background:linear-gradient(135deg,#1a1f2e 0%,#232b3e 100%);border:1px solid {border_color};border-radius:16px;padding:20px;margin:10px 0;{glow}font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
        <div style="display:flex;justify-content:space-between;align-items:center;">
            <div style="font-size:18px;font-weight:700;color:#60a5fa;margin-bottom:4px;">Quote #{quote.get("id", "—")}</div>
            <span style="display:inline-block;padding:2px 10px;border-radius:12px;font-size:12px;font-weight:600;{badge_style}">{status_label}</span>
        </div>
        <div style="font-size:14px;color:#94a3b8;margin-bottom:12px;">{quote.get("client_name", "")} — {quote.get("job_description", quote.get("description", ""))}</div>
        {f'<div style="font-size:12px;color:#64748b;margin-bottom:8px;">📍 {quote["address"]}</div>' if quote.get("address") else ""}
        {no_items_msg}
        {line_items_html}
        <div style="display:flex;justify-content:space-between;padding:14px 0 4px 0;border-top:2px solid #3d4f7c;margin-top:10px;font-size:16px;font-weight:700;">
            <span style="color:#e2e8f0;">Subtotal</span>
            <span style="font-weight:600;color:#60a5fa;">${subtotal:.2f}</span>
        </div>
        <div style="display:flex;justify-content:space-between;padding:4px 0;font-size:13px;color:#94a3b8;">
            <span>GST (10%)</span>
            <span>${gst:.2f}</span>
        </div>
        <div style="display:flex;justify-content:space-between;padding:10px 0 4px 0;border-top:2px solid #3d4f7c;margin-top:6px;font-size:18px;font-weight:700;">
            <span style="color:#e2e8f0;">TOTAL (inc GST)</span>
            <span style="color:#34d399;font-size:22px;">${total:.2f}</span>
        </div>
        <div style="text-align:center;font-size:11px;color:#475569;margin-top:16px;padding-top:12px;border-top:1px solid rgba(255,255,255,0.06);">
            Generated by SiteVoice • {quote.get("created_at", now_local().strftime("%Y-%m-%d %H:%M"))}
        </div>
    </div>
    '''
    return card_html


# --- SIDEBAR (rendered at bottom of script for fresh DB state after chat handler runs) ---


# --- MAIN CHAT AREA ---

# Welcome message on first load
if not st.session_state.greeted:
    welcome = f"{get_greeting()}, mate! I'm SiteVoice — your hands-free assistant for the job site. Tell me to schedule jobs, build quotes with real pricing, or just ask what's on for the day. Let's get to work!"
    st.session_state.messages.append({"role": "assistant", "content": welcome})
    st.session_state.greeted = True

# Sticky header with title + quick actions
quick_prompt = None
header_container = st.container()
with header_container:
    st.markdown("""
    <div style="display: flex; align-items: center; gap: 20px; margin-bottom: 10px; padding: 14px 0;">
        <div style="width: 72px; height: 72px; background: linear-gradient(135deg, #1e40af, #059669); border-radius: 18px; display: flex; align-items: center; justify-content: center; font-size: 36px; box-shadow: 0 6px 16px rgba(96, 165, 250, 0.25); flex-shrink: 0;">🔧</div>
        <div>
            <h1 style="margin: 0; padding: 0; font-size: 48px; font-weight: 900; background: linear-gradient(135deg, #60a5fa 0%, #34d399 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; letter-spacing: -1px; line-height: 1.1;">SiteVoice</h1>
            <p style="margin: 4px 0 0 0; color: #94a3b8; font-size: 16px; letter-spacing: 0.5px;">Voice-powered AI assistant for plumbers</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("👋 First time? Tap to see how to test the demo", expanded=False):
        st.markdown(
            """
            <div style="font-size:14px;color:#cbd5e1;line-height:1.6;">
            <b>Two ways to talk to the agent:</b><br>
            • Click any blue example button below — it auto-submits a realistic prompt<br>
            • Tap the 🎤 mic to speak, or type into the chat at the bottom<br><br>
            <b>What to watch:</b><br>
            • Sidebar updates live as jobs and quotes are created<br>
            • The active quote card shows running line items and total<br>
            • Sidebar bottom — open <i>Dev — Tool-call telemetry</i> to see GPT-4o measurements<br><br>
            <b>Persistence:</b><br>
            • Refresh — your data stays (URL has your unique workspace ID)<br>
            • Open this site in a new tab without <code>?ws=</code> for a fresh empty workspace<br>
            • Share your <code>?ws=...</code> URL with someone to share the workspace
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.caption("Try one of these to see the agent in action:")
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        if st.button("📅 Schedule a job", use_container_width=True):
            quick_prompt = "Schedule an electric hot water replacement for Karen Smith at 12 Bell Street tomorrow at 9am, urgent priority"
    with col2:
        if st.button("💰 Build a quote", use_container_width=True):
            quick_prompt = "Build a quote for Karen Smith at 12 Bell Street: Rheem 250L electric HWS, tempering valve, 4 hours of standard labour. Then lock it in."
    with col3:
        if st.button("📋 List jobs", use_container_width=True):
            quick_prompt = "What jobs do I have?"
    with col4:
        if st.button("🔧 Check a price", use_container_width=True):
            quick_prompt = "What does a basin mixer cost?"
    with col5:
        if st.button("🗑️ Clear chat", use_container_width=True):
            greeting = f"{get_greeting()}, mate! Chat cleared. What can I help with?"
            st.session_state.messages = [{"role": "assistant", "content": greeting}]
            st.session_state.last_audio = None
            st.session_state.pending_audio = None
            st.session_state.audio_played = False
            st.rerun()

st.markdown("---")

# Chat area
chat_container = st.container()
with chat_container:
    for message in st.session_state.messages:
        if isinstance(message, dict) and message.get("role") in ["user", "assistant"]:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

# Voice recording
st.markdown("""
<div style="display:flex;align-items:center;gap:8px;margin:8px 0 4px 0;">
    <span style="font-size:20px;">🎤</span>
    <span style="font-size:16px;font-weight:600;color:#e2e8f0;">Tap to speak</span>
    <span style="font-size:12px;color:#64748b;">or type below</span>
</div>
""", unsafe_allow_html=True)
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

# Handle input
prompt = voice_text or quick_prompt or st.chat_input("Or type your message here...")

if prompt:
    if voice_text:
        st.info(f'🎤 Heard: "{voice_text}"')

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Build API messages — include active quote context
    api_messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Inject active quote context so AI knows what's been added
    active_q = db.get_active_quote(st.session_state.workspace_id)
    if active_q:
        items_summary = ""
        for idx, li in enumerate(active_q["line_items"], 1):
            items_summary += f"  {idx}. {li['item_name']} — {li['quantity']} x ${li['unit_price']:.2f} = ${li['line_total']:.2f} ({li['category']})\n"
        running_total = sum(li["line_total"] for li in active_q["line_items"])
        quote_context = (
            f"\n[ACTIVE QUOTE CONTEXT]\n"
            f"Currently building quote for: {active_q['client_name']}\n"
            f"Job: {active_q['job_description']}\n"
            f"Current line items:\n{items_summary if items_summary else '  (none yet)'}\n"
            f"Running total: ${running_total:.2f} (ex GST)\n"
            f"[END QUOTE CONTEXT]"
        )
        api_messages.append({"role": "system", "content": quote_context})

    for msg in st.session_state.messages:
        if isinstance(msg, dict) and msg.get("role") in ["user", "assistant"]:
            api_messages.append(msg)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            reply = process_ai_response(api_messages)
        st.markdown(reply)

    st.session_state.messages.append({"role": "assistant", "content": reply})

    # Auto-scroll to bottom so user always sees latest message.
    # Streamlit renamed the main container across versions, so try several selectors.
    components.html("""
    <script>
        (function() {
            var doc = window.parent.document;
            var main = doc.querySelector('section.main')
                    || doc.querySelector('section[data-testid="stMain"]')
                    || doc.querySelector('[data-testid="stAppViewContainer"]')
                    || doc.querySelector('main');
            if (!main) return;
            main.scrollTo({ top: main.scrollHeight, behavior: 'smooth' });
        })();
    </script>
    """, height=0)

    # Detect if the AI is asking a question (for auto-listen)
    reply_lower = reply.lower().strip()
    is_question = reply_lower.endswith("?") or any(
        phrase in reply_lower for phrase in [
            "what else", "anything else", "need anything", "what do you",
            "shall i", "want me to", "how does that", "sound good",
            "let me know", "what's the", "which one"
        ]
    )

    st.session_state.should_auto_listen = is_question

    # Generate TTS and store in session state (played below, outside this block)
    with st.spinner("Generating voice..."):
        speech_response = client.audio.speech.create(
            model="tts-1",
            voice="onyx",
            input=reply,
            speed=1.2
        )
        st.session_state.pending_audio = speech_response.content
        st.session_state.audio_played = False

# --- AUDIO PLAYBACK & AUTO-LISTEN ---
if st.session_state.pending_audio and not st.session_state.audio_played:
    audio_b64 = base64.b64encode(st.session_state.pending_audio).decode()
    should_listen = st.session_state.get("should_auto_listen", False)

    end_status_text = "🎤 Your turn"
    end_color = "#34d399"
    if should_listen:
        # Auto-click: search broadly for any mic/record button in the parent doc
        auto_listen_block = """
                setTimeout(function() {
                    try {
                        var doc = window.parent.document;
                        var allBtns = doc.querySelectorAll('button');
                        for (var i = 0; i < allBtns.length; i++) {
                            var b = allBtns[i];
                            var label = (b.getAttribute('aria-label') || '').toLowerCase();
                            var testid = (b.getAttribute('data-testid') || '').toLowerCase();
                            var title = (b.getAttribute('title') || '').toLowerCase();
                            if (label.indexOf('record') !== -1 ||
                                testid.indexOf('record') !== -1 ||
                                testid.indexOf('audio') !== -1 ||
                                title.indexOf('record') !== -1) {
                                b.click();
                                break;
                            }
                        }
                    } catch(e) {}
                }, 800);
        """
    else:
        auto_listen_block = ""

    components.html(f"""
    <audio id="sv-audio" preload="auto" style="width:100%;display:none;">
        <source src="data:audio/mp3;base64,{audio_b64}" type="audio/mp3">
    </audio>
    <div id="sv-status" style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;font-size:13px;color:#60a5fa;padding:8px 0;">
        🔊 Speaking...
    </div>
    <script>
        (function() {{
            var audio = document.getElementById('sv-audio');
            var status = document.getElementById('sv-status');
            if (!audio) return;

            var resolved = false;
            function endTurn() {{
                if (resolved) return;
                resolved = true;
                status.textContent = '{end_status_text}';
                status.style.color = '{end_color}';
                {auto_listen_block}
            }}

            audio.addEventListener('ended', endTurn);

            audio.addEventListener('error', function() {{
                if (resolved) return;
                resolved = true;
                status.textContent = '⚠️ Audio error — type your message instead';
                status.style.color = '#f59e0b';
            }});

            // Try to play explicitly. If browser blocks autoplay, surface controls.
            var playPromise = audio.play();
            if (playPromise !== undefined) {{
                playPromise.catch(function() {{
                    audio.controls = true;
                    audio.style.display = 'block';
                    status.textContent = '🔇 Tap play to hear reply';
                    status.style.color = '#f59e0b';
                    audio.addEventListener('play', function() {{
                        status.textContent = '🔊 Speaking...';
                        status.style.color = '#60a5fa';
                    }}, {{ once: true }});
                }});
            }}

            // Safety: never let the indicator hang. End the turn after 30s no matter what.
            setTimeout(endTurn, 30000);
        }})();
    </script>
    """, height=80)

    st.session_state.audio_played = True
    st.session_state.pending_audio = None


# --- SIDEBAR (placed last so it sees DB writes from this rerun's chat handler) ---
with st.sidebar:
    ws_id = st.session_state.workspace_id
    sidebar_jobs = db.list_jobs(ws_id)
    sidebar_active_quote = db.get_active_quote(ws_id)
    sidebar_completed_quotes = db.list_completed_quotes(ws_id)

    if sidebar_active_quote:
        st.markdown("## 🔨 Building Quote...")
        try:
            st.html(render_quote_card(sidebar_active_quote, mode="active"))
        except AttributeError:
            st.markdown(render_quote_card(sidebar_active_quote, mode="active"), unsafe_allow_html=True)
        items_count = len(sidebar_active_quote["line_items"])
        running_total = sum(li["line_total"] for li in sidebar_active_quote["line_items"])
        st.caption(f"{items_count} items • ${running_total:.2f} ex GST • Keep talking to add more")
        st.markdown("---")

    st.markdown("## 📋 Job Board")
    if sidebar_jobs:
        for job in sidebar_jobs:
            status_emoji = STATUS_EMOJI.get(job["status"], "📅")
            priority_color = "🔴" if job["priority"] == "urgent" else "🟡" if job["priority"] == "normal" else "🟢"

            with st.expander(f"{status_emoji} {job['client_name']} — {job.get('job_date') or 'TBD'}"):
                st.write(f"**Job:** {job['description']}")
                st.write(f"**Time:** {job.get('job_time') or 'TBD'}")
                st.write(f"**Address:** {job.get('address') or 'Not specified'}")
                st.write(f"**Priority:** {priority_color} {job['priority'].title()}")
                st.write(f"**Status:** {job['status']}")
                if job.get("notes"):
                    st.write("**Notes:**")
                    for note in job["notes"]:
                        if isinstance(note, dict):
                            st.write(f"  - [{note['time']}] {note['text']}")
                        else:
                            st.write(f"  - {note}")

                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    if job["status"] != "Complete":
                        if st.button("Done", key=f"done_{job['id']}", use_container_width=True):
                            db.set_job_status_by_id(job["id"], "Complete")
                            st.rerun()
                with col_b:
                    if job["status"] == "Scheduled":
                        if st.button("Start", key=f"start_{job['id']}", use_container_width=True):
                            db.set_job_status_by_id(job["id"], "In Progress")
                            st.rerun()
                with col_c:
                    if st.button("Del", key=f"del_{job['id']}", use_container_width=True):
                        db.delete_job(job["id"])
                        st.rerun()
    else:
        st.info("No jobs yet — tell SiteVoice to schedule one!")

    st.markdown("---")
    st.markdown("## 💰 Completed Quotes")

    if sidebar_completed_quotes:
        for quote in sidebar_completed_quotes:
            total = float(quote.get("total") or 0)
            with st.expander(f"#{quote['id']} {quote['client_name']} — ${total:,.2f}"):
                try:
                    st.html(render_quote_card(quote, mode="completed"))
                except AttributeError:
                    st.markdown(render_quote_card(quote, mode="completed"), unsafe_allow_html=True)
                if st.button("🗑️ Delete Quote", key=f"del_q_{quote['id']}", use_container_width=True):
                    db.delete_quote(quote["id"])
                    st.rerun()
    else:
        st.info("No quotes yet — ask SiteVoice to create one!")

    st.markdown("---")
    st.markdown("## 📊 Dashboard")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Jobs", len(sidebar_jobs))
    with col2:
        st.metric("Quotes", len(sidebar_completed_quotes))

    if sidebar_completed_quotes:
        total_value = sum(float(q.get("total") or 0) for q in sidebar_completed_quotes)
        st.metric("Revenue Pipeline", f"${total_value:,.2f}")

    complete_jobs = sum(1 for j in sidebar_jobs if j["status"] == "Complete")
    if sidebar_jobs:
        completion_rate = int((complete_jobs / len(sidebar_jobs)) * 100)
        if completion_rate < 33:
            bar_color = "#ef4444"
        elif completion_rate < 66:
            bar_color = "#f59e0b"
        else:
            bar_color = "#22c55e"
        st.markdown(f"**Completion: {completion_rate}%**")
        st.markdown(
            f"""<div style="background-color: #1e293b; border-radius: 10px; height: 16px; width: 100%;">
                <div style="background: linear-gradient(90deg, {bar_color}, {bar_color}dd); width: {max(completion_rate, 2)}%; height: 16px; border-radius: 10px; transition: width 0.5s ease;"></div>
            </div>""",
            unsafe_allow_html=True
        )

    st.markdown("---")
    with st.expander("🔬 Dev — Tool-call telemetry", expanded=False):
        scope = st.radio(
            "Scope",
            ["This workspace", "All workspaces"],
            horizontal=True,
            label_visibility="collapsed",
        )
        try:
            stats = db.telemetry_stats(ws_id if scope == "This workspace" else None)
        except Exception as e:
            st.caption(f"Telemetry unavailable: {e}")
            stats = {"total_turns": 0}

        if stats.get("total_turns", 0) == 0:
            st.caption("No turns logged yet — chat with SiteVoice to populate.")
        else:
            mc1, mc2 = st.columns(2)
            with mc1:
                st.metric("Turns", stats["total_turns"])
                st.metric("Avg rounds", stats["avg_rounds"])
            with mc2:
                st.metric("Hit-cap rate", f"{stats['hit_cap_rate']}%")
                if stats.get("p50_latency_ms") is not None:
                    st.metric("p50 latency", f"{stats['p50_latency_ms']} ms")
            if stats.get("p95_latency_ms") is not None:
                st.caption(f"p95 latency: {stats['p95_latency_ms']} ms")
            if stats.get("top_tools"):
                st.caption("**Top tools:**")
                for name, count in stats["top_tools"]:
                    st.caption(f"  - {name}: {count}")
        st.caption(f"Cap: {MAX_TOOL_ROUNDS} rounds per turn")
