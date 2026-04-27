SiteVoice

A hands-free AI assistant for plumbers. Voice in, voice out. Schedules jobs, looks up material prices, builds itemised quotes by conversation, and keeps everything persistent across sessions.

Built solo for the Sophiie AI Agents Hackathon (Feb 14-15, 2026), then refactored into a production-leaning portfolio piece.


The Problem

Tradies spend half their day on tools and the other half on admin. Quote-building in particular is brutal: scribbling notes on a job site, re-typing them into a spreadsheet that night, looking up unit prices, calculating GST, sending it before the customer goes cold. SiteVoice flips it. The plumber talks. The agent listens, asks clarifying questions, looks up prices from a real materials database, builds the quote line-by-line in a sidebar card, and locks it in on command. Hands stay free. Quotes ship same day.


How It Works

```
Browser  <->  Streamlit (Python)  <->  OpenAI (Whisper / GPT-4o / TTS)
                    |
                    v
              Supabase Postgres
              (jobs, quotes, telemetry)
```

A single Streamlit script renders both the UI and the server-side logic. Voice input goes to Whisper for transcription. The transcript hits GPT-4o with 11 function tools registered (create_job, start_quote, add_quote_line_item, finalise_quote, lookup_price, daily_summary, etc). GPT-4o decides whether to ask a clarifying question or call tools; the loop runs up to 5 rounds per turn. The text reply goes to OpenAI tts-1 (voice: onyx) and plays back via an HTML audio element. If the reply ends with a question, JavaScript auto-clicks the mic button so the next user turn starts immediately - no tap-to-talk friction during a real conversation.

Persistence is a Supabase Postgres database keyed by an unguessable workspace UUID in the URL (?ws=...). Same security model as a Google Docs share link: knowing the URL grants access. Refresh keeps your data. Open a new tab without ?ws= and you get a fresh empty workspace. No login.

Every GPT-4o turn is instrumented. A telemetry table logs round count, tools called, latency, and token usage. A Dev panel in the sidebar reads aggregates: avg rounds, hit-cap rate, p50/p95 latency, top tools.


Tech Stack

- Streamlit (frontend + backend in one Python process)
- OpenAI: gpt-4o (chat + function calling), whisper-1 (STT), tts-1 (TTS, voice=onyx)
- Supabase Postgres (persistence + telemetry)
- supabase-py (DB client)
- python-dotenv (secrets in dev)


Run Locally

Prerequisites: Python 3.11+, uv (https://docs.astral.sh/uv/), an OpenAI API key, and a Supabase project.

    git clone https://github.com/IshaanKataria/sitevoice.git
    cd sitevoice
    uv venv
    uv pip install -r requirements.txt

Create .env with your secrets:

    OPENAI_API_KEY=sk-...
    SUPABASE_URL=https://your-project.supabase.co
    SUPABASE_ANON_KEY=eyJ...

Apply the schema (paste schema.sql into Supabase SQL Editor and run). Then:

    uv run streamlit run app.py

Open http://localhost:8501. The first load mints a workspace UUID and redirects to ?ws=<uuid>. Bookmark it; refresh keeps your jobs and quotes.


Decisions

Why Streamlit over Next.js + FastAPI? Speed. A 33-hour hackathon rewards shipping working voice STT/TTS in hours, not days. Streamlit unifies frontend + backend in one Python process, so there's no API contract to define and no TypeScript context-switch. The cost is real: no mobile-friendly UI, no fine-grained component control, session state model is per-tab. For a single-tradie demo this tradeoff is correct. For productionising see DESIGN_V2.md.

Why GPT-4o over Claude or Gemini? Function calling reliability and latency on a long tool chain. The quote workflow can fire 6+ tools in a single turn (start_quote, multiple add_quote_line_item, finalise_quote). GPT-4o handled this without hallucinating tool arguments in testing.

Why Supabase over SQLite? Streamlit Cloud has an ephemeral filesystem; SQLite would get wiped on every redeploy. Supabase gives free hosted Postgres with no DevOps. Postgres also unlocks JSONB for the per-job notes array and indexes on workspace_id - cheap stuff that matters when there's more than one tradie.

Why URL-based workspaces over auth? Auth is the wrong abstraction for a demo. Each browser gets a unique unguessable UUID; refresh-stable, shareable, no signup friction. For a real multi-tenant version you swap the workspace_id for an authenticated user_id and add Supabase RLS policies. The schema is already shaped for that migration.

Why function calling over intent classification? Structured tool definitions let the model parse client names and amounts directly into typed arguments, instead of hoping a regex catches the right substring. It's the modern approach and it composes - GPT-4o can chain 5 tools in one turn.

Why telemetry on a personal project? Most student projects ship and pray. I instrumented every GPT-4o turn so I could measure hit-cap rate, round count, and latency over time. Found that quote-building turns average 1.5-2 rounds and never hit the 5-round cap, so the cap is not the bottleneck. Latency p50 is around 5-6s end-to-end - the path to improvement is streaming TTS, not the cap.


What's in the Code

- app.py - the Streamlit script: page config, system prompt, 11 tool definitions, function handlers, voice I/O, audio playback with autoplay-block fallback
- db.py - thin Supabase wrappers (workspaces, jobs, quotes, line items, telemetry)
- plumbing_data.py - hardcoded materials + labour rate database (Australian prices, AUD)
- schema.sql - Postgres DDL for the 5 tables, indexed
- requirements.txt - pinned to streamlit / openai / python-dotenv / supabase


What I'd Do Next

See DESIGN_V2.md for the full v2 spec: migrate to Next.js + FastAPI, stream Whisper chunks over WebSocket for sub-second voice latency, add Supabase Auth with RLS, ship a mobile PWA. Designed but deliberately not built - the Streamlit version is the right tool for the demo's constraints.


Built For

Sophiie AI Agents Hackathon 2026 - solo, 33 hours, voice agent track. The original hackathon submission lives at github.com/IshaanKataria/hackathon. This repo is the post-hackathon polished version.
