import { useState } from "react";
import { ArrowRight, Eye, EyeOff, LoaderCircle, ShieldCheck } from "lucide-react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";

import Brand from "../components/Brand";
import { useAuth } from "../context/AuthContext";
import { startMicrosoftLogin } from "../utils/microsoftAuth";

function MicrosoftLogo() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className="h-[18px] w-[18px]">
      <path fill="#f35325" d="M1 1h10.5v10.5H1z" />
      <path fill="#81bc06" d="M12.5 1H23v10.5H12.5z" />
      <path fill="#05a6f0" d="M1 12.5h10.5V23H1z" />
      <path fill="#ffba08" d="M12.5 12.5H23V23H12.5z" />
    </svg>
  );
}

export default function Login() {
  const { isAuthenticated, loading: authLoading, login, authError, clearAuthError } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [form, setForm] = useState({ email: "", password: "" });
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(location.state?.error || authError || "");
  const [microsoftSubmitting, setMicrosoftSubmitting] = useState(false);

  if (authLoading) {
    return (
      <main className="auth-page">
        <div className="login-loop login-loop-one" aria-hidden="true" />
        <div className="login-loop login-loop-two" aria-hidden="true" />
        <section className="auth-card" aria-live="polite">
          <div className="flex flex-col items-center gap-4 py-12 text-center">
            <LoaderCircle size={32} className="animate-spin text-[#075fae]" />
            <p className="text-sm font-semibold text-slate-600">Checking your session…</p>
          </div>
        </section>
      </main>
    );
  }

  if (isAuthenticated) return <Navigate to="/dashboard" replace />;

  const update = (event) => {
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }));
    setError("");
    clearAuthError?.();
  };

  const submit = async (event) => {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      await login({ ...form, email: form.email.trim().toLowerCase() });
      navigate(location.state?.from?.pathname || "/dashboard", { replace: true });
    } catch (requestError) {
      setError(requestError.message || "Invalid email or password.");
    } finally {
      setSubmitting(false);
    }
  };

  const submitMicrosoft = async () => {
    setMicrosoftSubmitting(true);
    setError("");
    clearAuthError?.();
    try {
      // loginRedirect navigates the page away – the browser will not return
      // here. The spinner stays visible until the navigation completes.
      await startMicrosoftLogin();
    } catch (requestError) {
      setError(requestError.message || "Microsoft sign-in failed.");
      setMicrosoftSubmitting(false);
    }
  };

  return (
    <main className="auth-page">
      <div className="login-loop login-loop-one" aria-hidden="true" />
      <div className="login-loop login-loop-two" aria-hidden="true" />
      <section className="auth-card" aria-labelledby="login-title">
        <Brand to="/login" />
        <div className="mt-9">
          <div className="mb-4 inline-flex items-center gap-2 rounded-full bg-[#edf8ff] px-3 py-1.5 text-[10px] font-extrabold uppercase tracking-[.15em] text-[#075fae]"><ShieldCheck size={14} /> Secure workspace</div>
          <h1 id="login-title" className="text-3xl font-black tracking-[-0.035em] text-[#10233f]">Welcome back.</h1>
          <p className="mt-2 text-sm leading-6 text-slate-500">Sign in to continue to your InnerLoop workspace.</p>
        </div>
        {location.state?.message && <div className="auth-success" role="status">{location.state.message}</div>}
        {error && <div className="auth-error" role="alert">{error}</div>}
        <form className="mt-6 space-y-4" onSubmit={submit} noValidate>
          <label className="field-label">Email<input name="email" type="email" autoComplete="email" value={form.email} onChange={update} className="field-input" placeholder="name@example.com" required /></label>
          <label className="field-label">Password<span className="relative block"><input name="password" type={showPassword ? "text" : "password"} autoComplete="current-password" value={form.password} onChange={update} className="field-input pr-12" placeholder="Enter your password" required /><button type="button" onClick={() => setShowPassword((value) => !value)} className="password-toggle" aria-label={showPassword ? "Hide password" : "Show password"}>{showPassword ? <EyeOff size={18} /> : <Eye size={18} />}</button></span></label>
          <button type="submit" disabled={submitting || authLoading} className="primary-button w-full justify-center disabled:cursor-not-allowed disabled:opacity-60">{submitting ? <><LoaderCircle size={18} className="animate-spin" /> Signing in…</> : <>Login <ArrowRight size={17} /></>}</button>
        </form>
        <div className="my-5 flex items-center gap-3 text-xs text-slate-400"><span className="h-px flex-1 bg-slate-200" />or<span className="h-px flex-1 bg-slate-200" /></div>
        <button type="button" onClick={submitMicrosoft} disabled={submitting || microsoftSubmitting || authLoading} className="secondary-button w-full justify-center disabled:cursor-not-allowed disabled:opacity-60">
          {microsoftSubmitting ? <><LoaderCircle size={18} className="animate-spin" /> Connecting to Microsoft…</> : <><MicrosoftLogo /> Continue with Microsoft</>}
        </button>
        <p className="mt-3 text-center text-xs font-medium text-slate-500">Employees and management sign in with Microsoft.</p>
        <p className="mt-7 text-center text-sm text-slate-500">New to InnerLoop? <Link to="/register" className="font-extrabold text-[#075fae] hover:underline">Register</Link></p>
      </section>
    </main>
  );
}
