import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  AlertTriangle, ArrowRight, ArrowUpRight, CalendarDays, Check, CheckCircle2, CircleDot,
  FolderKanban, LayoutGrid, Link2, ListFilter, LoaderCircle, RefreshCw, CheckSquare,
  Pencil, Plus, Search, Sparkles, Target, Trash2, UserRound, X,
} from "lucide-react";

import { createProject, deleteProject, getProjectOptions, listProjects, updateProject } from "../api/projectApi";
import { useAuth } from "../context/AuthContext";
import { canCreateProjects, canManageProjects } from "../utils/rolePermissions";
import SmoothReveal from "../components/SmoothReveal";

const COMPLETE = new Set(["completed", "complete", "done", "closed"]);
const RISK = new Set(["blocked", "delayed", "at risk", "at-risk"]);
const emptyForm = { project_name: "", project_category: "", project_description: "", project_type: "", responsible_employee_id: "", current_status: "Planning", progress_percentage: 0, current_progress_update: "", next_activity: "", target_date: "", blockers: "", related_links: "" };

function normalized(value) {
  return String(value || "").trim().toLowerCase();
}

function projectTone(status) {
  const value = normalized(status);
  if (COMPLETE.has(value)) return "bg-emerald-50 text-emerald-700 ring-emerald-200";
  if (RISK.has(value)) return "bg-rose-50 text-rose-700 ring-rose-200";
  if (["active",  "on track"].includes(value)) return "bg-blue-50 text-[#075fae] ring-blue-200";
  return "bg-slate-100 text-slate-600 ring-slate-200";
}

function formatDate(value) {
  if (!value) return "No target date";
  return new Intl.DateTimeFormat("en", { day: "numeric", month: "short", year: "numeric" }).format(new Date(`${value}T00:00:00`));
}

function safeLink(value) {
  if (!value) return null;
  const first = value.split(/[\n,]/).map((item) => item.trim()).find(Boolean);
  if (!first) return null;
  return /^https?:\/\//i.test(first) ? first : `https://${first}`;
}

function Metric({ icon: Icon, label, value, detail, tone = "blue" }) {
  const color = tone === "green" ? "bg-emerald-50 text-emerald-600" : tone === "rose" ? "bg-rose-50 text-rose-600" : "bg-blue-50 text-[#075fae]";
  return <article className="stat-card"><span className={`grid h-11 w-11 place-items-center rounded-2xl ${color}`}><Icon size={20} /></span><div><p className="text-[11px] font-extrabold uppercase tracking-[.14em] text-slate-400">{label}</p><p className="mt-1 text-2xl font-black text-[#10233f]">{value}</p><p className="mt-1 text-[11px] text-slate-400">{detail}</p></div></article>;
}

function formFromProject(project, responsibleEmployeeId) {
  if (!project) return { ...emptyForm, responsible_employee_id: responsibleEmployeeId || "" };
  return {
    ...emptyForm,
    ...project,
    responsible_employee_id: project.responsible_employee_id || "",
    progress_percentage: Number(project.progress_percentage) || 0,
    target_date: project.target_date || "",
  };
}

