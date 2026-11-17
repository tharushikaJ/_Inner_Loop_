import { Link } from "react-router-dom";

export default function Brand({ compact = false, to = "/dashboard" }) {
  return (
    <Link to={to} className="group flex items-center gap-3" aria-label="InnerLoop home">
      <span className="relative block h-11 w-11 shrink-0" aria-hidden="true">
        <svg viewBox="0 0 44 44" className="h-11 w-11 transition duration-300 group-hover:scale-105">
          <path d="M12 12 32 22 12 32" fill="none" stroke="#075fae" strokeLinecap="round" strokeLinejoin="round" strokeWidth="3.5" />
          <circle cx="12" cy="12" r="6.5" fill="#087bd1" />
          <circle cx="32" cy="22" r="6.5" fill="#20b51d" />
          <circle cx="12" cy="32" r="6.5" fill="#075fae" />
          <circle cx="12" cy="12" r="2" fill="white" />
          <circle cx="32" cy="22" r="2" fill="white" />
          <circle cx="12" cy="32" r="2" fill="white" />
        </svg>
      </span>
      {!compact && (
        <span className="leading-none">
          <span className="block text-[22px] font-extrabold tracking-[-0.055em] text-[#075fae]">INNER<span className="text-[#20b51d]">LOOP</span></span>
          <span className="mt-1 block text-[9px] font-bold uppercase tracking-[0.33em] text-slate-500">The connection</span>
        </span>
      )}
    </Link>
  );
}
