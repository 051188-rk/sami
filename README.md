# Hospital AI Voice Appointment Booking System

A production-ready AI voice agent for hospital front desks. Patients speak naturally to book, manage, modify, and cancel appointments. The system uses LiveKit for real-time voice streaming, Deepgram for STT, Cartesia for TTS, Gemini as the LLM, and Beyond Presence for a lip-synced avatar.

---

## Architecture

```
User Speech
    │
    ▼
LiveKit (real-time audio room)
    │
    ▼
Deepgram STT (transcript)
    │
    ▼
LangChain Agent + Gemini LLM
    │ (tool calls)
    ├──► identify_user        → SQLite (Users)
    ├──► fetch_slots          → hardcoded doctor schedules
    ├──► book_appointment     → SQLite (Appointments) + Twilio SMS
    ├──► retrieve_appointments → SQLite query
    ├──► cancel_appointment   → SQLite update
    ├──► modify_appointment   → SQLite update
    └──► end_conversation     → Gemini summary generation
    │
    ▼
Cartesia TTS (audio synthesis)
    │
    ▼
LiveKit (audio stream back to user)
    │
    ▼
Beyond Presence Avatar (lip-synced playback)
```

**Tool execution events** are broadcast via LiveKit data channel to the frontend in real time.

---

## Monorepo Structure

```
sami/
├── frontend/            Next.js App Router UI
│   ├── app/
│   ├── components/
│   ├── lib/
│   └── ...
├── backend/             FastAPI + LiveKit Agent
│   ├── app/
│   │   ├── main.py
│   │   ├── agents/      LiveKit voice agent
│   │   ├── tools/       LangChain tools
│   │   ├── routes/      REST API routes
│   │   ├── models/      SQLAlchemy models
│   │   ├── db/          Database setup & seed
│   │   ├── services/    SMS, summary
│   │   └── utils/       Helpers
│   └── requirements.txt
└── README.md
```

---

## Prerequisites

- Python 3.11+
- Node.js 18+
- A LiveKit Cloud account (or self-hosted LiveKit server)
- API keys for: Deepgram, Cartesia, Gemini, Beyond Presence, Twilio

---

## Environment Setup

### Backend `.env`

Copy `backend/.env` and fill in your keys:

```env
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your_livekit_api_key
LIVEKIT_API_SECRET=your_livekit_api_secret
DEEPGRAM_API_KEY=your_deepgram_api_key
CARTESIA_API_KEY=your_cartesia_api_key
GEMINI_API_KEY=your_gemini_api_key
BEYOND_PRESENCE_API_KEY=your_beyond_presence_api_key
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_PHONE_NUMBER=+1234567890
```

### Frontend `.env`

Copy `frontend/.env` and fill in:

```env
NEXT_PUBLIC_LIVEKIT_URL=wss://your-project.livekit.cloud
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_BEYOND_PRESENCE_API_KEY=your_beyond_presence_api_key
```

---

## Running Locally

### 1. Backend API Server

```bash
cd backend
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`.

### 2. LiveKit Voice Agent (separate terminal)

```bash
cd backend
source venv/bin/activate  # or venv\Scripts\activate

python -m app.agents.voice_agent dev
```

The agent worker connects to LiveKit and waits for rooms to be created.

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`.

---

## How It Works

### Voice Pipeline

1. User clicks **Start Call** — frontend requests a LiveKit token from `/api/token`
2. Frontend joins the LiveKit room and publishes microphone audio
3. The LiveKit agent worker receives the job, joins the room, and starts the voice pipeline
4. **Deepgram** transcribes incoming audio in real time
5. Transcripts are sent to the **LangChain AgentExecutor** backed by **Gemini 1.5 Pro**
6. Gemini decides which tool to call (or responds directly)
7. Tool results are returned to Gemini for a final response
8. Response text goes to **Cartesia TTS** which synthesizes audio
9. Audio streams back through LiveKit to the user's browser
10. **Beyond Presence** avatar lip-syncs with the audio playback

### Tool Calling (LangChain)

Each tool is a `@tool`-decorated async function registered with the LangChain `AgentExecutor`:

| Tool | Description |
|------|-------------|
| `identify_user` | Ask for phone number, register in DB |
| `fetch_slots` | Return available slots for 5 hardcoded doctors |
| `book_appointment` | Create appointment, prevent double booking, send SMS |
| `retrieve_appointments` | Fetch all appointments for identified user |
| `cancel_appointment` | Mark appointment as cancelled |
| `modify_appointment` | Reschedule an existing appointment |
| `end_conversation` | Generate and store structured JSON summary |

Each tool fires a LiveKit data message (`type: tool_start` / `type: tool_complete`) so the frontend can show real-time tool execution status.

### Conversation Summary

When `end_conversation` is called, Gemini generates a structured JSON summary:

```json
{
  "summary_text": "Patient John booked with Dr. Smith...",
  "user_details": { "name": "John", "phone": "+1..." },
  "appointments": [...],
  "preferences": { "preferred_doctor": "..." },
  "timestamp": "2024-01-01T10:00:00"
}
```

This is stored server-side and also broadcast via the LiveKit data channel. The frontend renders it as the **Call Summary Screen**.

### SMS Confirmation

On every successful booking, Twilio sends an SMS to the patient's registered phone number with doctor name, date, and time.

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/token` | Generate LiveKit room token |
| `GET` | `/api/appointments/{phone}` | Get user appointments |
| `GET` | `/api/summary/{session_id}` | Get session summary |
| `GET` | `/api/health` | Health check |

---

## Design System

- **Theme**: Strict black and white — no colors, no gradients
- **Font**: Plus Jakarta Sans
- **Animations**: Framer Motion (subtle transitions)
- **Icons**: React Icons only
- **Framework**: Tailwind CSS utility classes
