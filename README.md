# sami.ai

A production-ready AI voice agent for hospital front desks. Patients speak naturally to book, manage, modify, and cancel appointments. The system uses LiveKit for real-time voice streaming, Deepgram for STT, Cartesia for TTS, Gemini as the LLM, and Beyond Presence for a lip-synced avatar.

---

## Architecture

![Architecture Diagram](diagram.png)

**Tool execution events** are broadcast via LiveKit data channel to the frontend in real time.

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
