"use client";

import { motion, AnimatePresence } from "framer-motion";
import {
  RiLoader4Line,
  RiCheckLine,
  RiCloseLine,
  RiUserSearchLine,
  RiCalendarCheckLine,
  RiCalendarLine,
  RiCalendarCloseLine,
  RiEditLine,
  RiStopCircleLine,
  RiSearchLine,
} from "react-icons/ri";
import type { ToolEvent } from "@/lib/types";

interface ToolExecutionProps {
  events: ToolEvent[];
  sessionState: "idle" | "connecting" | "active" | "ended";
}

const TOOL_CONFIG: Record<
  string,
  { label: string; icon: React.ElementType }
> = {
  identify_user: { label: "Identifying Patient", icon: RiUserSearchLine },
  fetch_slots: { label: "Fetching Available Slots", icon: RiSearchLine },
  book_appointment: { label: "Booking Appointment", icon: RiCalendarCheckLine },
  retrieve_appointments: { label: "Loading Appointments", icon: RiCalendarLine },
  cancel_appointment: { label: "Cancelling Appointment", icon: RiCalendarCloseLine },
  modify_appointment: { label: "Rescheduling Appointment", icon: RiEditLine },
  end_conversation: { label: "Generating Summary", icon: RiStopCircleLine },
};

export default function ToolExecution({ events, sessionState }: ToolExecutionProps) {
  return (
    <div className="h-full flex flex-col bg-black">
      {/* Header */}
      <div className="px-4 py-2.5 border-b border-[#111] shrink-0 flex items-center justify-between">
        <p className="text-[10px] font-semibold uppercase tracking-widest text-[#333]">
          Tool Execution
        </p>
        {events.some((e) => e.status === "running") && (
          <RiLoader4Line size={12} className="text-white animate-spin" />
        )}
      </div>

      {/* Events list */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-2">
        <AnimatePresence initial={false}>
          {events.length === 0 ? (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex flex-col items-center gap-2 pt-6"
            >
              <div className="w-8 h-8 rounded-full border border-[#111] flex items-center justify-center">
                <RiCalendarLine size={16} className="text-[#222]" />
              </div>
              <p className="text-xs text-[#222] text-center">
                {sessionState === "idle"
                  ? "Tool actions will appear here during the call"
                  : "Waiting for actions..."}
              </p>
            </motion.div>
          ) : (
            events.map((event, idx) => (
              <ToolEventRow key={idx} event={event} />
            ))
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

function ToolEventRow({ event }: { event: ToolEvent }) {
  const config = TOOL_CONFIG[event.tool] ?? {
    label: event.tool,
    icon: RiCalendarLine,
  };
  const Icon = config.icon;

  return (
    <motion.div
      initial={{ opacity: 0, x: 12 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.25 }}
      className={`flex items-start gap-3 p-3 rounded-lg border ${
        event.status === "running"
          ? "border-[#1a1a1a] bg-[#0a0a0a]"
          : event.status === "complete" && event.success
          ? "border-[#1a1a1a] bg-[#080808]"
          : "border-[#1a1a1a] bg-[#080808]"
      }`}
    >
      {/* Tool icon */}
      <div
        className={`shrink-0 w-7 h-7 rounded-md flex items-center justify-center border ${
          event.status === "running"
            ? "border-white/20 text-white"
            : event.success
            ? "border-white/10 text-white/70"
            : "border-[#222] text-[#444]"
        }`}
      >
        <Icon size={14} />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between gap-2">
          <p
            className={`text-xs font-medium truncate ${
              event.status === "running" ? "text-white" : "text-[#666]"
            }`}
          >
            {config.label}
          </p>
          <StatusIcon status={event.status} success={event.success} />
        </div>
        <p
          className={`text-[11px] mt-0.5 leading-snug ${
            event.status === "running" ? "text-[#555]" : "text-[#333]"
          }`}
        >
          {event.label}
        </p>
      </div>
    </motion.div>
  );
}

function StatusIcon({
  status,
  success,
}: {
  status: "running" | "complete";
  success?: boolean;
}) {
  if (status === "running") {
    return <RiLoader4Line size={12} className="text-white animate-spin shrink-0" />;
  }
  if (success) {
    return (
      <div className="shrink-0 w-4 h-4 rounded-full bg-white/10 flex items-center justify-center">
        <RiCheckLine size={10} className="text-white" />
      </div>
    );
  }
  return (
    <div className="shrink-0 w-4 h-4 rounded-full bg-[#111] flex items-center justify-center">
      <RiCloseLine size={10} className="text-[#444]" />
    </div>
  );
}
