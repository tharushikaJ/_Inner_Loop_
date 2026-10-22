import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  AlertCircle,
  ArrowRight,
  Calendar,
  CalendarClock,
  CheckCheck,
  Clock3,
  ClockAlert,
  Layers,
  ListTodo,
  LoaderCircle,
  RefreshCw,
  Sparkles,
  TrendingUp,
} from "lucide-react";

import { getDashboard } from "../api/dashboardApi";
import { useAuth } from "../context/AuthContext";

const DONE = new Set(["completed", "complete", "done", "closed", "approved"]);

function normalized(value) {
  return String(value || "").trim().toLowerCase();
}

function formatDate(value, includeTime = false) {
  if (!value) return "Not scheduled";
  const parsed = new Date(value.length === 10 ? `${value}T00:00:00` : value);
  return new Intl.DateTimeFormat("en", includeTime
    ? { day: "numeric", month: "short", hour: "numeric", minute: "2-digit" }
    : { day: "numeric", month: "short", year: "numeric" }).format(parsed);
}

function toneForStatus(status) {
  const value = normalized(status);
  if (DONE.has(value)) return "bg-emerald-50 text-emerald-700";
  if (["blocked", "delayed", "at risk", "at-risk"].includes(value)) return "bg-rose-50 text-rose-700";
  if (["active", "in progress", "in-progress", "on track", "scheduled"].includes(value)) return "bg-blue-50 text-[#075fae]";
  return "bg-slate-100 text-slate-600";
}

function MetricCard({ icon: Icon, label, value, detail, to, tone = "blue" }) {
  const toneClasses = tone === "green"
    ? "border-emerald-200/70 bg-emerald-50/70 text-emerald-600"
    : tone === "rose"
      ? "border-rose-200/70 bg-rose-50/70 text-rose-600"
      : "border-sky-200/70 bg-sky-50/70 text-[#075fae]";

  const content = (
    <>
      <span className={`grid h-11 w-11 shrink-0 place-items-center rounded-xl border ${toneClasses} shadow-xs transition-transform duration-200 group-hover:scale-105`}>
        <Icon size={20} strokeWidth={2} />
      </span>
      <span className="min-w-0">
        <span className="block text-[10px] font-black uppercase tracking-[.15em] text-slate-400">{label}</span>
        <strong className="mt-1 block text-2xl font-black text-[#10233f]">{value}</strong>
        <span className="mt-1 block truncate text-[11px] text-slate-400">{detail}</span>
      </span>
      {to && (
        <ArrowRight className="ml-auto text-slate-300 transition group-hover:translate-x-1 group-hover:text-[#075fae]" size={16} />
      )}
    </>
  );
  return to ? <Link className="stat-card group" to={to}>{content}</Link> : <article className="stat-card">{content}</article>;
}

function EmptyState({ icon: Icon, title, detail }) {
  return <div className="rounded-2xl border border-dashed border-slate-200 px-5 py-10 text-center"><Icon className="mx-auto text-slate-300" size={28} strokeWidth={1.75} /><p className="mt-3 text-sm font-extrabold text-slate-600">{title}</p><p className="mt-1 text-xs leading-5 text-slate-400">{detail}</p></div>;
}

function SectionHeader({ eyebrow, title, to, linkLabel }) {
  return <div className="mb-5 flex items-end justify-between gap-4"><div><p className="eyebrow text-[#0871c6]">{eyebrow}</p><h3 className="section-title">{title}</h3></div>{to && <Link className="inline-flex items-center gap-1.5 text-xs font-extrabold text-[#075fae] hover:underline" to={to}>{linkLabel}<ArrowRight size={13} /></Link>}</div>;
}

