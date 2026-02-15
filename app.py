import streamlit as st
import streamlit.components.v1 as components
from openai import OpenAI
from dotenv import load_dotenv
import os
import tempfile
import json
import base64
from datetime import datetime
from plumbing_data import (
    PLUMBING_MATERIALS, LABOR_RATES, JOB_TEMPLATES,
    lookup_material, search_materials, get_job_template,
    get_all_categories, get_labor_rates_text
)

# Load API key
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Page config
st.set_page_config(
    page_title="SiteVoice",
    page_icon="🔧",
    layout="wide"
)

# --- CUSTOM CSS ---
st.markdown("""
<style>
    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
    }

    /* Hide default streamlit elements for cleaner look */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Chat input at bottom */
    .stChatInput {
        position: sticky;
        bottom: 0;
        z-index: 998;
        background: #0e1117;
    }
</style>
""", unsafe_allow_html=True)


# --- TIME-AWARE GREETING ---
def get_greeting():
    hour = datetime.now().hour
    if hour < 12:
        return "Good morning"
    elif hour < 17:
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

Current date and time: {datetime.now().strftime("%A, %d %B %Y, %I:%M %p")}

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
7. When they're happy, call finalise_quote to lock it in
8. Keep the conversation natural — you're building the quote WITH them, not interrogating them

For example, if a plumber says "I need a quote for Karen, hot water replacement":
- Start the quote, ask what model/brand they're looking at
- Add the HWS unit as a line item
- Ask about pipework condition, valves needed
- Add those as line items
- Add labor based on estimated hours
- Suggest the callout fee
- Total it up and confirm

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
if "messages" not in st.session_state:
    st.session_state.messages = []
if "jobs" not in st.session_state:
    st.session_state.jobs = []
if "quotes" not in st.session_state:
    st.session_state.quotes = []
if "active_quote" not in st.session_state:
    st.session_state.active_quote = None
if "last_audio" not in st.session_state:
    st.session_state.last_audio = None
if "greeted" not in st.session_state:
    st.session_state.greeted = False
if "pending_audio" not in st.session_state:
    st.session_state.pending_audio = None
if "audio_played" not in st.session_state:
    st.session_state.audio_played = False


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
        priority_flag = " URGENT" if job["priority"] == "urgent" else ""
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


def handle_start_quote(args):
    quote = {
        "id": len(st.session_state.quotes) + 1,
        "client_name": args.get("client_name", "Unknown"),
        "job_description": args.get("job_description", ""),
        "address": args.get("address", ""),
        "line_items": [],
        "status": "draft",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "finalised_at": None,
        "notes": "",
        "include_gst": True,
    }
    st.session_state.active_quote = quote
    return f"Quote started for {quote['client_name']} — {quote['job_description']}. I'm ready to add line items. What materials and work are needed?"


def handle_add_quote_line_item(args):
    if st.session_state.active_quote is None:
        return "No active quote. Start a quote first with start_quote."

    item = {
        "item_name": args.get("item_name", "Unknown item"),
        "category": args.get("category", "other"),
        "unit_price": args.get("unit_price", 0),
        "quantity": args.get("quantity", 1),
        "unit": args.get("unit", "each"),
        "line_total": args.get("unit_price", 0) * args.get("quantity", 1),
    }
    st.session_state.active_quote["line_items"].append(item)

    # Calculate running total
    running_total = sum(li["line_total"] for li in st.session_state.active_quote["line_items"])

    return (
        f"Added: {item['item_name']} — {item['quantity']} x ${item['unit_price']:.2f} = ${item['line_total']:.2f}. "
        f"Running total: ${running_total:.2f} (ex GST). "
        f"What else do we need to add?"
    )


