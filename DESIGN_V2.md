SiteVoice v2 - Design Document

This is a design for the production version of SiteVoice. Deliberately not built. The current Streamlit version is the right tool for a 33-hour hackathon and a single-user demo. v2 is what I would do given a real product runway: mobile-first, multi-tenant, sub-second voice latency.


Why Migrate

The Streamlit version has three structural ceilings:

1. No mobile-friendly UI. Tradies are not at desks. They are in vans, in trenches, on roofs. Streamlit's rerun-the-whole-script model and its session-per-tab state make a real mobile experience impossible. We need a PWA on a phone.

2. Voice latency is too high. End-to-end p50 is ~5-6 seconds: record audio, upload, Whisper transcribe, GPT-4o respond, TTS generate, playback. Tradies will lose patience. We need sub-second time-to-first-word - which means streaming everything.

3. Single-tenant by design. URL-based workspaces are great for a demo but break the moment two plumbers from the same business want to share a job board. Auth becomes load-bearing.

Each of these is fixable in v2 without rewriting the AI logic.


Architecture

```
Browser (Next.js PWA on phone)
   |
   |-- HTTPS / REST: jobs, quotes, materials lookup, telemetry reads
   |-- WebSocket: streaming voice (chunked audio in, streaming TTS out)
   |
   v
Backend (FastAPI on Railway)
   |
   |-- /api/jobs (REST: CRUD)
   |-- /api/quotes (REST: CRUD)
   |-- /api/materials/search (REST: read-only)
   |-- /ws/voice (WebSocket: full-duplex voice loop)
   |       |- listens for audio chunks
   |       |- streams them to Whisper as they arrive
   |       |- sends partial transcripts back to client
   |       |- on speech end, sends transcript to GPT-4o (streaming)
   |       |- pipes GPT-4o tokens directly to OpenAI TTS streaming endpoint
   |       |- streams audio chunks back to client
   |
   v
Supabase Postgres (same schema, plus auth)
```


Frontend - Next.js 15 App Router

Why Next.js over SvelteKit / Remix: React ecosystem maturity for the audio APIs (MediaRecorder, AudioContext) and component libraries that already handle voice UX patterns. App Router specifically because the marketing page benefits from server components and SEO, while the live agent page is fully client-side.

Page structure:

- /  (marketing landing, server component)
- /app  (live agent, client component, requires auth)
- /app/quotes/[id]  (shareable quote URL, server-rendered for OG metadata)
- /app/jobs  (job board, client component)

State management: Zustand for client state (active conversation, audio playback state), React Query for server state (jobs, quotes - cached, stale-while-revalidate). No Redux. No useReducer maze.

Voice UX: a single big "tap to talk" button on /app. Hold-to-talk on mobile, tap-toggle on desktop. WebSocket connection opens on first interaction (browser autoplay rules require it). Visual states: idle / listening (waveform animation) / thinking / speaking (pulsing).

Why a PWA over a native app: 90% of the value with 10% of the work. iOS PWAs handle audio fine via getUserMedia. No App Store review cycle. Native is the next move if we ever care about background recording or system-level shortcuts.


Backend - FastAPI on Railway

Why FastAPI over Express / Hono: async-native fits the voice streaming pattern; Pydantic gives typed request/response schemas that the Next.js client consumes directly via auto-generated OpenAPI types. The AI logic is Python-native (existing prompts, tool definitions, plumbing_data.py port directly).

Why Railway over Vercel functions: long-lived WebSocket connections. Vercel functions are serverless and time-limited; the voice stream needs a persistent process. Railway runs a real container at $5/month for the demo tier.

API surface:

REST endpoints (all require Authorization: Bearer <jwt>):
- GET    /api/jobs               - list workspace jobs
- POST   /api/jobs               - create job
- PATCH  /api/jobs/:id           - update status, notes
- DELETE /api/jobs/:id
- GET    /api/quotes             - list (filter: ?status=draft|sent)
- POST   /api/quotes             - start new quote
- POST   /api/quotes/:id/items   - add line item
- DELETE /api/quotes/:id/items/:position
- POST   /api/quotes/:id/finalise
- DELETE /api/quotes/:id
- GET    /api/materials/search   - paginated, materials database
- GET    /api/telemetry/stats    - dev-only, telemetry aggregates

