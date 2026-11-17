import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { LoaderCircle } from "lucide-react";

import Brand from "../components/Brand";
import { useAuth } from "../context/AuthContext";

/**
 * MicrosoftCallback
 *
 * Landing page for Azure AD redirect URI (http://localhost:3000/auth/callback).
 * AuthContext handles token extraction and the backend exchange on mount.
 * When complete, this navigates to /dashboard if authenticated, or displays the
 * error message if the sign-in failed.
 */
export default function MicrosoftCallback() {
  const { isAuthenticated, loading, authError, clearAuthError } = useAuth();
  const navigate = useNavigate();
  useEffect(() => {
    if (loading || !isAuthenticated) return undefined;
    navigate("/dashboard", { replace: true });
    return undefined;
  }, [loading, isAuthenticated, navigate]);

  if (!loading && (authError || !isAuthenticated)) {
    return (
      <main className="auth-page">
        <div className="login-loop login-loop-one" aria-hidden="true" />
        <div className="login-loop login-loop-two" aria-hidden="true" />
        <section className="auth-card" aria-labelledby="callback-title">
          <Brand to="/login" />
          <div className="mt-9">
            <h1 id="callback-title" className="text-2xl font-black tracking-[-0.035em] text-[#10233f]">
              Sign-in failed
            </h1>
            <div className="auth-error mt-4" role="alert">
              {authError || "Unable to complete Microsoft sign-in."}
            </div>
            <button
              type="button"
              onClick={() => {
                clearAuthError();
                navigate("/login", { replace: true });
              }}
              className="primary-button mt-5 w-full justify-center"
            >
              Back to login
            </button>
          </div>
        </section>
      </main>
    );
  }

  return (
    <main className="auth-page">
      <div className="login-loop login-loop-one" aria-hidden="true" />
      <div className="login-loop login-loop-two" aria-hidden="true" />
      <section className="auth-card" aria-labelledby="callback-title">
        <Brand to="/login" />
        <div className="mt-9 flex flex-col items-center gap-4 py-6 text-center">
          <LoaderCircle size={32} className="animate-spin text-[#075fae]" />
          <p id="callback-title" className="text-sm font-semibold text-slate-600">
            Completing Microsoft sign-in…
          </p>
        </div>
      </section>
    </main>
  );
}
