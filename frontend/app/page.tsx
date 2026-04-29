"use client";

import { useCallback, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";

import AppointmentPanel from "@/components/AppointmentPanel";
import Avatar from "@/components/Avatar";
import SummaryScreen from "@/components/SummaryScreen";
import ToolExecution from "@/components/ToolExecution";
import Transcript from "@/components/Transcript";
import VoiceInterface from "@/components/VoiceInterface";
import { useHospitalSession } from "@/lib/useLiveKit";
import type { SessionSummary, ToolEvent, TranscriptEntry } from "@/lib/types";

export default function HomePage() {
  const [sessionState, setSessionState] = useState<
    "idle" | "connecting" | "active" | "ended"
  >("idle");
  const [transcripts, setTranscripts] = useState<TranscriptEntry[]>([]);
  const [toolEvents, setToolEvents] = useState<ToolEvent[]>([]);
  const [summary, setSummary] = useState<SessionSummary | null>(null);
  const [isSpeaking, setIsSpeaking] = useState(false);

  const handleTranscript = useCallback((entry: TranscriptEntry) => {
    setTranscripts((prev) => [...prev, entry]);
  }, []);

  const handleToolEvent = useCallback((event: ToolEvent) => {
    setToolEvents((prev) => {
      // If same tool has a pending start, update it to complete
      const idx = prev.findIndex(
        (e) => e.tool === event.tool && e.status === "running"
      );
      if (idx !== -1 && event.status === "complete") {
        const updated = [...prev];
        updated[idx] = { ...updated[idx], ...event };
        return updated;
      }
      return [...prev, event];
    });
  }, []);

  const handleSummary = useCallback((data: SessionSummary) => {
    setSummary(data);
    setSessionState("ended");
  }, []);

  const handleAvatarState = useCallback((speaking: boolean) => {
    setIsSpeaking(speaking);
  }, []);

  const { startSession, endSession, roomName } = useHospitalSession({
    onTranscript: handleTranscript,
    onToolEvent: handleToolEvent,
    onSummary: handleSummary,
    onAvatarState: handleAvatarState,
  });

  const handleStartCall = async () => {
    setSessionState("connecting");
    setTranscripts([]);
    setToolEvents([]);
    setSummary(null);
    try {
      await startSession();
      setSessionState("active");
    } catch {
      setSessionState("idle");
    }
  };

  const handleEndCall = async () => {
    await endSession();
    setSessionState("ended");
  };

  const handleRestart = () => {
    setSessionState("idle");
    setTranscripts([]);
    setToolEvents([]);
    setSummary(null);
  };

  return (
    <div className="min-h-screen bg-black text-white flex flex-col">
      {/* Header */}
      <header className="border-b border-[#1a1a1a] px-6 py-4 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-2 h-2 rounded-full bg-white" />
          <span className="text-sm font-semibold tracking-widest uppercase">
            City General Hospital
          </span>
        </div>
        <span className="text-xs text-[#666] tracking-wider uppercase">
          AI Receptionist
        </span>
      </header>

      <AnimatePresence mode="wait">
        {sessionState === "ended" && summary ? (
          <motion.div
            key="summary"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.4 }}
            className="flex-1 overflow-auto"
          >
            <SummaryScreen summary={summary} onRestart={handleRestart} />
          </motion.div>
        ) : (
          <motion.main
            key="main"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="flex-1 grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-0 overflow-hidden"
          >
            {/* Left: Avatar + Voice Interface */}
            <div className="flex flex-col border-r border-[#1a1a1a] overflow-hidden">
              {/* Avatar section */}
              <div className="flex-1 flex flex-col items-center justify-center p-8 relative min-h-[320px]">
                <Avatar isSpeaking={isSpeaking} sessionState={sessionState} />
              </div>

              {/* Divider */}
              <div className="border-t border-[#1a1a1a]" />

              {/* Voice Interface Controls + Transcript */}
              <div className="flex flex-col" style={{ height: "340px" }}>
                <VoiceInterface
                  sessionState={sessionState}
                  onStartCall={handleStartCall}
                  onEndCall={handleEndCall}
                />
                <div className="flex-1 overflow-hidden border-t border-[#1a1a1a]">
                  <Transcript entries={transcripts} />
                </div>
              </div>
            </div>

            {/* Right panel */}
            <div className="flex flex-col overflow-hidden">
              {/* Tool execution */}
              <div className="border-b border-[#1a1a1a]" style={{ height: "50%" }}>
                <ToolExecution events={toolEvents} sessionState={sessionState} />
              </div>

              {/* Appointments */}
              <div style={{ height: "50%" }} className="overflow-hidden">
                <AppointmentPanel
                  events={toolEvents}
                  sessionState={sessionState}
                />
              </div>
            </div>
          </motion.main>
        )}
      </AnimatePresence>
    </div>
  );
}
