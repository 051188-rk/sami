"use client";

import { motion } from "framer-motion";
import {
  RiUserLine,
  RiPhoneLine,
  RiCalendarLine,
  RiTimeLine,
  RiRefreshLine,
  RiCheckLine,
  RiCloseLine,
} from "react-icons/ri";
import type { SessionSummary } from "@/lib/types";

interface SummaryScreenProps {
  summary: SessionSummary;
  onRestart: () => void;
}

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.08 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 16 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.4 } },
};

export default function SummaryScreen({ summary, onRestart }: SummaryScreenProps) {
  const formattedTime = summary.timestamp
    ? new Date(summary.timestamp).toLocaleString("en-US", {
        dateStyle: "medium",
        timeStyle: "short",
      })
    : "";

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="min-h-full bg-black px-6 py-10 flex flex-col items-center"
    >
      <div className="w-full max-w-2xl space-y-6">
        {/* Header */}
        <motion.div variants={itemVariants} className="text-center space-y-1">
          <div className="w-10 h-10 rounded-full border border-[#1a1a1a] flex items-center justify-center mx-auto mb-4">
            <RiCheckLine size={18} className="text-white" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight">Call Summary</h1>
          {formattedTime && (
            <p className="text-xs text-[#444] uppercase tracking-widest">{formattedTime}</p>
          )}
        </motion.div>

        {/* Summary text */}
        <motion.div
          variants={itemVariants}
          className="border border-[#1a1a1a] rounded-xl p-5 bg-[#080808]"
        >
          <p className="text-xs text-[#444] uppercase tracking-widest mb-2">Summary</p>
          <p className="text-sm text-[#aaa] leading-relaxed">
            {summary.summary_text || "Session completed successfully."}
          </p>
        </motion.div>

        {/* Patient details */}
        {summary.user_details && (
          <motion.div
            variants={itemVariants}
            className="border border-[#1a1a1a] rounded-xl p-5 bg-[#080808]"
          >
            <p className="text-xs text-[#444] uppercase tracking-widest mb-3">Patient</p>
            <div className="space-y-2">
              {summary.user_details.name && (
                <DetailRow
                  icon={RiUserLine}
                  label="Name"
                  value={summary.user_details.name}
                />
              )}
              {summary.user_details.phone && (
                <DetailRow
                  icon={RiPhoneLine}
                  label="Phone"
                  value={summary.user_details.phone}
                />
              )}
            </div>
          </motion.div>
        )}

        {/* Appointments */}
        {summary.appointments && summary.appointments.length > 0 && (
          <motion.div
            variants={itemVariants}
            className="border border-[#1a1a1a] rounded-xl p-5 bg-[#080808]"
          >
            <p className="text-xs text-[#444] uppercase tracking-widest mb-3">
              Appointments ({summary.appointments.length})
            </p>
            <div className="space-y-3">
              {summary.appointments.map((appt, idx) => (
                <div
                  key={idx}
                  className={`p-3 rounded-lg border ${
                    appt.status === "cancelled"
                      ? "border-[#111] opacity-50"
                      : "border-[#1a1a1a]"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-medium">{appt.doctor}</p>
                    <div className="flex items-center gap-1">
                      {appt.status === "confirmed" ? (
                        <RiCheckLine size={12} className="text-white/50" />
                      ) : (
                        <RiCloseLine size={12} className="text-[#333]" />
                      )}
                      <span className="text-[10px] text-[#444] uppercase tracking-wider">
                        {appt.status}
                      </span>
                    </div>
                  </div>
                  {appt.specialization && (
                    <p className="text-xs text-[#333] mt-0.5">{appt.specialization}</p>
                  )}
                  <div className="flex items-center gap-4 mt-2">
                    <div className="flex items-center gap-1.5">
                      <RiCalendarLine size={11} className="text-[#333]" />
                      <span className="text-xs text-[#555]">{appt.date}</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <RiTimeLine size={11} className="text-[#333]" />
                      <span className="text-xs text-[#555]">{appt.time}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        )}

        {/* Preferences */}
        {summary.preferences &&
          Object.keys(summary.preferences).length > 0 && (
            <motion.div
              variants={itemVariants}
              className="border border-[#1a1a1a] rounded-xl p-5 bg-[#080808]"
            >
              <p className="text-xs text-[#444] uppercase tracking-widest mb-3">
                Noted Preferences
              </p>
              <div className="space-y-1.5">
                {Object.entries(summary.preferences).map(([key, value]) =>
                  value ? (
                    <div key={key} className="flex items-center justify-between">
                      <span className="text-xs text-[#444] capitalize">
                        {key.replace(/_/g, " ")}
                      </span>
                      <span className="text-xs text-[#888]">{value}</span>
                    </div>
                  ) : null
                )}
              </div>
            </motion.div>
          )}

        {/* Restart button */}
        <motion.div variants={itemVariants} className="flex justify-center pt-2">
          <button
            onClick={onRestart}
            className="flex items-center gap-2 px-6 py-3 border border-[#222] rounded-full text-sm font-medium text-white hover:border-white/30 transition-colors"
          >
            <RiRefreshLine size={14} />
            Start New Session
          </button>
        </motion.div>
      </div>
    </motion.div>
  );
}

function DetailRow({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ElementType;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-center gap-3">
      <div className="w-6 h-6 rounded border border-[#1a1a1a] flex items-center justify-center shrink-0">
        <Icon size={11} className="text-[#444]" />
      </div>
      <div className="flex items-center gap-2 min-w-0">
        <span className="text-xs text-[#333] w-10 shrink-0">{label}</span>
        <span className="text-xs text-[#aaa] truncate">{value}</span>
      </div>
    </div>
  );
}
