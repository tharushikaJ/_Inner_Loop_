import { useEffect, useState } from "react";
import { ArrowRight, Eye, EyeOff, LoaderCircle, RefreshCw, UserPlus } from "lucide-react";
import { Link, Navigate, useNavigate } from "react-router-dom";

import { authApi } from "../api/authApi";
import Brand from "../components/Brand";
import { useAuth } from "../context/AuthContext";

const initialForm = { role: "intern", name: "", email: "", password: "", confirmPassword: "", designation: "", department: "", assigned_supervisor_id: "" };
const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function validate(form) {
  const errors = {};
  if (!form.role) errors.role = "Role is required.";
  if (!form.name.trim()) errors.name = "Full name is required.";
  if (!emailPattern.test(form.email.trim())) errors.email = "Enter a valid email address.";
  if (!form.password) errors.password = "Password is required.";
  else if (form.password.length < 8) errors.password = "Password must contain at least 8 characters.";
  else if (new TextEncoder().encode(form.password).length > 72) errors.password = "Password must be at most 72 bytes.";
  if (form.confirmPassword !== form.password) errors.confirmPassword = "Passwords do not match.";
  if (form.role !== "intern" && !form.designation.trim()) errors.designation = "Designation is required for employees and management.";
  if (form.role !== "intern" && !form.department.trim()) errors.department = "Department is required for employees and management.";
  return errors;
}

function FieldError({ message }) {
  return message ? <span className="mt-1.5 block text-[11px] font-semibold text-red-600">{message}</span> : null;
}

