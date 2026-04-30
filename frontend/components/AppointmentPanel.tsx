"use client";

import { useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { RiCalendarLine, RiTimeLine, RiUserLine, RiCloseLine, RiCheckLine } from "react-icons/ri";
import type { ToolEvent, AppointmentData } from "@/lib/types";

interface AppointmentPanelProps {
  events: ToolEvent[];
  sessionState: "idle" | "connecting" | "active" | "ended";
}

export default function AppointmentPanel({ events, sessionState }: AppointmentPanelProps) {
  // Extract appointment data from tool events
  const appointments = useMemo<AppointmentData[]>(() => {
    const all: AppointmentData[] = [];

    for (const event of events) {
      if (!event.data) continue;

      // From book_appointment success
      if (
        event.tool === "book_appointment" &&
        event.status === "complete" &&
        event.success &&
        event.data?.appointment_id
      ) {
        const d = event.data as Record<string, string | number>;
        all.push({
          id: d.appointment_id as number,
          doctor: d.doctor as string,
          date: d.date as string,
          time: d.time as string,
          status: "confirmed",
        });
      }

      // From retrieve_appointments
      if (
        event.tool === "retrieve_appointments" &&
        event.data?.appointments
      ) {
        for (const a of event.data.appointments as AppointmentData[]) {
          if (!all.find((x) => x.id === a.id)) {
            all.push(a);
          }
        }
      }

      // Update status on cancel
      if (event.tool === "cancel_appointment" && event.success) {
        const apptId = event.data?.appointment_id as number | undefined;
        if (apptId) {
          const found = all.find((a) => a.id === apptId);
          if (found) found.status = "cancelled";
        }
      }
    }

    return all;
  }, [events]);

  return (
    <div className="h-full flex flex-col bg-black">
      {/* Header */}
      <div className="px-4 py-2.5 border-b border-[#111] shrink-0 flex items-center justify-between">
        <p className="text-[10px] font-semibold uppercase tracking-widest text-[#333]">
          Appointments
        </p>
        {appointments.length > 0 && (
          <span className="text-[10px] font-medium text-[#444] bg-[#111] px-2 py-0.5 rounded-full border border-[#1a1a1a]">
            {appointments.length}
          </span>
        )}
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-2">
        <AnimatePresence initial={false}>
          {appointments.length === 0 ? (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex flex-col items-center gap-2 pt-6"
            >
              <RiCalendarLine size={20} className="text-[#1a1a1a]" />
              <p className="text-xs text-[#222] text-center">
                {sessionState === "idle"
                  ? "Your appointments will appear here"
                  : "No appointments yet"}
              </p>
            </motion.div>
          ) : (
            appointments.map((appt, idx) => (
              <motion.div
                key={appt.id ?? idx}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.25 }}
                className={`p-3 rounded-lg border ${
                  appt.status === "cancelled"
                    ? "border-[#111] bg-[#050505] opacity-50"
                    : "border-[#1a1a1a] bg-[#0a0a0a]"
                }`}
              >
                {/* Doctor + status */}
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2 min-w-0">
                    <div className="shrink-0 w-5 h-5 rounded border border-[#1a1a1a] flex items-center justify-center">
                      <RiUserLine size={10} className="text-[#555]" />
                    </div>
                    <p className="text-xs font-medium text-white truncate">
                      {appt.doctor}
                    </p>
                  </div>
                  <StatusBadge status={appt.status} />
                </div>

                {/* Specialization */}
                {appt.specialization && (
                  <p className="text-[11px] text-[#333] mt-1 ml-7">
                    {appt.specialization}
                  </p>
                )}

                {/* Date & Time */}
                <div className="flex items-center gap-3 mt-2 ml-7">
                  <div className="flex items-center gap-1">
                    <RiCalendarLine size={11} className="text-[#333]" />
                    <span className="text-[11px] text-[#555]">{appt.date}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <RiTimeLine size={11} className="text-[#333]" />
                    <span className="text-[11px] text-[#555]">{appt.time}</span>
                  </div>
                </div>
              </motion.div>
            ))
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  if (status === "confirmed") {
    return (
      <div className="flex items-center gap-1 shrink-0">
        <RiCheckLine size={10} className="text-white/50" />
        <span className="text-[10px] text-white/40 uppercase tracking-wider">
          Confirmed
        </span>
      </div>
    );
  }
  return (
    <div className="flex items-center gap-1 shrink-0">
      <RiCloseLine size={10} className="text-[#333]" />
      <span className="text-[10px] text-[#333] uppercase tracking-wider">
        Cancelled
      </span>
    </div>
  );
}
