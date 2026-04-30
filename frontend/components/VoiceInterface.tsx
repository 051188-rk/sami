"use client";

import { motion } from "framer-motion";
import { RiMicLine, RiPhoneLine, RiLoader4Line } from "react-icons/ri";

interface VoiceInterfaceProps {
  sessionState: "idle" | "connecting" | "active" | "ended";
  onStartCall: () => void;
  onEndCall: () => void;
}

export default function VoiceInterface({
  sessionState,
  onStartCall,
  onEndCall,
}: VoiceInterfaceProps) {
  return (
    <div className="flex items-center justify-between px-6 py-4 bg-black">
      {/* Status indicator */}
      <div className="flex items-center gap-3">
        <StatusDot state={sessionState} />
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-white">
            {sessionState === "idle" && "Ready"}
            {sessionState === "connecting" && "Connecting"}
            {sessionState === "active" && "Live"}
            {sessionState === "ended" && "Ended"}
          </p>
          <p className="text-[11px] text-[#555] mt-0.5">
            {sessionState === "idle" && "Start a call to speak with the AI receptionist"}
            {sessionState === "connecting" && "Establishing secure voice connection..."}
            {sessionState === "active" && "Listening — speak clearly"}
            {sessionState === "ended" && "Session complete"}
          </p>
        </div>
      </div>

      {/* Waveform (active only) */}
      {sessionState === "active" && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="flex items-center gap-[3px] h-8"
        >
          {[1, 2, 3, 4, 5].map((i) => (
            <div
              key={i}
              className="waveform-bar w-[3px] bg-white rounded-full"
              style={{
                height: `${16 + Math.random() * 14}px`,
                animationDelay: `${(i - 1) * 0.1}s`,
              }}
            />
          ))}
        </motion.div>
      )}

      {/* Mic icon (idle) */}
      {sessionState === "idle" && (
        <div className="text-[#333]">
          <RiMicLine size={20} />
        </div>
      )}

      {/* Call button */}
      <CallButton
        sessionState={sessionState}
        onStart={onStartCall}
        onEnd={onEndCall}
      />
    </div>
  );
}

function StatusDot({ state }: { state: string }) {
  return (
    <div className="relative w-3 h-3">
      <div
        className={`w-3 h-3 rounded-full ${
          state === "active"
            ? "bg-white"
            : state === "connecting"
            ? "bg-[#666]"
            : "bg-[#222]"
        }`}
      />
      {state === "active" && (
        <div className="ping-slow absolute inset-0 rounded-full bg-white" />
      )}
    </div>
  );
}

function CallButton({
  sessionState,
  onStart,
  onEnd,
}: {
  sessionState: string;
  onStart: () => void;
  onEnd: () => void;
}) {
  if (sessionState === "connecting") {
    return (
      <button
        disabled
        className="flex items-center gap-2 px-5 py-2.5 border border-[#222] rounded-full text-sm font-medium text-[#555] cursor-not-allowed"
      >
        <RiLoader4Line className="animate-spin" size={16} />
        Connecting
      </button>
    );
  }

  if (sessionState === "active") {
    return (
      <motion.button
        whileTap={{ scale: 0.95 }}
        onClick={onEnd}
        className="flex items-center gap-2 px-5 py-2.5 bg-red-600 text-white rounded-full text-sm font-semibold hover:bg-red-700 transition-colors"
      >
        <RiPhoneLine size={16} />
        End Call
      </motion.button>
    );
  }

  return (
    <motion.button
      whileTap={{ scale: 0.95 }}
      whileHover={{ scale: 1.02 }}
      onClick={onStart}
      className="flex items-center gap-2 px-5 py-2.5 bg-white text-black rounded-full text-sm font-semibold hover:bg-[#ddd] transition-colors"
    >
      <RiPhoneLine size={16} />
      Start Call
    </motion.button>
  );
}