export default function Register() {
  const { isAuthenticated, loading: authLoading, register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState(initialForm);
  const [errors, setErrors] = useState({});
  const [apiError, setApiError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [showPasswords, setShowPasswords] = useState(false);
  const [supervisors, setSupervisors] = useState([]);
  const [supervisorsLoading, setSupervisorsLoading] = useState(true);
  const [supervisorsError, setSupervisorsError] = useState("");
  const [supervisorReload, setSupervisorReload] = useState(0);

  useEffect(() => {
    if (form.role !== "intern") return undefined;
    let active = true;
    setSupervisorsLoading(true);
    setSupervisorsError("");
    authApi.supervisors()
      .then((items) => { if (active) setSupervisors(items); })
      .catch((error) => { if (active) { setSupervisors([]); setSupervisorsError(error.message || "Unable to load supervisors."); } })
      .finally(() => { if (active) setSupervisorsLoading(false); });
    return () => { active = false; };
  }, [form.role, supervisorReload]);

  if (!authLoading && isAuthenticated) return <Navigate to="/dashboard" replace />;

  const update = (event) => {
    const { name, value } = event.target;
    setForm((current) => {
      if (name !== "role") return { ...current, [name]: value };
      if (value === "intern") return { ...current, role: value, designation: "", department: "", assigned_supervisor_id: "" };
      return { ...current, role: value, assigned_supervisor_id: "" };
    });
    setErrors((current) => ({ ...current, [name]: "" }));
    setApiError("");
  };

  const submit = async (event) => {
    event.preventDefault();
    const nextErrors = validate(form);
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length) return;

    const payload = {
      role: form.role,
      name: form.name.trim(),
      email: form.email.trim().toLowerCase(),
      password: form.password,
      ...(form.role === "intern"
        ? { assigned_supervisor_id: form.assigned_supervisor_id ? Number(form.assigned_supervisor_id) : null }
        : { designation: form.designation.trim(), department: form.department.trim() }),
    };
    setSubmitting(true);
    try {
      const result = await register(payload);
      navigate("/login", { replace: true, state: { message: result.message } });
    } catch (requestError) {
      setApiError(requestError.message || "Registration could not be completed.");
    } finally {
      setSubmitting(false);
    }
  };

  const employeeFields = form.role === "management";
  return (
    <main className="auth-page py-8 sm:py-12">
      <div className="login-loop login-loop-one" aria-hidden="true" />
      <div className="login-loop login-loop-two" aria-hidden="true" />
      <section className="auth-card max-w-[560px]" aria-labelledby="register-title">
        <Brand to="/register" />
        <div className="mt-8">
          <div className="mb-4 inline-flex items-center gap-2 rounded-full bg-[#edfbed] px-3 py-1.5 text-[10px] font-extrabold uppercase tracking-[.15em] text-[#168f18]"><UserPlus size={14} /> Join InnerLoop</div>
          <h1 id="register-title" className="text-3xl font-black tracking-[-0.035em] text-[#10233f]">Create your account.</h1>
          <p className="mt-2 text-sm leading-6 text-slate-500">Choose your role and tell us how you connect with the Digital Lab.</p>
        </div>
        {apiError && <div className="auth-error" role="alert">{apiError}</div>}
        <form className="mt-6 grid gap-4 sm:grid-cols-2" onSubmit={submit} noValidate>
          <label className="field-label sm:col-span-2">Role<select name="role" value={form.role} onChange={update} className="field-input" aria-invalid={Boolean(errors.role)}><option value="intern">Intern</option><option value="management">Management</option></select><FieldError message={errors.role} /></label>
          {form.role === "intern" && <label className="field-label sm:col-span-2">Assigned Supervisor<select name="assigned_supervisor_id" value={form.assigned_supervisor_id} onChange={update} className="field-input" disabled={supervisorsLoading || Boolean(supervisorsError)}><option value="">{supervisorsLoading ? "Loading supervisors…" : "Not Assigned"}</option>{supervisors.map((supervisor) => <option key={supervisor.id} value={supervisor.id}>{supervisor.name}</option>)}</select>{!supervisorsLoading && !supervisorsError && supervisors.length === 0 && <span className="mt-1.5 block text-[11px] font-semibold text-slate-400">No active employees are available.</span>}{supervisorsError && <span className="mt-1.5 flex items-center justify-between gap-3 text-[11px] font-semibold text-red-600" role="alert"><span>{supervisorsError}</span><button type="button" onClick={() => setSupervisorReload((value) => value + 1)} className="inline-flex items-center gap-1 text-[#075fae]"><RefreshCw size={12} /> Retry</button></span>}</label>}
          <label className="field-label sm:col-span-2">Full Name<input name="name" value={form.name} onChange={update} className="field-input" autoComplete="name" placeholder="Your full name" aria-invalid={Boolean(errors.name)} /><FieldError message={errors.name} /></label>
          <label className="field-label sm:col-span-2">Email<input name="email" type="email" value={form.email} onChange={update} className="field-input" autoComplete="email" placeholder="name@example.com" aria-invalid={Boolean(errors.email)} /><FieldError message={errors.email} /></label>
          <label className="field-label">Password<span className="relative block"><input name="password" type={showPasswords ? "text" : "password"} value={form.password} onChange={update} className="field-input pr-12" autoComplete="new-password" placeholder="At least 8 characters" aria-invalid={Boolean(errors.password)} /><button type="button" onClick={() => setShowPasswords((value) => !value)} className="password-toggle" aria-label={showPasswords ? "Hide passwords" : "Show passwords"}>{showPasswords ? <EyeOff size={18} /> : <Eye size={18} />}</button></span><FieldError message={errors.password} /></label>
          <label className="field-label">Confirm Password<input name="confirmPassword" type={showPasswords ? "text" : "password"} value={form.confirmPassword} onChange={update} className="field-input" autoComplete="new-password" placeholder="Repeat password" aria-invalid={Boolean(errors.confirmPassword)} /><FieldError message={errors.confirmPassword} /></label>
          {employeeFields && <><label className="field-label">Designation<input name="designation" value={form.designation} onChange={update} className="field-input" placeholder="e.g. Software Engineer" aria-invalid={Boolean(errors.designation)} /><FieldError message={errors.designation} /></label><label className="field-label">Department<input name="department" value={form.department} onChange={update} className="field-input" placeholder="e.g. Digital Lab" aria-invalid={Boolean(errors.department)} /><FieldError message={errors.department} /></label></>}
          <button type="submit" disabled={submitting} className="primary-button mt-2 w-full justify-center disabled:cursor-not-allowed disabled:opacity-60 sm:col-span-2">{submitting ? <><LoaderCircle size={18} className="animate-spin" /> Creating account…</> : <>Register <ArrowRight size={17} /></>}</button>
        </form>
        <p className="mt-7 text-center text-sm text-slate-500">Already have an account? <Link to="/login" className="font-extrabold text-[#075fae] hover:underline">Login</Link></p>
      </section>
    </main>
  );
}