function ProjectForm({ initialProject, options, responsibleEmployeeId, submitting, onSubmit, onClose }) {
  const [form, setForm] = useState(() => formFromProject(initialProject, responsibleEmployeeId));
  const editing = Boolean(initialProject);
  const update = (field) => (event) => setForm((current) => ({ ...current, [field]: event.target.value }));
  const nullable = (value) => value.trim() || null;
  function submit(event) {
    event.preventDefault();
    onSubmit({
      ...form,
      project_name: form.project_name.trim(),
      project_category: nullable(form.project_category),
      project_description: nullable(form.project_description),
      project_type: nullable(form.project_type),
      responsible_employee_id: form.responsible_employee_id ? Number(form.responsible_employee_id) : null,
      progress_percentage: Number(form.progress_percentage) || 0,
      current_progress_update: nullable(form.current_progress_update),
      next_activity: nullable(form.next_activity), target_date: form.target_date || null,
      blockers: nullable(form.blockers), related_links: nullable(form.related_links),
    });
  }
  return <form className="content-card space-y-5" onSubmit={submit}>
    <div className="flex items-center justify-between"><div><p className="eyebrow text-[#0871c6]">Project workspace</p><h3 className="section-title">{editing ? "Edit project" : "Create project"}</h3></div><button type="button" className="icon-button" onClick={onClose} aria-label="Close project form"><X size={18} /></button></div>
    <div className="grid gap-4 sm:grid-cols-2">
      <label className="field-label sm:col-span-2">Project name<input className="field-input" value={form.project_name} onChange={update("project_name")} required maxLength={255} /></label>
      <label className="field-label">Category<input className="field-input" value={form.project_category} onChange={update("project_category")} placeholder="e.g. Product development" /></label>
      <label className="field-label">Type<input className="field-input" value={form.project_type} onChange={update("project_type")} placeholder="e.g. Internal" /></label>
      <label className="field-label">Responsible employee<select className="field-input" value={form.responsible_employee_id} onChange={update("responsible_employee_id")}><option value="">Select an employee</option>{options.employees.map((employee) => <option key={employee.id} value={employee.id}>{employee.name}{employee.designation ? ` - ${employee.designation}` : ""}</option>)}</select></label>
      <label className="field-label">Status<select className="field-input" value={form.current_status} onChange={update("current_status")}><option>Planning</option><option>Active</option><option>In progress</option><option>On track</option><option>At risk</option><option>Blocked</option><option>Delayed</option><option>Completed</option></select></label>
      <label className="field-label">Target date<input className="field-input" type="date" value={form.target_date} onChange={update("target_date")} /></label>
      <label className="field-label">Progress %<input className="field-input" type="number" min="0" max="100" step="0.1" value={form.progress_percentage} onChange={update("progress_percentage")} /></label>
      <label className="field-label sm:col-span-2">Description<textarea className="field-input min-h-24 resize-y" value={form.project_description} onChange={update("project_description")} placeholder="Describe the project outcome and scope." /></label>
      <label className="field-label">Current progress<textarea className="field-input min-h-24 resize-y" value={form.current_progress_update} onChange={update("current_progress_update")} /></label>
      <label className="field-label">Next activity<textarea className="field-input min-h-24 resize-y" value={form.next_activity} onChange={update("next_activity")} /></label>
      <label className="field-label">Blockers<textarea className="field-input min-h-24 resize-y" value={form.blockers} onChange={update("blockers")} /></label>
      <label className="field-label">Related links<textarea className="field-input min-h-24 resize-y" value={form.related_links} onChange={update("related_links")} placeholder="One or more project URLs" /></label>
    </div>
    <button className="primary-button w-full justify-center" disabled={submitting}>{submitting ? <LoaderCircle className="animate-spin" size={17} /> : <Check size={17} />}{submitting ? "Saving..." : editing ? "Update project" : "Save project"}</button>
  </form>;
}

