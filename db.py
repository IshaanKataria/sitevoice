"""
Thin Supabase wrappers for SiteVoice persistence.
Tenant isolation via workspace_id (UUID from ?ws= URL param).
"""
import os
from typing import Optional
from supabase import Client, create_client
from dotenv import load_dotenv

load_dotenv()

_client: Optional[Client] = None


def client() -> Client:
    global _client
    if _client is None:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_ANON_KEY")
        if not url or not key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_ANON_KEY must be set")
        _client = create_client(url, key)
    return _client


# --- workspaces ---

def ensure_workspace(ws_id: str) -> None:
    """Insert workspace row if it doesn't exist. Idempotent."""
    client().table("workspaces").upsert(
        {"id": ws_id}, on_conflict="id"
    ).execute()


# --- jobs ---

def list_jobs(ws_id: str) -> list[dict]:
    res = client().table("jobs").select("*").eq("workspace_id", ws_id).order("created_at", desc=False).execute()
    return res.data or []


def search_jobs(ws_id: str, query: str) -> list[dict]:
    q = query.lower()
    res = (
        client().table("jobs").select("*").eq("workspace_id", ws_id)
        .or_(f"client_name.ilike.%{q}%,description.ilike.%{q}%")
        .execute()
    )
    return res.data or []


def find_job_by_client(ws_id: str, client_name: str) -> Optional[dict]:
    res = (
        client().table("jobs").select("*").eq("workspace_id", ws_id)
        .ilike("client_name", f"%{client_name}%")
        .limit(1).execute()
    )
    rows = res.data or []
    return rows[0] if rows else None


def create_job(
    ws_id: str,
    client_name: str,
    description: str,
    job_date: str = "TBD",
    job_time: str = "TBD",
    address: str = "Not specified",
    priority: str = "normal",
) -> dict:
    res = client().table("jobs").insert({
        "workspace_id": ws_id,
        "client_name": client_name,
        "description": description,
        "job_date": job_date,
        "job_time": job_time,
        "address": address,
        "priority": priority,
        "status": "Scheduled",
        "notes": [],
    }).execute()
    return res.data[0]


def add_note_to_job(ws_id: str, client_name: str, note_text: str, time_label: str) -> Optional[dict]:
    job = find_job_by_client(ws_id, client_name)
    if not job:
        return None
    notes = job.get("notes") or []
    notes.append({"text": note_text, "time": time_label})
    res = client().table("jobs").update({"notes": notes}).eq("id", job["id"]).execute()
    return res.data[0] if res.data else None


def update_job_status(ws_id: str, client_name: str, status: str) -> Optional[dict]:
    job = find_job_by_client(ws_id, client_name)
    if not job:
        return None
    res = client().table("jobs").update({"status": status}).eq("id", job["id"]).execute()
    return res.data[0] if res.data else None


def set_job_status_by_id(job_id: int, status: str) -> None:
    client().table("jobs").update({"status": status}).eq("id", job_id).execute()


def delete_job(job_id: int) -> None:
    client().table("jobs").delete().eq("id", job_id).execute()


# --- quotes ---

def get_active_quote(ws_id: str) -> Optional[dict]:
    res = (
        client().table("quotes").select("*").eq("workspace_id", ws_id).eq("status", "draft")
        .order("created_at", desc=True).limit(1).execute()
    )
    rows = res.data or []
    if not rows:
        return None
    quote = rows[0]
    quote["line_items"] = _list_line_items(quote["id"])
    return quote


def list_completed_quotes(ws_id: str) -> list[dict]:
    res = (
        client().table("quotes").select("*").eq("workspace_id", ws_id).neq("status", "draft")
        .order("created_at", desc=True).execute()
    )
    quotes = res.data or []
    for q in quotes:
        q["line_items"] = _list_line_items(q["id"])
    return quotes


def _list_line_items(quote_id: int) -> list[dict]:
    res = (
        client().table("quote_line_items").select("*").eq("quote_id", quote_id)
        .order("position", desc=False).execute()
    )
    return res.data or []


