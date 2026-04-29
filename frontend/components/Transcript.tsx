"use client";

import { useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { RiUserLine, RiRobot2Line } from "react-icons/ri";
import type { TranscriptEntry } from "@/lib/types";

interface TranscriptProps {
  entries: TranscriptEntry[];
}

export default function Transcript({ entries }: TranscriptProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [entries]);

  return (
    <div className="h-full flex flex-col bg-black">
      {/* Header */}
      <div className="px-4 py-2.5 border-b border-[#111] shrink-0">
        <p className="text-[10px] font-semibold uppercase tracking-widest text-[#333]">
          Live Transcript
        </p>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-2">
        <AnimatePresence initial={false}>
          {entries.length === 0 ? (
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-xs text-[#222] text-center pt-4"
            >
              Conversation will appear here
            </motion.p>
          ) : (
            entries.map((entry, idx) => (
              <motion.div
                key={idx}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.25 }}
                className={`flex gap-2 ${
                  entry.role === "user" ? "flex-row-reverse" : "flex-row"
                }`}
              >
                {/* Icon */}
                <div
                  className={`shrink-0 w-5 h-5 rounded-full border flex items-center justify-center mt-0.5 ${
                    entry.role === "user"
                      ? "border-[#222] text-[#444]"
                      : "border-white/20 text-white/60"
                  }`}
                >
                  {entry.role === "user" ? (
                    <RiUserLine size={10} />
                  ) : (
                    <RiRobot2Line size={10} />
                  )}
                </div>

                {/* Bubble */}
                <div
                  className={`max-w-[78%] px-3 py-1.5 rounded-xl text-xs leading-relaxed ${
                    entry.role === "user"
                      ? "bg-[#111] text-[#ccc] border border-[#1a1a1a]"
                      : "bg-white text-black"
                  }`}
                >
                  {entry.text}
                </div>
              </motion.div>
            ))
          )}
        </AnimatePresence>
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
