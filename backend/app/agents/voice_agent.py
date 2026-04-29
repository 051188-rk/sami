"""
Hospital AI Voice Agent — LiveKit Worker

Architecture:
  Deepgram STT → LangChain AgentExecutor (Gemini) → Cartesia TTS
  Tool events are broadcast via LiveKit data channel to the frontend.

Run with:
  python -m app.agents.voice_agent dev
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Allow imports from project root
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from livekit import rtc
from livekit.agents import (
    AutoSubscribe,
    JobContext,
    WorkerOptions,
    cli,
    llm as lk_llm,
)
from livekit.agents.pipeline import VoicePipelineAgent
from livekit.plugins import cartesia, deepgram

from app.tools.appointment_tools import SessionState, create_tools

logger = logging.getLogger("hospital-agent")

SYSTEM_PROMPT = """
You are a friendly and professional AI receptionist at City General Hospital.
Your job is to help patients book, manage, modify, and cancel appointments.

Guidelines:
- Always greet the patient warmly at the start
- Ask for their phone number early to identify them (use identify_user tool)
- Listen carefully to understand their intent before calling tools
- Confirm details before booking or cancelling
- Be concise — patients are speaking verbally, so keep responses short
- If a patient wants to end the call, use end_conversation tool
- Never make up doctor names or slots — always use fetch_slots tool
- Maintain a natural conversational flow across multiple turns

You have access to these tools:
- identify_user: Register or look up a patient by phone number
- fetch_slots: Get available appointment slots for doctors
- book_appointment: Book a slot for the identified patient
- retrieve_appointments: Get the patient's existing appointments
- cancel_appointment: Cancel an appointment by ID
- modify_appointment: Reschedule an appointment
- end_conversation: End the call and generate a summary

Always be warm, professional, and efficient.
""".strip()


# ---------------------------------------------------------------------------
# Custom LLM: wraps LangChain AgentExecutor inside LiveKit's LLM interface
# ---------------------------------------------------------------------------

class LangChainLLM(lk_llm.LLM):
    """
    A LiveKit LLM plugin that delegates to a LangChain AgentExecutor
    backed by Gemini 1.5 Pro with tool calling.
    """

    def __init__(self, state: SessionState):
        super().__init__()
        self._state = state
        self._executor = self._build_executor()
        self._chat_history: list = []

    def _build_executor(self):
        from langchain.agents import AgentExecutor, create_tool_calling_agent
        from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
        from langchain_google_genai import ChatGoogleGenerativeAI

        tools = create_tools(self._state)

        llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-pro",
            google_api_key=os.getenv("GEMINI_API_KEY"),
            temperature=0.4,
            convert_system_message_to_human=True,
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder("agent_scratchpad"),
        ])

        agent = create_tool_calling_agent(llm, tools, prompt)
        return AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,
            max_iterations=8,
            handle_parsing_errors=True,
        )

    def chat(
        self,
        *,
        chat_ctx: lk_llm.ChatContext,
        fnc_ctx=None,
    ) -> "LangChainLLMStream":
        return LangChainLLMStream(
            executor=self._executor,
            chat_ctx=chat_ctx,
            history=self._chat_history,
            llm=self,
        )


class LangChainLLMStream(lk_llm.LLMStream):
    def __init__(self, executor, chat_ctx: lk_llm.ChatContext, history: list, llm):
        super().__init__(llm, chat_ctx=chat_ctx, fnc_ctx=None)
        self._executor = executor
        self._history = history

    async def _run(self):
        from langchain_core.messages import AIMessage, HumanMessage

        # Extract last user message from chat context
        messages = self._chat_ctx.messages
        user_text = ""
        for msg in reversed(messages):
            if msg.role == "user":
                user_text = msg.content if isinstance(msg.content, str) else ""
                break

        if not user_text:
            return

        try:
            # Run LangChain agent in thread pool (sync executor)
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self._executor.invoke({
                    "input": user_text,
                    "chat_history": self._history,
                }),
            )
            response_text = result.get("output", "I'm sorry, I didn't understand that.")

            # Update conversation history
            self._history.append(HumanMessage(content=user_text))
            self._history.append(AIMessage(content=response_text))

            # Keep history bounded to last 10 turns (20 messages)
            if len(self._history) > 20:
                self._history = self._history[-20:]

        except Exception as exc:
            logger.exception("LangChain agent error: %s", exc)
            response_text = "I'm sorry, I encountered an issue. Please try again."

        # Emit the response as a single chunk
        self._event_ch.send_nowait(
            lk_llm.ChatChunk(
                choices=[
                    lk_llm.Choice(
                        delta=lk_llm.ChoiceDelta(role="assistant", content=response_text),
                        index=0,
                    )
                ]
            )
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

    stt = deepgram.STT(
        api_key=os.getenv("DEEPGRAM_API_KEY"),
        model="nova-2",
        language="en-US",
        interim_results=False,
        smart_format=True,
    )

    tts = cartesia.TTS(
        api_key=os.getenv("CARTESIA_API_KEY"),
        voice_id="248be419-c632-4f23-adf1-5324ed7dbf1d",  # Friendly female voice
        model="sonic-english",
    )

    agent = VoicePipelineAgent(
        vad=None,
        stt=stt,
        llm=langchain_llm,
        tts=tts,
        min_endpointing_delay=0.5,
        allow_interruptions=True,
    )

    # Broadcast transcripts to frontend via data channel
    @agent.on("user_speech_committed")
    def on_user_speech(msg: lk_llm.ChatMessage):
        payload = json.dumps({
            "type": "transcript",
            "role": "user",
            "text": msg.content if isinstance(msg.content, str) else "",
        }).encode()
        asyncio.ensure_future(
            ctx.room.local_participant.publish_data(payload, reliable=True)
        )

    @agent.on("agent_speech_committed")
    def on_agent_speech(msg: lk_llm.ChatMessage):
        payload = json.dumps({
            "type": "transcript",
            "role": "assistant",
            "text": msg.content if isinstance(msg.content, str) else "",
        }).encode()
        asyncio.ensure_future(
            ctx.room.local_participant.publish_data(payload, reliable=True)
        )

    @agent.on("agent_started_speaking")
    def on_agent_speaking():
        payload = json.dumps({"type": "avatar_state", "speaking": True}).encode()
        asyncio.ensure_future(
            ctx.room.local_participant.publish_data(payload, reliable=True)
        )

    @agent.on("agent_stopped_speaking")
    def on_agent_stopped():
        payload = json.dumps({"type": "avatar_state", "speaking": False}).encode()
        asyncio.ensure_future(
            ctx.room.local_participant.publish_data(payload, reliable=True)
        )

    agent.start(ctx.room)

    # Greet the patient
    await agent.say(
        "Hello! Welcome to City General Hospital. I'm your AI receptionist. "
        "How can I help you today? I can help you book, manage, or cancel appointments.",
        allow_interruptions=True,
    )

    # Keep agent alive until room is empty
    await asyncio.sleep(3600)


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            worker_type="room",
        )
    )