def start_quote(ws_id: str, client_name: str, job_description: str, address: str = "") -> dict:
    res = client().table("quotes").insert({
        "workspace_id": ws_id,
        "client_name": client_name,
        "job_description": job_description,
        "address": address,
        "status": "draft",
    }).execute()
    quote = res.data[0]
    quote["line_items"] = []
    return quote


def add_line_item(
    quote_id: int,
    item_name: str,
    category: str,
    unit_price: float,
    quantity: float,
    unit: str = "each",
) -> dict:
    next_pos = _next_position(quote_id)
    line_total = round(unit_price * quantity, 2)
    res = client().table("quote_line_items").insert({
        "quote_id": quote_id,
        "position": next_pos,
        "item_name": item_name,
        "category": category,
        "unit_price": unit_price,
        "quantity": quantity,
        "unit": unit,
        "line_total": line_total,
    }).execute()
    return res.data[0]


def remove_line_item_at_position(quote_id: int, position_1based: int) -> Optional[dict]:
    items = _list_line_items(quote_id)
    if position_1based < 1 or position_1based > len(items):
        return None
    target = items[position_1based - 1]
    client().table("quote_line_items").delete().eq("id", target["id"]).execute()
    return target


def _next_position(quote_id: int) -> int:
    res = (
        client().table("quote_line_items").select("position").eq("quote_id", quote_id)
        .order("position", desc=True).limit(1).execute()
    )
    rows = res.data or []
    return (rows[0]["position"] + 1) if rows else 1


def finalise_quote(quote_id: int, notes: str = "", include_gst: bool = True) -> dict:
    items = _list_line_items(quote_id)
    subtotal = round(sum(li["line_total"] for li in items), 2)
    gst = round(subtotal * 0.1, 2) if include_gst else 0.0
    total = round(subtotal + gst, 2)
    res = client().table("quotes").update({
        "status": "sent",
        "notes": notes,
        "include_gst": include_gst,
        "subtotal": subtotal,
        "gst": gst,
        "total": total,
        "finalised_at": "now()",
    }).eq("id", quote_id).execute()
    quote = res.data[0]
    quote["line_items"] = items
    return quote


def delete_quote(quote_id: int) -> None:
    client().table("quotes").delete().eq("id", quote_id).execute()


# --- telemetry (used by task #3) ---

def log_tool_call_event(
    workspace_id: Optional[str],
    turn_id: str,
    rounds_used: int,
    hit_cap: bool,
    tools_called: list[str],
    total_latency_ms: Optional[int],
    prompt_tokens: Optional[int],
    completion_tokens: Optional[int],
    error: Optional[str] = None,
) -> None:
    client().table("tool_call_events").insert({
        "workspace_id": workspace_id,
        "turn_id": turn_id,
        "rounds_used": rounds_used,
        "hit_cap": hit_cap,
        "tools_called": tools_called,
        "total_latency_ms": total_latency_ms,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "error": error,
    }).execute()


def telemetry_stats(ws_id: Optional[str] = None) -> dict:
    """Aggregate stats for the Dev panel. None ws_id = global."""
    q = client().table("tool_call_events").select("rounds_used,hit_cap,total_latency_ms,tools_called")
    if ws_id:
        q = q.eq("workspace_id", ws_id)
    res = q.execute()
    rows = res.data or []
    if not rows:
        return {"total_turns": 0}
    total = len(rows)
    rounds = [r["rounds_used"] for r in rows]
    cap_hits = sum(1 for r in rows if r["hit_cap"])
    latencies = sorted([r["total_latency_ms"] for r in rows if r["total_latency_ms"] is not None])
    p50 = latencies[len(latencies) // 2] if latencies else None
    p95 = latencies[int(len(latencies) * 0.95)] if latencies else None
    tool_counts: dict[str, int] = {}
    for r in rows:
        for t in r.get("tools_called") or []:
            tool_counts[t] = tool_counts.get(t, 0) + 1
    return {
        "total_turns": total,
        "avg_rounds": round(sum(rounds) / total, 2),
        "hit_cap_rate": round(cap_hits / total * 100, 1),
        "p50_latency_ms": p50,
        "p95_latency_ms": p95,
        "top_tools": sorted(tool_counts.items(), key=lambda x: -x[1])[:5],
    }
