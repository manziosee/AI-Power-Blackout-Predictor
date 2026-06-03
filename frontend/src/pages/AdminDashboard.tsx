import { useState } from "react";
import { Link } from "react-router-dom";
import {
  useAccuracy,
  useAdminStats,
  useAdminUsers,
  useCeleryHealth,
  useFraudFlags,
  useSmppStatus,
} from "../hooks/useAdmin";

type Tab = "overview" | "smpp" | "celery" | "fraud" | "users" | "accuracy";

const TABS: { key: Tab; label: string; icon: string }[] = [
  { key: "overview",  label: "Overview",  icon: "📊" },
  { key: "smpp",      label: "SMPP",      icon: "📡" },
  { key: "celery",    label: "Workers",   icon: "⚙️" },
  { key: "accuracy",  label: "Accuracy",  icon: "🎯" },
  { key: "fraud",     label: "Fraud",     icon: "🚨" },
  { key: "users",     label: "Users",     icon: "👥" },
];

function StatCard({ label, value, sub, color = "text-white" }: { label: string; value: string | number; sub?: string; color?: string }) {
  return (
    <div className="bg-slate-800 rounded-2xl p-4 flex flex-col gap-1">
      <p className="text-xs text-slate-400">{label}</p>
      <p className={`text-2xl font-bold ${color}`}>{value}</p>
      {sub && <p className="text-xs text-slate-500">{sub}</p>}
    </div>
  );
}

function OverviewTab() {
  const { data, loading } = useAdminStats();
  if (loading) return <p className="text-slate-500 text-center py-8">Loading…</p>;
  if (!data) return <p className="text-red-400 text-center py-8">Admin access required</p>;
  return (
    <div className="flex flex-col gap-4">
      <p className="text-xs text-slate-400 uppercase tracking-widest">Users</p>
      <div className="grid grid-cols-2 gap-3">
        <StatCard label="Total users" value={data.users.total} />
        <StatCard label="New today" value={data.users.new_today} color="text-green-400" />
        <StatCard label="New this week" value={data.users.new_week} />
        <StatCard label="New this month" value={data.users.new_month} />
      </div>

      <p className="text-xs text-slate-400 uppercase tracking-widest mt-2">SMS (last 30 days)</p>
      <div className="grid grid-cols-2 gap-3">
        <StatCard label="Total sent" value={data.sms.total_30d} />
        <StatCard label="Delivery rate" value={data.sms.delivery_rate !== null ? `${data.sms.delivery_rate}%` : "—"} color="text-blue-400" />
        <StatCard label="Delivered" value={data.sms.delivered} color="text-green-400" />
        <StatCard label="Failed" value={data.sms.failed} color={data.sms.failed > 0 ? "text-red-400" : "text-white"} />
      </div>

      <p className="text-xs text-slate-400 uppercase tracking-widest mt-2">Activity</p>
      <div className="grid grid-cols-2 gap-3">
        <StatCard label="Reports today" value={data.outages.reports_today} />
        <StatCard label="Reports this week" value={data.outages.reports_week} />
        <StatCard label="Predictions today" value={data.predictions.run_today} />
        <StatCard label="Open fraud flags" value={data.fraud.open_flags} color={data.fraud.open_flags > 0 ? "text-orange-400" : "text-white"} />
      </div>
    </div>
  );
}

function SmppTab() {
  const connectors = useSmppStatus();
  return (
    <div className="flex flex-col gap-3">
      {connectors.length === 0 && <p className="text-slate-500 text-center py-8">Loading connectors…</p>}
      {connectors.map(c => (
        <div key={c.id} className="bg-slate-800 rounded-2xl p-4 flex items-center justify-between gap-3">
          <div>
            <p className="text-sm font-semibold text-white">{c.operator}</p>
            <p className="text-xs text-slate-400">{c.country} · {c.host || "host not set"}</p>
          </div>
          <span className={`px-3 py-1 rounded-full text-xs font-semibold ${c.configured ? "bg-green-900/50 text-green-400" : "bg-red-900/50 text-red-400"}`}>
            {c.configured ? "Configured" : "Missing"}
          </span>
        </div>
      ))}
    </div>
  );
}

