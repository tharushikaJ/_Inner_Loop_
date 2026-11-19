import { Link } from "react-router-dom";

export default function Brand({ compact = false, to = "/dashboard" }) {
  return (
    <Link to={to} className="group flex items-center gap-3" aria-label="InnerLoop home">
      <span className="relative block h-12 w-12 shrink-0 overflow-hidden" aria-hidden="true">
        <img
          src="/innerloop-logo.svg"
          alt=""
          className="h-full w-full object-contain transition duration-300 group-hover:scale-105"
        />
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