def handle_remove_quote_line_item(args):
    if st.session_state.active_quote is None:
        return "No active quote."

    idx = args.get("item_index", 0) - 1  # Convert to 0-based
    items = st.session_state.active_quote["line_items"]
    if 0 <= idx < len(items):
        removed = items.pop(idx)
        running_total = sum(li["line_total"] for li in items)
        return f"Removed: {removed['item_name']}. Running total now: ${running_total:.2f} (ex GST)."
    return "Invalid item number. Check the quote and try again."


def handle_finalise_quote(args):
    if st.session_state.active_quote is None:
        return "No active quote to finalise."

    quote = st.session_state.active_quote
    quote["notes"] = args.get("notes", "")
    quote["include_gst"] = args.get("include_gst", True)
    quote["status"] = "sent"
    quote["finalised_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")

    subtotal = sum(li["line_total"] for li in quote["line_items"])
    gst = subtotal * 0.1 if quote["include_gst"] else 0
    total = subtotal + gst
    quote["subtotal"] = subtotal
    quote["gst"] = gst
    quote["total"] = total

    st.session_state.quotes.append(quote)
    st.session_state.active_quote = None

    materials_count = len([li for li in quote["line_items"] if li["category"] == "materials"])
    labor_items = [li for li in quote["line_items"] if li["category"] == "labor"]

    return (
        f"Quote finalised for {quote['client_name']}! "
        f"{materials_count} material items, {len(labor_items)} labor items. "
        f"Subtotal: ${subtotal:.2f} + GST ${gst:.2f} = Total: ${total:.2f}. "
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
    quote_value = sum(q.get("total", q.get("amount", 0)) for q in st.session_state.quotes)
    summary = f"Here's your day at a glance:\n"
    summary += f"- Total jobs: {total}\n"
    summary += f"- Scheduled: {scheduled}\n"
    summary += f"- In progress: {in_progress}\n"
    summary += f"- Complete: {complete}\n"
    if urgent > 0:
        summary += f"- Urgent jobs: {urgent}\n"
    summary += f"- Quotes sent: {total_quotes} (${quote_value:.2f} total value)\n"
    if st.session_state.active_quote:
        summary += f"- Quote in progress for: {st.session_state.active_quote['client_name']}\n"
    return summary


def handle_search_jobs(args):
    query = args.get("query", "").lower()
    found = [j for j in st.session_state.jobs if query in j["client_name"].lower() or query in j["description"].lower()]
    if not found:
        return f"No jobs found matching '{query}'."
    results = []
    for job in found:
        status_emoji = {"Scheduled": "📅", "In Progress": "🔨", "Complete": "✅", "Cancelled": "❌"}.get(job["status"], "📅")
        results.append(f"- {status_emoji} {job['description']} for {job['client_name']} on {job['date']} at {job['time']} [{job['status']}]")
    return f"Found {len(found)} job(s) matching '{query}':\n" + "\n".join(results)


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


def process_ai_response(messages):
    """Process AI response, handling multiple rounds of tool calls."""
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        tools=TOOLS,
    )
    message = response.choices[0].message

    # Handle tool calls (may need multiple rounds)
    max_rounds = 5
    rounds = 0
    while message.tool_calls and rounds < max_rounds:
        rounds += 1
        messages.append(message)
        for tool_call in message.tool_calls:
            func_name = tool_call.function.name
            func_args = json.loads(tool_call.function.arguments)
            if func_name in FUNCTION_MAP:
                result = FUNCTION_MAP[func_name](func_args)
            else:
                result = f"Unknown function: {func_name}"
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result
            })

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=TOOLS,
        )
        message = response.choices[0].message

    return message.content


