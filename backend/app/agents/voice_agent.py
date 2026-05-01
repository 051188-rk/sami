"""
Hospital AI Voice Agent — LiveKit Worker (livekit-agents 0.8.12)

Architecture:
  Silero VAD → Deepgram STT → LangChain AgentExecutor (Gemini 2.5-flash) → Cartesia TTS
  Tool events broadcast via LiveKit data channel to the frontend.

Run with:
  python -m app.agents.voice_agent dev
"""

import asyncio
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from livekit.agents import (
    AutoSubscribe,
    JobContext,
    WorkerOptions,
    WorkerType,
    cli,
    llm as lk_llm,
)
from livekit.agents.voice_assistant import VoiceAssistant
from livekit.plugins import cartesia, deepgram
from livekit.plugins.silero import VAD as SileroVAD

from app.tools.appointment_tools import SessionState, create_tools

# Silence the noisy google.generativeai deprecation warning
import warnings
warnings.filterwarnings("ignore", category=FutureWarning, module="langchain_google_genai")
warnings.filterwarnings("ignore", category=UserWarning, module="langchain_google_genai")

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("hospital-agent")
logger.setLevel(logging.INFO)

# Mute internal langchain / livekit noise that isn't useful in production
for noisy in ("langchain", "langchain_core", "langchain_google_genai",
              "livekit.agents.pipeline", "asyncio"):
    logging.getLogger(noisy).setLevel(logging.ERROR)

SYSTEM_PROMPT = """
You are a friendly and professional AI receptionist at City General Hospital.
Help patients book, manage, modify, and cancel appointments.

Guidelines:
- Greet the patient warmly at the start
- Ask for phone number early to identify them (use identify_user tool)
- Confirm details before booking or cancelling
- Be concise — keep responses under 2–3 short sentences
- Use end_conversation tool when patient says goodbye
- Never invent doctors or slots — always use fetch_slots tool

Available tools: identify_user, fetch_slots, book_appointment,
retrieve_appointments, cancel_appointment, modify_appointment, end_conversation.
""".strip()


def _parse_retry_secs(err_str: str) -> int:
    """Extract the retry_delay seconds from a Gemini 429 response string."""
    m = re.search(r"retry_delay\s*\{\s*seconds:\s*(\d+)", err_str)
    return int(m.group(1)) + 2 if m else 30


# ---------------------------------------------------------------------------
# LangChainLLMStream
#
# Key design: a shared asyncio.Lock (one per session) ensures only ONE
# Gemini call is in-flight at a time, preventing the rate-limit flood.
# ---------------------------------------------------------------------------

class LangChainLLMStream(lk_llm.LLMStream):
    def __init__(
        self,
        executor,
        chat_ctx: lk_llm.ChatContext,
        history: list,
        lock: asyncio.Lock,
    ):
        super().__init__(chat_ctx=chat_ctx, fnc_ctx=None)
        self._executor = executor
        self._history = history
        self._lock = lock
        self._queue: asyncio.Queue[Optional[lk_llm.ChatChunk]] = asyncio.Queue()
        self._gen_task = asyncio.ensure_future(self._generate())

    async def _generate(self) -> None:
        from langchain_core.messages import AIMessage, HumanMessage

        user_text = ""
        for msg in reversed(self._chat_ctx.messages):
            if msg.role == "user":
                content = msg.content
                user_text = content if isinstance(content, str) else ""
                break

        if not user_text:
            await self._queue.put(None)
            return

        response_text = "I'm experiencing a short delay. Please hold on."

        # Acquire the session-wide lock → only one Gemini call runs at a time
        async with self._lock:
            loop = asyncio.get_event_loop()
            last_exc = None

            for attempt in range(4):
                try:
                    result = await loop.run_in_executor(
                        None,
                        lambda: self._executor.invoke({
                            "input": user_text,
                            "chat_history": list(self._history),
                        }),
                    )
                    response_text = result.get("output", response_text)
                    last_exc = None
                    break

                except Exception as exc:
                    last_exc = exc
                    err_str = str(exc)
                    is_rate_limit = (
                        "429" in err_str
                        or "ResourceExhausted" in err_str
                        or "quota" in err_str.lower()
                    )
                    if is_rate_limit:
                        wait = _parse_retry_secs(err_str)
                        logger.warning(
                            "Gemini rate limit — waiting %ds (attempt %d/4)", wait, attempt + 1
                        )
                        await asyncio.sleep(wait)
                    else:
                        logger.exception("LangChain agent error: %s", exc)
                        break

            if last_exc:
                response_text = (
                    "I'm very busy right now. Please say that again in a moment."
                )

            # Update shared rolling history (max 20 messages = 10 turns)
            self._history.append(HumanMessage(content=user_text))
            self._history.append(AIMessage(content=response_text))
            if len(self._history) > 20:
                del self._history[:-20]

        await self._queue.put(
            lk_llm.ChatChunk(
                choices=[
                    lk_llm.Choice(
                        delta=lk_llm.ChoiceDelta(role="assistant", content=response_text),
                        index=0,
                    )
                ]
            )
        )
        await self._queue.put(None)

    async def __anext__(self) -> lk_llm.ChatChunk:
        item = await self._queue.get()
        if item is None:
            raise StopAsyncIteration
        return item


