"use client";

import { useEffect } from "react";
import { motion } from "framer-motion";
import { RiRefreshLine, RiAlertLine } from "react-icons/ri";

interface ErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function Error({ error, reset }: ErrorProps) {
  useEffect(() => {
    console.error("Page error:", error);
  }, [error]);

  return (
    <div className="min-h-screen bg-black text-white flex items-center justify-center p-6">
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="flex flex-col items-center gap-5 max-w-md text-center"
      >
        <div className="w-10 h-10 rounded-full border border-[#222] flex items-center justify-center">
          <RiAlertLine size={18} className="text-white" />
        </div>
        <div className="space-y-1">
          <h2 className="text-base font-semibold">Something went wrong</h2>
          <p className="text-xs text-[#555] leading-relaxed">
            {error?.message || "An unexpected error occurred."}
          </p>
        </div>
        <button
          onClick={reset}
          className="flex items-center gap-2 px-5 py-2.5 border border-[#222] rounded-full text-sm font-medium text-white hover:border-white/30 transition-colors"
        >
          <RiRefreshLine size={14} />
          Try again
        </button>
      </motion.div>
    </div>
  );
}
