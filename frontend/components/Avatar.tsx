"use client";

import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { RiUserVoiceLine } from "react-icons/ri";

interface AvatarProps {
  isSpeaking: boolean;
  sessionState: "idle" | "connecting" | "active" | "ended";
}

const BEYOND_PRESENCE_API_KEY =
  process.env.NEXT_PUBLIC_BEYOND_PRESENCE_API_KEY || "";

export default function Avatar({ isSpeaking, sessionState }: AvatarProps) {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const [avatarReady, setAvatarReady] = useState(false);
  const [avatarSessionUrl, setAvatarSessionUrl] = useState<string | null>(null);

  // Create a Beyond Presence avatar session when the call starts
  useEffect(() => {
    if (sessionState !== "active" || !BEYOND_PRESENCE_API_KEY) {
      setAvatarSessionUrl(null);
      setAvatarReady(false);
      return;
    }

    let cancelled = false;

    async function createAvatarSession() {
      try {
        const resp = await fetch("https://api.beyondpresence.ai/v1/sessions", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${BEYOND_PRESENCE_API_KEY}`,
          },
          body: JSON.stringify({
            avatar_id: "default",
            voice_enabled: true,
          }),
        });

        if (!resp.ok) return;
        const data = await resp.json();
        if (!cancelled && data.session_url) {
          setAvatarSessionUrl(data.session_url);
        }
      } catch {
        // Avatar unavailable — fall back to animated placeholder
      }
    }

    createAvatarSession();
    return () => {
      cancelled = true;
    };
  }, [sessionState]);

  // Notify Beyond Presence avatar of speaking state changes
  useEffect(() => {
    if (!iframeRef.current || !avatarSessionUrl) return;
    try {
      iframeRef.current.contentWindow?.postMessage(
        { type: "speaking_state", speaking: isSpeaking },
        "*"
      );
    } catch {
      // Cross-origin restriction — Beyond Presence handles sync internally
    }
  }, [isSpeaking, avatarSessionUrl]);

  return (
    <div className="flex flex-col items-center gap-4 w-full">
      {/* Avatar container */}
      <motion.div
        className="relative w-48 h-48 rounded-full overflow-hidden border border-[#1a1a1a]"
        animate={{
          boxShadow: isSpeaking
            ? "0 0 0 4px rgba(255,255,255,0.08), 0 0 0 8px rgba(255,255,255,0.04)"
            : "0 0 0 0px rgba(255,255,255,0)",
        }}
        transition={{ duration: 0.3 }}
      >
        <AnimatePresence mode="wait">
          {avatarSessionUrl ? (
            <motion.div
              key="iframe"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="w-full h-full"
            >
              <iframe
                ref={iframeRef}
                src={avatarSessionUrl}
                className="w-full h-full border-0"
                allow="camera; microphone; autoplay"
                onLoad={() => setAvatarReady(true)}
              />
            </motion.div>
          ) : (
            <motion.div
              key="placeholder"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="w-full h-full bg-[#0d0d0d] flex items-center justify-center"
            >
              <AvatarPlaceholder isSpeaking={isSpeaking} sessionState={sessionState} />
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>

      {/* Speaking indicator label */}
      <AnimatePresence>
        {isSpeaking && (
          <motion.div
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 4 }}
            className="flex items-center gap-2"
          >
            <div className="flex items-center gap-[3px] h-4">
              {[1, 2, 3].map((i) => (
                <div
                  key={i}
                  className="waveform-bar w-[2px] bg-white rounded-full h-4"
                  style={{ animationDelay: `${(i - 1) * 0.15}s` }}
                />
              ))}
            </div>
            <span className="text-xs text-[#666] uppercase tracking-widest">
              Speaking
            </span>
          </motion.div>
        )}
        {!isSpeaking && sessionState === "active" && (
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="text-xs text-[#333] uppercase tracking-widest"
          >
            Listening
          </motion.p>
        )}
        {sessionState === "idle" && (
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-xs text-[#333] uppercase tracking-widest"
          >
            AI Receptionist
          </motion.p>
        )}
      </AnimatePresence>
    </div>
  );
}

function AvatarPlaceholder({
  isSpeaking,
  sessionState,
}: {
  isSpeaking: boolean;
  sessionState: string;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-3">
      <motion.div
        animate={{
          scale: isSpeaking ? [1, 1.05, 1] : 1,
        }}
        transition={{
          duration: 0.8,
          repeat: isSpeaking ? Infinity : 0,
          ease: "easeInOut",
        }}
      >
        <RiUserVoiceLine
          size={56}
          className={sessionState === "active" ? "text-white" : "text-[#222]"}
        />
      </motion.div>

      {/* Animated rings when speaking */}
      {isSpeaking && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          {[1, 2].map((i) => (
            <motion.div
              key={i}
              className="absolute rounded-full border border-white/10"
              initial={{ width: 80, height: 80, opacity: 0.6 }}
              animate={{ width: 160, height: 160, opacity: 0 }}
              transition={{
                duration: 1.8,
                repeat: Infinity,
                delay: i * 0.6,
                ease: "easeOut",
              }}
            />
          ))}
        </div>
      )}
    </div>
  );
}