def render_quote_card_html(quote, is_active=False):
    """Render a self-contained quote card with all styles inline (works in st.html iframe)."""
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
            Generated by SiteVoice • {quote.get("created_at", datetime.now().strftime("%Y-%m-%d %H:%M"))}
        </div>
    </div>
    '''
    return card_html


# --- SIDEBAR ---
with st.sidebar:
    # Active quote card (top of sidebar for visibility)
    if st.session_state.active_quote:
        st.markdown("## 🔨 Building Quote...")
        # st.html renders raw HTML properly in its own iframe (Streamlit 1.33+)
        try:
            st.html(render_quote_card_html(st.session_state.active_quote, is_active=True))
        except AttributeError:
            st.markdown(render_quote_card_html(st.session_state.active_quote, is_active=True), unsafe_allow_html=True)
        items_count = len(st.session_state.active_quote["line_items"])
        running_total = sum(li["line_total"] for li in st.session_state.active_quote["line_items"])
        st.caption(f"{items_count} items • ${running_total:.2f} ex GST • Keep talking to add more")
        st.markdown("---")

    st.markdown("## 📋 Job Board")
    if st.session_state.jobs:
        for i, job in enumerate(st.session_state.jobs):
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
                            st.write(f"  - [{note['time']}] {note['text']}")
                        else:
                            st.write(f"  - {note}")

                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    if job["status"] != "Complete":
                        if st.button("Done", key=f"done_{i}", use_container_width=True):
                            st.session_state.jobs[i]["status"] = "Complete"
                            st.rerun()
                with col_b:
                    if job["status"] == "Scheduled":
                        if st.button("Start", key=f"start_{i}", use_container_width=True):
                            st.session_state.jobs[i]["status"] = "In Progress"
                            st.rerun()
                with col_c:
                    if st.button("Del", key=f"del_{i}", use_container_width=True):
                        st.session_state.jobs.pop(i)
                        st.rerun()
    else:
        st.info("No jobs yet — tell SiteVoice to schedule one!")

    st.markdown("---")
    st.markdown("## 💰 Completed Quotes")

    if st.session_state.quotes:
        for i, quote in enumerate(st.session_state.quotes):
            total = quote.get("total", quote.get("amount", 0))
            with st.expander(f"#{quote.get('id', i+1)} {quote['client_name']} — ${total:,.2f}"):
                # Job description
                job_desc = quote.get("job_description", quote.get("description", ""))
                addr_line = f"  \n📍 {quote['address']}" if quote.get("address") else ""
                st.markdown(f"*{job_desc}*{addr_line}")

                # Group line items
                materials = [li for li in quote.get("line_items", []) if li["category"] == "materials"]
                labor = [li for li in quote.get("line_items", []) if li["category"] == "labor"]
                callout = [li for li in quote.get("line_items", []) if li["category"] == "callout"]
                other = [li for li in quote.get("line_items", []) if li["category"] == "other"]

                for section_name, items in [("Materials", materials), ("Labour", labor), ("Callout", callout), ("Other", other)]:
                    if items:
                        st.markdown(f"**{section_name}**")
                        for item in items:
                            col_l, col_r = st.columns([3, 1])
                            with col_l:
                                st.markdown(f"{item['item_name']}  \n`{item['quantity']} x ${item['unit_price']:.2f}`")
                            with col_r:
                                st.markdown(f"**${item['line_total']:.2f}**")

                subtotal = quote.get("subtotal", sum(li["line_total"] for li in quote.get("line_items", [])))
                gst = quote.get("gst", subtotal * 0.1)
                st.divider()
                col_l, col_r = st.columns([3, 1])
                with col_l:
                    st.markdown("Subtotal")
                with col_r:
                    st.markdown(f"**${subtotal:.2f}**")
                col_l, col_r = st.columns([3, 1])
                with col_l:
                    st.markdown("GST (10%)")
                with col_r:
                    st.markdown(f"${gst:.2f}")
                st.divider()
                col_l, col_r = st.columns([3, 1])
                with col_l:
                    st.markdown("**TOTAL**")
                with col_r:
                    st.markdown(f"### ${total:,.2f}")

                st.caption(f"Generated {quote.get('created_at', '')}")
                if st.button("Delete", key=f"del_q_{i}", use_container_width=True):
                    st.session_state.quotes.pop(i)
                    st.rerun()
    else:
        st.info("No quotes yet — ask SiteVoice to create one!")

    # Quick stats
    st.markdown("---")
    st.markdown("## 📊 Dashboard")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Jobs", len(st.session_state.jobs))
    with col2:
        st.metric("Quotes", len(st.session_state.quotes))

    if st.session_state.quotes:
        total_value = sum(q.get("total", q.get("amount", 0)) for q in st.session_state.quotes)
        st.metric("Revenue Pipeline", f"${total_value:,.2f}")

    complete_jobs = len([j for j in st.session_state.jobs if j["status"] == "Complete"])
    if st.session_state.jobs:
        completion_rate = int((complete_jobs / len(st.session_state.jobs)) * 100)
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
    <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 4px;">
        <span style="font-size: 36px;">🔧</span>
        <div>
            <h1 style="margin: 0; padding: 0; font-size: 30px; font-weight: 800; background: linear-gradient(135deg, #60a5fa, #34d399); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">SiteVoice</h1>
            <p style="margin: 0; color: #94a3b8; font-size: 13px;">Voice-powered AI assistant for plumbers</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
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
            quick_prompt = "I need to create a quote for a customer"

st.markdown("---")

# Chat area
chat_container = st.container()
with chat_container:
    for message in st.session_state.messages:
        if isinstance(message, dict) and message.get("role") in ["user", "assistant"]:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

# Voice recording
st.markdown("#### 🎤 Tap to speak")
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
    if st.session_state.active_quote:
        q = st.session_state.active_quote
        items_summary = ""
        for idx, li in enumerate(q["line_items"], 1):
            items_summary += f"  {idx}. {li['item_name']} — {li['quantity']} x ${li['unit_price']:.2f} = ${li['line_total']:.2f} ({li['category']})\n"
        running_total = sum(li["line_total"] for li in q["line_items"])
        quote_context = (
            f"\n[ACTIVE QUOTE CONTEXT]\n"
            f"Currently building quote for: {q['client_name']}\n"
            f"Job: {q['job_description']}\n"
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

    # Generate TTS and store in session state (played below, outside this block)
    with st.spinner("Generating voice..."):
        speech_response = client.audio.speech.create(
            model="tts-1",
            voice="onyx",
            input=reply
        )
        st.session_state.pending_audio = speech_response.content
        st.session_state.audio_played = False

# --- AUDIO PLAYBACK & AUTO-LISTEN ---
# Two-phase approach: render audio on first pass, clear on second pass so input unblocks
if st.session_state.pending_audio and not st.session_state.audio_played:
    # Render audio in a components iframe (allows JS execution)
    audio_b64 = base64.b64encode(st.session_state.pending_audio).decode()

    # Custom HTML audio with JS: auto-play, and when finished auto-click the mic button
    components.html(f"""
    <audio id="sitevoice-tts" autoplay style="display:none;">
        <source src="data:audio/mp3;base64,{audio_b64}" type="audio/mp3">
    </audio>
    <div id="status" style="font-family:sans-serif;font-size:13px;color:#60a5fa;padding:8px 0;">
        🔊 Speaking...
    </div>
    <script>
        const audio = document.getElementById('sitevoice-tts');
        const status = document.getElementById('status');
        if (audio) {{
            audio.addEventListener('ended', function() {{
                status.textContent = '🎤 Your turn — listening...';
                status.style.color = '#34d399';
                // Try to auto-click the mic record button in the parent Streamlit frame
                setTimeout(function() {{
                    try {{
                        const buttons = window.parent.document.querySelectorAll('button[data-testid="stAudioInputRecordButton"]');
                        if (buttons.length > 0) {{
                            buttons[0].click();
                        }}
                    }} catch(e) {{
                        // Cross-origin may block this, that's ok
                    }}
                }}, 600);
            }});
            audio.addEventListener('error', function() {{
                status.textContent = '⚠️ Audio error — type your message instead';
                status.style.color = '#f59e0b';
            }});
        }}
    </script>
    """, height=40)

    st.session_state.audio_played = True
    st.session_state.pending_audio = None