function ProjectCard({ project, canManage, onEdit, onDelete, onNavigateTasks }) {
  const progress = Math.max(0, Math.min(100, Number(project.progress_percentage) || 0));
  const link = safeLink(project.related_links);
  return (
    <article
      onClick={onNavigateTasks}
      className="group flex h-full cursor-pointer flex-col rounded-[28px] border border-slate-200/80 bg-white p-5 shadow-[0_12px_40px_rgba(15,45,75,.045)] transition hover:-translate-y-1 hover:border-blue-300 hover:shadow-[0_20px_55px_rgba(15,45,75,.1)] sm:p-6"
    >
      <div className="flex items-start justify-between gap-3">
        <span className="grid h-11 w-11 place-items-center rounded-2xl bg-gradient-to-br from-[#075fae] to-[#1696c9] text-white shadow-lg shadow-blue-900/15">
          <FolderKanban size={20} />
        </span>
        <div className="flex items-center gap-2">
          {canManage && (
            <>
              <button
                type="button"
                className="icon-button"
                onClick={(e) => {
                  e.stopPropagation();
                  onEdit(project);
                }}
                aria-label={`Edit ${project.project_name}`}
              >
                <Pencil size={15} />
              </button>
              <button
                type="button"
                className="icon-button hover:border-red-200 hover:bg-red-50 hover:text-red-600"
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete(project);
                }}
                aria-label={`Delete ${project.project_name}`}
              >
                <Trash2 size={15} />
              </button>
            </>
          )}
          <span className={`rounded-full px-3 py-1 text-[10px] font-black uppercase tracking-wide ring-1 ${projectTone(project.current_status)}`}>
            {project.current_status || "Not set"}
          </span>
        </div>
      </div>
      <div className="mt-5 flex-1">
        <div className="flex flex-wrap gap-2">
          <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[10px] font-bold text-slate-500">{project.project_category || "General"}</span>
          {project.project_type && <span className="rounded-full bg-[#edf8ed] px-2.5 py-1 text-[10px] font-bold text-[#198f1b]">{project.project_type}</span>}
        </div>
        <h3 className="mt-3 text-lg font-black leading-snug text-[#10233f] group-hover:text-[#075fae] transition-colors">{project.project_name}</h3>
        <p className="mt-2 line-clamp-2 text-sm leading-6 text-slate-500">{project.project_description || "No project description has been added yet."}</p>
      </div>
      <div className="mt-6">
        <div className="flex items-center justify-between text-xs">
          <span className="font-bold text-slate-500">Delivery progress</span>
          <b className="text-[#075fae]">{Math.round(progress)}%</b>
        </div>
        <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-100">
          <div className={`h-full rounded-full ${RISK.has(normalized(project.current_status)) ? "bg-rose-500" : "bg-gradient-to-r from-[#20b51d] to-[#19a7b9]"}`} style={{ width: `${progress}%` }} />
        </div>
      </div>

      {/* Current Running Task / Stage (Management & Team Oversight) */}
      {project.current_running_stage ? (
        <div className="mt-4 rounded-2xl border border-blue-100 bg-blue-50/40 p-3.5 text-xs">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-1.5 min-w-0">
              <span className="shrink-0 rounded-md bg-[#075fae] px-1.5 py-0.5 text-[9px] font-black uppercase tracking-wider text-white">
                Seq #{project.current_running_stage.sequence_id}
              </span>
              <span className="font-extrabold text-[#10233f] truncate">
                Current task: {project.current_running_stage.tasks.length === 1
                  ? project.current_running_stage.tasks[0].task_title
                  : `Stage #${project.current_running_stage.sequence_id}`}
              </span>
            </div>
            <span className="shrink-0 text-[10px] font-bold text-slate-500">
              {project.current_running_stage.status_summary}
            </span>
          </div>

          {/* If there are multiple tasks for this sequence id (e.g. 3 tasks for id=2), show them! */}
          {project.current_running_stage.tasks && project.current_running_stage.tasks.length > 0 && (
            <div className="mt-2.5 space-y-1.5 border-t border-blue-100/70 pt-2">
              {project.current_running_stage.tasks.map((task) => (
                <div key={task.id} className="flex items-center justify-between gap-2 text-[11px]">
                  <div className="flex items-center gap-1.5 min-w-0">
                    <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${
                      COMPLETE.has(normalized(task.status))
                        ? "bg-emerald-500"
                        : ["in progress", "in-progress", "active"].includes(normalized(task.status))
                        ? "bg-blue-500 animate-pulse"
                        : "bg-slate-300"
                    }`} />
                    <span className="truncate text-slate-700 font-medium">
                      #{task.id} · {task.task_title}
                    </span>
                    {task.assigned_user_name && (
                      <span className="text-[10px] text-slate-400">· {task.assigned_user_name}</span>
                    )}
                  </div>
                  <span className={`shrink-0 rounded-full px-2 py-0.5 text-[9px] font-black uppercase ${
                    COMPLETE.has(normalized(task.status))
                      ? "bg-emerald-100 text-emerald-800"
                      : ["in progress", "in-progress", "active"].includes(normalized(task.status))
                      ? "bg-blue-100 text-blue-800"
                      : "bg-slate-100 text-slate-600"
                  }`}>
                    {task.status || "To do"}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      ) : (
        <div className="mt-4 rounded-2xl border border-slate-100 bg-slate-50/60 p-3 text-xs text-slate-400">
          <span className="font-semibold text-slate-500">Current task:</span> No tasks running
        </div>
      )}

      <div className="mt-4 grid gap-3 border-t border-slate-100 pt-4 text-xs">
        <div className="flex items-center gap-2 text-slate-500"><UserRound size={15} className="text-[#075fae]" /><span>{project.responsible_employee_name || "Unassigned"}</span></div>
        <div className="flex items-center gap-2 text-slate-500"><CalendarDays size={15} className="text-slate-400" /><span>{formatDate(project.target_date)}</span></div>
        <div className="flex items-start gap-2 text-slate-500"><Target size={15} className="mt-0.5 shrink-0 text-[#20a91e]" /><span className="line-clamp-2">{project.next_activity || "Next activity not defined"}</span></div>
        {project.blockers && <div className="flex items-start gap-2 rounded-2xl bg-rose-50 p-3 text-rose-700"><AlertTriangle size={15} className="mt-0.5 shrink-0" /><span className="line-clamp-2">{project.blockers}</span></div>}
      </div>
      <div className="mt-5 flex items-center justify-between border-t border-slate-100 pt-4 text-xs font-bold">
        <span className="inline-flex items-center gap-1.5 text-[#075fae] group-hover:text-[#0871c6]">
          <CheckSquare size={15} />
          <span>View task section</span>
          <ArrowRight size={13} className="transition group-hover:translate-x-1" />
        </span>
        {link && (
          <a
            className="inline-flex items-center gap-1.5 text-slate-400 hover:text-[#075fae]"
            href={link}
            target="_blank"
            rel="noreferrer"
            onClick={(e) => e.stopPropagation()}
          >
            <Link2 size={13} />
            <span>Resource</span>
            <ArrowUpRight size={12} />
          </a>
        )}
      </div>
    </article>
  );
}

export default function Projects() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const canCreate = canCreateProjects(user?.role);
  const canManage = canManageProjects(user?.role);
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("active");
  const [category, setCategory] = useState("all");
  const [formProject, setFormProject] = useState(undefined);
  const [options, setOptions] = useState({ employees: [] });
  const [saving, setSaving] = useState(false);

  async function load() {
    setLoading(true); setError("");
    try { setProjects(await listProjects()); } catch (requestError) { setError(requestError.message || "Unable to load projects."); } finally { setLoading(false); }
  }

  useEffect(() => { load(); if (canCreate) getProjectOptions().then(setOptions).catch((requestError) => setError(requestError.message)); }, [canCreate]);

  async function saveProject(payload) {
    setSaving(true); setError(""); setSuccess("");
    try {
      const saved = formProject ? await updateProject(formProject.id, payload) : await createProject(payload);
      const wasEditing = Boolean(formProject);
      setFormProject(undefined);
      await load();
      setSuccess(`Project “${saved.project_name}” ${wasEditing ? "updated" : "created"} successfully.`);
    }
    catch (requestError) { setError(requestError.message || `Unable to ${formProject ? "update" : "create"} project.`); }
    finally { setSaving(false); }
  }

  async function removeProject(project) {
    if (!window.confirm(`Delete ${project.project_name}? This action cannot be undone.`)) return;
    setError(""); setSuccess("");
    try {
      await deleteProject(project.id);
      setProjects((current) => current.filter((item) => item.id !== project.id));
      setSuccess(`Project “${project.project_name}” deleted successfully.`);
    } catch (requestError) {
      setError(requestError.message || "Unable to delete project.");
    }
  }

  const stats = useMemo(() => {
    const active = projects.filter((item) => ["active", "in progress", "on track"].includes(normalized(item.current_status))).length;
    const risk = projects.filter((item) => RISK.has(normalized(item.current_status)) || item.blockers).length;
    const completed = projects.filter((item) => COMPLETE.has(normalized(item.current_status))).length;
    const average = projects.length ? Math.round(projects.reduce((sum, item) => sum + Number(item.progress_percentage || 0), 0) / projects.length) : 0;
    return { active, risk, completed, average };
  }, [projects]);

  const statuses = useMemo(() => [...new Set(projects.map((item) => item.current_status).filter(Boolean))], [projects]);
  const categories = useMemo(() => [...new Set(projects.map((item) => item.project_category).filter(Boolean))], [projects]);
  const visible = useMemo(() => projects.filter((project) => {
    const matchesStatus = status === "all" || normalized(project.current_status) === normalized(status);
    const matchesCategory = category === "all" || normalized(project.project_category) === normalized(category);
    const haystack = [project.project_name, project.project_category, project.project_description, project.project_type, project.current_progress_update, project.responsible_employee_name].join(" ").toLowerCase();
    return matchesStatus && matchesCategory && haystack.includes(query.trim().toLowerCase());
  }), [projects, query, status, category]);

  const roleMessage = user?.role === "management" ? "A portfolio-wide view of delivery health, risk, and momentum." : user?.role === "employee" ? "Keep delivery moving with clear progress, targets, and next actions." : "Projects connected to your assigned work.";

  return <div className="space-y-6">
    <section className="subpage-hero"><div className="relative z-10 max-w-2xl"><div className="inline-flex items-center gap-2 rounded-full bg-[#edfbed] px-3 py-1.5 text-[10px] font-black uppercase tracking-[.15em] text-[#168f18]"><Sparkles size={13} /> {user?.role} portfolio</div><h2 className="mt-4 text-4xl font-black tracking-[-.045em] text-[#10233f] sm:text-5xl">Projects that move the lab forward.</h2><p className="mt-4 max-w-xl text-sm leading-7 text-slate-500">{roleMessage}</p>{canCreate && <button className="primary-button mt-6" onClick={() => setFormProject(null)}><Plus size={17} /> Add Project</button>}</div><div className="subpage-ring" /></section>
    {canManage && formProject !== undefined && <SmoothReveal revealKey={formProject?.id || "new-project"}><ProjectForm key={formProject?.id || "new"} initialProject={formProject} options={options} responsibleEmployeeId={user.id} submitting={saving} onSubmit={saveProject} onClose={() => setFormProject(undefined)} /></SmoothReveal>}
    {success && <div className="flex items-center justify-between rounded-2xl bg-emerald-50 px-4 py-3 text-sm font-semibold text-emerald-700" role="status"><span>{success}</span><button onClick={() => setSuccess("")} aria-label="Dismiss success message"><X size={16} /></button></div>}
    <section className="grid gap-4 sm:grid-cols-2 2xl:grid-cols-4"><Metric icon={CircleDot} label="In motion" value={stats.active} detail="Active delivery streams" /><Metric icon={AlertTriangle} label="Needs attention" value={stats.risk} detail="Blocked, delayed, or flagged" tone="rose" /><Metric icon={CheckCircle2} label="Completed" value={stats.completed} detail="Closed delivery loops" tone="green" /><Metric icon={Target} label="Portfolio progress" value={`${stats.average}%`} detail="Average across visible projects" /></section>
    <section className="content-card"><div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between"><div><p className="eyebrow text-[#0871c6]">Portfolio explorer</p><h3 className="section-title">Projects <span className="ml-2 text-sm text-slate-400">{visible.length}</span></h3></div><div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap"><label className="flex min-h-11 items-center gap-2 rounded-2xl border border-slate-200 bg-slate-50 px-4 text-slate-400 focus-within:border-blue-300 focus-within:bg-white"><Search size={16} /><input className="w-full bg-transparent text-sm text-slate-700 outline-none sm:w-48" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search projects or employees" aria-label="Search projects or employees" />{query && <button onClick={() => setQuery("")} aria-label="Clear search"><X size={14} /></button>}</label><label className="flex min-h-11 items-center gap-2 rounded-2xl border border-slate-200 bg-white px-4 text-sm font-bold text-slate-600"><ListFilter size={16} /><select className="bg-transparent outline-none" value={status} onChange={(event) => setStatus(event.target.value)} aria-label="Filter by status"><option value="all">All statuses</option><option value="active">Active</option>{statuses.filter((item) => normalized(item) !== "active").map((item) => <option key={item} value={normalized(item)}>{item}</option>)}</select></label><label className="flex min-h-11 items-center gap-2 rounded-2xl border border-slate-200 bg-white px-4 text-sm font-bold text-slate-600"><select className="bg-transparent outline-none" value={category} onChange={(event) => setCategory(event.target.value)} aria-label="Filter by category"><option value="all">All categories</option>{categories.map((item) => <option key={item}>{item}</option>)}</select></label><button className="icon-button" onClick={load} aria-label="Refresh projects"><RefreshCw size={17} /></button></div></div>
      {error && <div className="mt-5 rounded-2xl bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-700">{error}</div>}
      {loading ? <div className="flex items-center justify-center gap-2 py-20 text-sm font-semibold text-slate-400"><LoaderCircle className="animate-spin" size={19} /> Loading project portfolio...</div> : visible.length ? <div className="mt-6 grid gap-4 md:grid-cols-2 2xl:grid-cols-3">{visible.map((project) => <ProjectCard key={project.id} project={project} canManage={canManage} onEdit={setFormProject} onDelete={removeProject} onNavigateTasks={() => navigate(`/tasks?projectId=${project.id}`)} />)}</div> : <div className="py-20 text-center"><LayoutGrid className="mx-auto text-slate-300" size={38} /><p className="mt-3 font-extrabold text-slate-600">No matching projects</p><p className="mt-1 text-sm text-slate-400">Try a broader search or another status.</p></div>}
    </section>
  </div>;
}