function CeleryTab() {
  const { data, refetch } = useCeleryHealth();
  return (
    <div className="flex flex-col gap-4">
      <div className="flex justify-end">
        <button onClick={refetch} className="text-xs bg-slate-700 hover:bg-slate-600 text-slate-300 px-3 py-1.5 rounded-lg">Refresh</button>
      </div>
      {data && (
        <>
          <div className={`rounded-2xl p-4 flex items-center gap-3 ${data.status === "ok" ? "bg-green-900/30 border border-green-700" : "bg-red-900/30 border border-red-700"}`}>
            <span className="text-2xl">{data.status === "ok" ? "✅" : "❌"}</span>
            <div>
              <p className="font-semibold text-white capitalize">{data.status.replace("_", " ")}</p>
              {data.detail && <p className="text-xs text-red-300">{data.detail}</p>}
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <StatCard label="Workers online" value={data.worker_count} color={data.worker_count > 0 ? "text-green-400" : "text-red-400"} />
            <StatCard label="Active tasks" value={data.active_tasks} />
            <StatCard label="Scheduled tasks" value={data.scheduled_tasks} />
          </div>
          {data.workers.length > 0 && (
            <div className="bg-slate-800 rounded-2xl p-4 flex flex-col gap-2">
              <p className="text-xs text-slate-400 uppercase">Workers</p>
              {data.workers.map(w => (
                <p key={w} className="text-xs font-mono text-slate-300">{w}</p>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}

const SEVERITY_COLOR: Record<string, string> = {
  high:   "bg-red-900/40 text-red-300",
  medium: "bg-orange-900/40 text-orange-300",
  low:    "bg-yellow-900/40 text-yellow-300",
};

const RULE_LABEL: Record<string, string> = {
  rate_limit:          "Rate limit exceeded",
  h3_flood:            "Cell flooding",
  coord_mismatch:      "Coordinate mismatch",
  location_impossible: "Impossible location",
};

function FraudTab() {
  const { flags, resolve } = useFraudFlags(false);
  return (
    <div className="flex flex-col gap-3">
      {flags.length === 0 && (
        <div className="bg-slate-800 rounded-2xl p-10 text-center text-slate-500 flex flex-col gap-2">
          <p className="text-3xl">✅</p>
          <p>No open fraud flags</p>
        </div>
      )}
      {flags.map(f => (
        <div key={f.id} className="bg-slate-800 rounded-2xl p-4 flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${SEVERITY_COLOR[f.severity] ?? ""}`}>{f.severity.toUpperCase()}</span>
            <span className="text-xs text-slate-500">{new Date(f.created_at).toLocaleString()}</span>
          </div>
          <p className="text-sm font-semibold text-white">{RULE_LABEL[f.rule] ?? f.rule}</p>
          {f.detail && <p className="text-xs text-slate-400">{f.detail}</p>}
          {f.user_id && <p className="text-xs text-slate-500 font-mono">User: {f.user_id}</p>}
          <button
            onClick={() => resolve(f.id)}
            className="mt-1 self-end text-xs bg-slate-700 hover:bg-green-700 text-slate-300 hover:text-white px-3 py-1 rounded-lg transition-colors"
          >
            Resolve
          </button>
        </div>
      ))}
    </div>
  );
}

function UsersTab() {
  const [search, setSearch] = useState("");
  const { users, toggleBan } = useAdminUsers(search);
  return (
    <div className="flex flex-col gap-3">
      <input
        type="text"
        placeholder="Search by phone…"
        value={search}
        onChange={e => setSearch(e.target.value)}
        className="bg-slate-700 border border-slate-600 rounded-xl px-3 py-2 text-sm text-white placeholder-slate-500 outline-none focus:border-blue-500"
      />
      {users.map(u => (
        <div key={u.id} className="bg-slate-800 rounded-2xl p-4 flex items-center justify-between gap-3">
          <div>
            <p className="text-sm font-mono text-white">{u.phone}</p>
            <p className="text-xs text-slate-400">{u.country_code} · {u.language} · joined {new Date(u.created_at).toLocaleDateString()}</p>
            <div className="flex gap-1 mt-1">
              {u.is_admin && <span className="text-xs bg-purple-900/50 text-purple-300 px-2 py-0.5 rounded">Admin</span>}
              {!u.is_active && <span className="text-xs bg-red-900/50 text-red-400 px-2 py-0.5 rounded">Banned</span>}
            </div>
          </div>
          <button
            onClick={() => toggleBan(u.id)}
            className={`text-xs px-3 py-1.5 rounded-lg transition-colors ${u.is_active ? "bg-red-900/50 hover:bg-red-800 text-red-300" : "bg-green-900/50 hover:bg-green-800 text-green-300"}`}
          >
            {u.is_active ? "Ban" : "Unban"}
          </button>
        </div>
      ))}
    </div>
  );
}

function AccuracyTab() {
  const rows = useAccuracy();
  if (rows.length === 0) return <p className="text-slate-500 text-center py-8">No accuracy data yet — needs predictions + outage history.</p>;
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs text-slate-300">
        <thead>
          <tr className="text-slate-500 border-b border-slate-700">
            <th className="text-left py-2 pr-3">Country</th>
            <th className="text-left py-2 pr-3">Regions</th>
            <th className="text-left py-2 pr-3">Accuracy</th>
            <th className="text-left py-2 pr-3">F1</th>
            <th className="text-left py-2">Predictions</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(r => (
            <tr key={r.country_code} className="border-b border-slate-700/40">
              <td className="py-2 pr-3 font-semibold text-white">{r.country_code}</td>
              <td className="py-2 pr-3">{r.regions}</td>
              <td className="py-2 pr-3">{r.avg_accuracy !== null ? `${(r.avg_accuracy * 100).toFixed(1)}%` : "—"}</td>
              <td className="py-2 pr-3">{r.avg_f1 !== null ? `${(r.avg_f1 * 100).toFixed(1)}%` : "—"}</td>
              <td className="py-2">{r.total_predictions.toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function AdminDashboard() {
  const [tab, setTab] = useState<Tab>("overview");

  return (
    <div className="min-h-screen bg-slate-900 pb-8">
      <header className="flex items-center gap-3 px-4 pt-6 pb-2">
        <Link to="/" className="text-slate-400 hover:text-white text-lg">←</Link>
        <div>
          <h1 className="text-xl font-bold">Admin Dashboard</h1>
          <p className="text-xs text-slate-400">Platform operations — internal use only</p>
        </div>
      </header>

      {/* Tab bar — scrollable on small screens */}
      <div className="flex mx-4 mt-3 mb-4 bg-slate-800 rounded-xl p-1 gap-1 overflow-x-auto">
        {TABS.map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`shrink-0 flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${tab === t.key ? "bg-blue-600 text-white" : "text-slate-400 hover:text-white"}`}
          >
            <span>{t.icon}</span>
            <span className="hidden sm:inline">{t.label}</span>
          </button>
        ))}
      </div>

      <div className="px-4 max-w-lg mx-auto">
        {tab === "overview"  && <OverviewTab />}
        {tab === "smpp"      && <SmppTab />}
        {tab === "celery"    && <CeleryTab />}
        {tab === "accuracy"  && <AccuracyTab />}
        {tab === "fraud"     && <FraudTab />}
        {tab === "users"     && <UsersTab />}
      </div>
    </div>
  );
}