WebSocket: /ws/voice

Protocol (JSON-encoded messages over WS):

Client -> server:
- { type: "audio_chunk", data: <base64 PCM 16kHz mono> }
- { type: "audio_end" }
- { type: "interrupt" }  // user tapped while AI was speaking

Server -> client:
- { type: "partial_transcript", text: "..." }
- { type: "final_transcript", text: "..." }
- { type: "tool_call", name: "...", args: {...} }
- { type: "tool_result", name: "...", result: "..." }
- { type: "text_delta", delta: "..." }       // streaming GPT-4o tokens
- { type: "audio_chunk", data: <base64 mp3 chunk> }
- { type: "turn_end", turn_id: "uuid" }


Voice Latency Budget

Goal: time-to-first-audio-byte under 1.2 seconds from end-of-user-speech.

Pipeline:
- Whisper streaming (or chunked - Whisper API is not truly streaming yet; alternative: Deepgram Nova-2 which IS streaming, ~150ms partial latency)
- GPT-4o streaming (first token typically ~400ms after request)
- OpenAI TTS streaming endpoint (first audio chunk ~200ms after first text token)

If we stay on OpenAI throughout: realistic p50 ~1.5s. Switching STT to Deepgram brings us close to 1s. Worth the complexity for v2; not worth it for v1.


Auth - Supabase Auth + RLS

Migrate from URL-based workspace UUIDs to authenticated user accounts.

Schema changes:
- Add `user_id uuid` column to workspaces (FK to auth.users)
- Workspaces become 1-to-many with users (a tradie can have multiple workspaces; useful for separating work from a side gig, or sharing one workspace across a small business team)
- Add `workspace_members` table for shared workspaces (user_id, workspace_id, role)
- Enable RLS on jobs, quotes, quote_line_items, tool_call_events
- RLS policies: "user can read/write rows where workspace_id is in their accessible set"

The current schema is already shaped for this; no breaking migration needed.

Sign-in flow: Supabase Auth with Google OAuth (single-click for tradies who already have a Gmail), or email magic link as fallback. No password forms. No "verify your email" friction.


Deployment Topology

- Frontend: Vercel (Next.js, edge runtime where it makes sense, $0 hobby tier covers personal demo)
- Backend: Railway ($5/month hobby, custom domain, persistent WebSocket)
- Database: Supabase ($0 free tier, paid $25/month if traffic warrants)
- Domain: sitevoice.app or similar; Cloudflare DNS

Total cost: $5-30/month depending on tier. Under $1/day even with traffic.


What's Deliberately Out of Scope for v2

- Native iOS/Android apps. PWA covers 90% of value.
- Multi-language. English (Australian) only; expand once we have one happy customer.
- Custom voice cloning. The OpenAI tts-1 onyx voice is fine.
- Offline mode. Tradies have phones; phones have signal; PWA cache covers brief drops.
- Quote PDF export. Email a link to the share URL instead. No PDF rendering pain.
- SMS / email notifications. Twilio + Postmark are weeks of work for marginal value pre-product-market-fit.

These are all things a real product would eventually need. Including them in v2 scope is exactly the kind of premature scaling that kills demos.


Migration Effort Estimate

Realistic solo timeline assuming I am NOT learning React from scratch:

- Frontend scaffold + auth: 1 week
- REST API port from Streamlit handlers: 3 days
- WebSocket voice loop: 1 week (this is the hardest part - streaming, interruption, error handling)
- Materials search UX with autocomplete: 2 days
- Polish, mobile QA, deploy: 3-4 days

Total: 3-4 weeks of focused work. Half the time is the voice loop; that's where the perceived quality lives.


Why I Haven't Built This Yet

Two reasons. First, the Streamlit version is genuinely the right answer for the constraint that produced it (33-hour hackathon, solo, voice-first). Building v2 retroactively just to look impressive is the wrong frame; the project should be defensible on its own merits at the size it is. Second, my time is better spent right now on the things only I can do: explaining the decisions, instrumenting the existing code, writing this design doc. v2 is a 3-4 week project in a clear week. It's on the list, not on the critical path.
