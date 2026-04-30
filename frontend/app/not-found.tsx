import { RiArrowLeftLine } from "react-icons/ri";
import Link from "next/link";

export default function NotFound() {
  return (
    <div className="min-h-screen bg-black text-white flex items-center justify-center p-6">
      <div className="flex flex-col items-center gap-4 text-center">
        <p className="text-xs text-[#333] uppercase tracking-widest">404</p>
        <h1 className="text-xl font-semibold">Page not found</h1>
        <Link
          href="/"
          className="flex items-center gap-2 text-sm text-[#555] hover:text-white transition-colors"
        >
          <RiArrowLeftLine size={14} />
          Back to home
        </Link>
      </div>
    </div>
  );
}