# ---------------------------------------------------------------------------
# LangChainLLM plugin
# ---------------------------------------------------------------------------

class LangChainLLM(lk_llm.LLM):
    def __init__(self, state: SessionState):
        super().__init__()
        self._state = state
        self._executor = self._build_executor()
        self._chat_history: list = []
        # One lock per session — serializes all LLM invocations
        self._lock: asyncio.Lock = asyncio.Lock()

    def _build_executor(self):
        from langchain.agents import AgentExecutor, create_tool_calling_agent
        from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
        from langchain_google_genai import ChatGoogleGenerativeAI

        tools = create_tools(self._state)

        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=os.getenv("GEMINI_API_KEY"),
            temperature=0.4,
            max_retries=0,  # we handle retries ourselves with proper delays
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        agent = create_tool_calling_agent(llm, tools, prompt)
        return AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=False,       # suppress the noisy chain logs
            max_iterations=6,
            handle_parsing_errors=True,
        )

    def chat(
        self,
        *,
        chat_ctx: lk_llm.ChatContext,
        fnc_ctx: Optional[lk_llm.FunctionContext] = None,
    ) -> LangChainLLMStream:
        return LangChainLLMStream(
            executor=self._executor,
            chat_ctx=chat_ctx,
            history=self._chat_history,
            lock=self._lock,
        )


# ---------------------------------------------------------------------------
# Agent entry point
# ---------------------------------------------------------------------------

async def entrypoint(ctx: JobContext):
    logger.info("Agent job received: room=%s", ctx.room.name)

    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    session_id = ctx.room.name
    state = SessionState(session_id=session_id, room=ctx.room)

    langchain_llm = LangChainLLM(state=state)

    vad = SileroVAD.load()

    stt = deepgram.STT(
        api_key=os.getenv("DEEPGRAM_API_KEY"),
        model="nova-2-phonecall",
        language="en-US",
        interim_results=False,   # only fire on final transcript
        smart_format=True,
        punctuate=True,
        endpointing_ms=300,      # wait 300 ms of silence before committing speech
    )

    # Use a reliable default voice
    tts = cartesia.TTS(
        api_key=os.getenv("CARTESIA_API_KEY"),
        model="sonic-english",
        voice="79a125e8-cd45-4c05-928a-699e25295b5c",  # Default Cartesia voice
        language="en",
    )

    agent = VoiceAssistant(
        vad=vad,
        stt=stt,
        llm=langchain_llm,
        tts=tts,
        allow_interruptions=False,   # let TTS finish before accepting new input
    )

    @agent.on("user_speech_committed")
    def on_user_speech(msg: lk_llm.ChatMessage):
        _publish(ctx, {
            "type": "transcript",
            "role": "user",
            "text": msg.content if isinstance(msg.content, str) else "",
        })

    @agent.on("agent_speech_committed")
    def on_agent_speech(msg: lk_llm.ChatMessage):
        logger.info(f"Agent speech committed: {msg.content}")
        _publish(ctx, {
            "type": "transcript",
            "role": "assistant",
            "text": msg.content if isinstance(msg.content, str) else "",
        })

    @agent.on("agent_started_speaking")
    def on_agent_speaking():
        logger.info("Agent started speaking - TTS should be playing")
        _publish(ctx, {"type": "avatar_state", "speaking": True})

    @agent.on("agent_stopped_speaking")
    def on_agent_stopped():
        logger.info("Agent stopped speaking")
        _publish(ctx, {"type": "avatar_state", "speaking": False})

    agent.start(ctx.room)

    await agent.say(
        "Hello! Welcome to City General Hospital. I'm your AI receptionist. "
        "How can I help you today?",
        allow_interruptions=False,
    )

    await asyncio.sleep(3600)


def _publish(ctx: JobContext, data: dict) -> None:
    payload = json.dumps(data).encode()
    asyncio.ensure_future(
        ctx.room.local_participant.publish_data(payload, reliable=True)
    )


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            worker_type=WorkerType.ROOM,
        )
    )