function ProjectList({ projects }) {
  if (!projects.length) return <EmptyState icon={Layers} title="No projects in your workspace" detail="Projects assigned to your role will appear here." />;
  return <div className="space-y-2">{projects.map((project) => {
    const progress = Math.max(0, Math.min(100, Number(project.progress_percentage) || 0));
    return (
      <Link
        to={`/tasks?projectId=${project.id}`}
        className="group block rounded-2xl border border-slate-100 p-4 transition hover:-translate-y-0.5 hover:border-blue-200 hover:bg-blue-50/20 hover:shadow-sm"
        key={project.id}
      >
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="truncate text-sm font-black text-[#10233f] group-hover:text-[#075fae] transition-colors">{project.project_name}</p>
            <p className="mt-1 truncate text-xs text-slate-400">{project.responsible_employee_name || project.project_category || "No responsible employee"}</p>
          </div>
          <span className={`shrink-0 rounded-full px-2.5 py-1 text-[9px] font-black uppercase ${toneForStatus(project.current_status)}`}>{project.current_status || "Not set"}</span>
        </div>
        <div className="mt-4 flex items-center justify-between text-[11px]">
          <span className="font-bold text-slate-500">Progress</span>
          <b className="text-[#075fae]">{Math.round(progress)}%</b>
        </div>
        <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-100">
          <div className="h-full rounded-full bg-gradient-to-r from-[#20b51d] to-[#0871c6]" style={{ width: `${progress}%` }} />
        </div>
        {project.current_running_stage && (
          <div className="mt-2.5 flex items-center justify-between text-[10px]">
            <span className="font-bold text-[#075fae]">
              Current: {project.current_running_stage.title}
            </span>
            <span className="text-slate-400">
              {project.current_running_stage.status_summary}
            </span>
          </div>
        )}
      </Link>
    );
  })}</div>;
}

function TaskList({ tasks, emptyTitle = "No tasks assigned" }) {
  if (!tasks.length) return <EmptyState icon={ListTodo} title={emptyTitle} detail="New assigned work will appear here automatically." />;
  return <div className="divide-y divide-slate-100">{tasks.map((task) => <div className="flex items-start gap-3 py-4 first:pt-0 last:pb-0" key={task.id}><span className={`mt-0.5 grid h-9 w-9 shrink-0 place-items-center rounded-xl ${DONE.has(normalized(task.status)) ? "bg-emerald-50 text-emerald-600" : "bg-blue-50 text-[#075fae]"}`}>{DONE.has(normalized(task.status)) ? <CheckCheck size={17} strokeWidth={2.2} /> : <Clock3 size={17} strokeWidth={2} />}</span><div className="min-w-0 flex-1"><div className="flex flex-wrap items-center justify-between gap-2"><p className="truncate text-sm font-extrabold text-[#10233f]">{task.task_title}</p><span className={`rounded-full px-2.5 py-1 text-[9px] font-black uppercase ${toneForStatus(task.status)}`}>{task.status || "To do"}</span></div><p className="mt-1 truncate text-xs text-slate-400">{task.project_name || "Independent task"}{task.assigned_user_name ? ` · ${task.assigned_user_name}` : ""}</p><div className="mt-2 flex flex-wrap gap-3 text-[10px] font-bold text-slate-400"><span>{task.priority || "Normal"} priority</span><span>{task.due_date ? `Due ${formatDate(task.due_date)}` : "No due date"}</span></div></div></div>)}</div>;
}

function submissionStatus(task) {
  return task.submission_status || (task.completion_evidence_link || task.progress_note ? "Submitted" : "Not submitted");
}

function InternTaskList({ tasks }) {
  if (!tasks.length) return <EmptyState icon={ListTodo} title="No tasks assigned" detail="New assigned work will appear here automatically." />;
  return <div className="divide-y divide-slate-100">{tasks.map((task) => {
    const submitted = submissionStatus(task) === "Submitted";
    return <div className="py-4 first:pt-0 last:pb-0" key={task.id}>
      <div className="flex items-start gap-3"><span className={`mt-0.5 grid h-9 w-9 shrink-0 place-items-center rounded-xl ${DONE.has(normalized(task.status)) ? "bg-emerald-50 text-emerald-600" : "bg-blue-50 text-[#075fae]"}`}>{DONE.has(normalized(task.status)) ? <CheckCheck size={17} strokeWidth={2.2} /> : <Clock3 size={17} strokeWidth={2} />}</span><div className="min-w-0 flex-1"><div className="flex flex-wrap items-center justify-between gap-2"><p className="truncate text-sm font-extrabold text-[#10233f]">{task.task_title}</p><span className={`rounded-full px-2.5 py-1 text-[9px] font-black uppercase ${submitted ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-700"}`}>{submissionStatus(task)}</span></div><p className="mt-1 truncate text-xs text-slate-400">{task.project_name || "Independent task"}</p><div className="mt-2 flex flex-wrap gap-3 text-[10px] font-bold text-slate-400"><span>{task.due_date ? `Due ${formatDate(task.due_date)}` : "No due date"}</span><span className={toneForStatus(task.status)}>{task.status || "To do"}</span></div></div></div>
      <div className="mt-3 rounded-2xl bg-slate-50 px-3 py-2.5 text-xs leading-5 text-slate-500"><span className="font-extrabold text-slate-600">Feedback / progress note:</span> {task.progress_note || "No feedback yet."}</div>
    </div>;
  })}</div>;
}

function MeetingList({ meetings }) {
  if (!meetings.length) return <EmptyState icon={CalendarClock} title="No upcoming meetings" detail="Scheduled meetings relevant to you will appear here." />;
  return <div className="space-y-3">{meetings.map((meeting) => <div className="flex items-center gap-3 rounded-2xl bg-slate-50 p-4" key={meeting.id}><span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-white text-[#075fae] border border-slate-100 shadow-xs"><CalendarClock size={18} strokeWidth={1.8} /></span><div className="min-w-0 flex-1"><p className="truncate text-sm font-extrabold text-[#10233f]">{meeting.meeting_title}</p><p className="mt-1 text-xs text-slate-400">{formatDate(meeting.start_datetime, true)} · {meeting.meeting_type || "Meeting"}</p></div><span className={`rounded-full px-2.5 py-1 text-[9px] font-black uppercase ${toneForStatus(meeting.status)}`}>{meeting.status || "Scheduled"}</span></div>)}</div>;
}

export default function Dashboard() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true); setError("");
    try { setData(await getDashboard()); }
    catch (requestError) { setError(requestError.message || "Unable to load the overview."); }
    finally { setLoading(false); }
  }

  useEffect(() => { load(); }, []);

  if (loading) return <div className="content-card flex items-center justify-center gap-2 py-20 text-sm font-semibold text-slate-400"><LoaderCircle className="animate-spin" size={19} /> Loading your workspace...</div>;
  if (error) return <div className="content-card border-rose-100 bg-rose-50"><AlertCircle className="text-rose-500" size={24} /><p className="mt-3 font-extrabold text-rose-800">Overview unavailable</p><p className="mt-1 text-sm text-rose-700">{error}</p><button className="secondary-button mt-5" onClick={load}><RefreshCw size={16} /> Try again</button></div>;

  const role = user?.role || data?.role;
  const firstName = String(user?.name || "").trim().split(/\s+/)[0];
  const metrics = data?.metrics || {};
  const metricCards = role === "management" ? [
    [Layers, "Active projects", metrics.active_projects, "Portfolio in motion", "/projects", "green"],
    [ListTodo, "Total tasks", metrics.total_tasks, "All delivery work", "/tasks", "blue"],
    [CheckCheck, "Completed tasks", metrics.completed_tasks, "Finished work", "/tasks", "green"],
    [ClockAlert, "Overdue tasks", metrics.overdue_tasks, "Needs attention", "/tasks", "rose"],
    [Calendar, "Upcoming meetings", metrics.upcoming_meetings, "Scheduled ahead", "/meetings", "blue"],
  ] : [
    [Layers, "Active projects", metrics.active_projects, "Your current projects", "/projects", "green"],
    [ListTodo, "Assigned tasks", metrics.total_tasks, "Your delivery queue", "/tasks", "blue"],
    [CheckCheck, "Completed tasks", metrics.completed_tasks, "Work completed", "/tasks", "green"],
    [ClockAlert, "Overdue tasks", metrics.overdue_tasks, "Needs attention", "/tasks", "rose"],
    [Calendar, "Upcoming meetings", metrics.upcoming_meetings || 0, "Relevant meetings", role === "intern" ? null : "/meetings", "blue"],
    [TrendingUp, "Average progress", `${metrics.average_progress || 0}%`, "Across visible projects", "/projects", "green"],
  ];

  return <div className="space-y-6">
    <section className="hero-panel"><div className="hero-loop hero-loop-green" aria-hidden="true" /><div className="hero-loop hero-loop-blue" aria-hidden="true" /><div className="hero-monogram" aria-hidden="true"><span className="hero-letter hero-letter-t">T</span><span className="hero-letter hero-letter-p">P</span></div><div className="relative z-10 max-w-[720px]"><div className="inline-flex items-center gap-2 rounded-full border border-[#20b51d]/20 bg-[#edfbed] px-3 py-1.5 text-[10px] font-black uppercase tracking-[.16em] text-[#168f18]"><Sparkles size={13} /> Your workspace</div><h2 className="mt-6 text-[38px] font-black leading-[1.08] tracking-[-.045em] text-[#10233f] sm:text-[52px]">Good to see you{firstName && <>, <span className="text-[#075fae]">{firstName}</span></>}.</h2><p className="mt-5 max-w-[620px] text-sm leading-7 text-slate-500 sm:text-base">Keep your projects, tasks, deadlines and team activity organized in one workspace.</p><div className="mt-7 flex flex-wrap gap-3"><Link className="primary-button" to="/projects">View projects <ArrowRight size={16} /></Link><Link className="secondary-button" to="/tasks">View tasks <ArrowRight size={16} /></Link></div></div></section>

    <section><div className="mb-4"><p className="eyebrow text-[#199d1c]">Live workspace data</p><h3 className="section-title">At a glance</h3></div><div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-6">{metricCards.map(([Icon, label, value, detail, to, tone]) => <MetricCard key={label} icon={Icon} label={label} value={value ?? 0} detail={detail} to={to} tone={tone} />)}</div></section>

    <section className="grid gap-6 xl:grid-cols-2">
      <article className="content-card"><SectionHeader eyebrow="Portfolio" title={role === "intern" ? "Assigned projects" : "Recent projects"} to="/projects" linkLabel="All projects" /><ProjectList projects={data.projects || []} /></article>
      <article className="content-card"><SectionHeader eyebrow="Delivery calendar" title="Upcoming deadlines" to="/tasks" linkLabel="Task board" /><TaskList tasks={data.upcoming_deadlines || []} emptyTitle="No upcoming deadlines" /></article>
      <article className="content-card"><SectionHeader eyebrow={role === "intern" ? "Assigned work" : "Work queue"} title={role === "management" ? "Recent tasks" : "Assigned tasks"} to="/tasks" linkLabel="All tasks" />{role === "intern" ? <InternTaskList tasks={data.tasks || []} /> : <TaskList tasks={data.tasks || []} />}</article>
      {role !== "intern" && <article className="content-card"><SectionHeader eyebrow="Team calendar" title="Upcoming meetings" to="/meetings" linkLabel="All meetings" /><MeetingList meetings={data.meetings || []} /></article>}
    </section>

    <section className="content-card"><SectionHeader eyebrow="Portfolio health" title="Project progress" to="/projects" linkLabel="Open portfolio" />{(data.projects || []).length ? <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{data.projects.map((project) => { const progress = Math.max(0, Math.min(100, Number(project.progress_percentage) || 0)); return <Link to={`/tasks?projectId=${project.id}`} className="group block rounded-2xl bg-slate-50 p-4 transition hover:-translate-y-0.5 hover:bg-blue-50/40 hover:shadow-sm" key={project.id}><div className="flex items-start justify-between gap-3"><p className="text-sm font-extrabold text-[#10233f] group-hover:text-[#075fae] transition-colors">{project.project_name}</p><b className="text-sm text-[#075fae]">{Math.round(progress)}%</b></div><div className="mt-4 h-2 overflow-hidden rounded-full bg-white"><div className="h-full rounded-full bg-gradient-to-r from-[#20b51d] to-[#0871c6]" style={{ width: `${progress}%` }} /></div><p className="mt-3 line-clamp-1 text-xs text-slate-400">{project.current_progress_update || project.next_activity || "No progress update yet"}</p></Link>; })}</div> : <EmptyState icon={TrendingUp} title="No project progress yet" detail="Progress appears as projects are assigned and updated." />}</section>
  </div>;
}
