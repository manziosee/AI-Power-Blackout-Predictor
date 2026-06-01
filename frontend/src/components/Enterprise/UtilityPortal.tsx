import { useState } from "react";
import { useUtilityDashboard, useLiveOutages } from "../../hooks/useEnterprise";

const STAT_ITEMS = [
  { key: "outages_last_24h",    label: "Last 24h",       icon: "⚡" },
  { key: "active_unresolved",   label: "Active now",     icon: "🔴" },
  { key: "verified_last_7d",    label: "Verified 7d",    icon: "✅" },
  { key: "high_risk_areas_now", label: "High risk areas",icon: "⚠️" },
] as const;

function formatDuration(mins: number | null) {
  if (mins === null) return "—";
  if (mins < 60) return `${mins}m`;
  return `${(mins / 60).toFixed(1)}h`;
}

function formatTime(iso: string) {
  return new Date(iso).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

export default function UtilityPortal() {
  const [apiKey, setApiKey] = useState(localStorage.getItem("utility_api_key") ?? "");
  const [input, setInput] = useState(apiKey);
  const [hours, setHours] = useState(24);

  const { data: stats, error } = useUtilityDashboard(apiKey);
  const outages = useLiveOutages(apiKey, hours);

  function connect() {
    localStorage.setItem("utility_api_key", input);
    setApiKey(input);
  }

  return (
    <div className="flex flex-col gap-5">
      {/* API key entry */}
      <div className="bg-slate-800 rounded-2xl p-5 flex flex-col gap-3">
        <p className="text-xs text-slate-400 uppercase tracking-widest">Utility API Key</p>
        <div className="flex gap-2">
          <input
            type="password"
            value={input}
            onChange={e => setInput(e.target.value)}
            placeholder="util_xxxxxxxx"
            className="flex-1 bg-slate-700 border border-slate-600 rounded-xl px-3 py-2 text-sm text-white placeholder-slate-500 outline-none focus:border-blue-500"
            onKeyDown={e => e.key === "Enter" && connect()}
          />
          <button
            onClick={connect}
            className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold px-4 rounded-xl transition-colors"
          >
            Connect
          </button>
        </div>
        {error && <p className="text-red-400 text-xs">{error}</p>}
      </div>

      {/* Stats grid */}
      {stats && (
        <>
          <div className="flex flex-col gap-1">
            <p className="text-slate-300 font-semibold">{stats.company}</p>
            <p className="text-xs text-slate-500 uppercase">{stats.country_code} · {stats.plan} plan</p>
          </div>

          <div className="grid grid-cols-2 gap-3">
            {STAT_ITEMS.map(item => (
              <div key={item.key} className="bg-slate-800 rounded-2xl p-4 flex flex-col gap-1">
                <span className="text-2xl">{item.icon}</span>
                <p className="text-2xl font-bold text-white">{stats.stats[item.key]}</p>
                <p className="text-xs text-slate-400">{item.label}</p>
              </div>
            ))}
            <div className="bg-slate-800 rounded-2xl p-4 col-span-2 flex flex-col gap-1">
              <p className="text-xs text-slate-400">Avg outage duration (30d)</p>
              <p className="text-2xl font-bold text-white">{formatDuration(stats.stats.avg_duration_minutes)}</p>
            </div>
          </div>

          {/* Live outage table */}
          <div className="bg-slate-800 rounded-2xl p-5 flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <p className="text-xs text-slate-400 uppercase tracking-widest">Live Outages</p>
              <select
                value={hours}
                onChange={e => setHours(Number(e.target.value))}
                className="bg-slate-700 border border-slate-600 rounded-lg px-2 py-1 text-xs text-white"
              >
                <option value={6}>6h</option>
                <option value={24}>24h</option>
                <option value={48}>48h</option>
              </select>
            </div>

            {outages.length === 0 ? (
              <p className="text-slate-500 text-sm text-center py-4">No outages in this window</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-xs text-slate-300">
                  <thead>
                    <tr className="text-slate-500 border-b border-slate-700">
                      <th className="text-left py-2 pr-3">Area</th>
                      <th className="text-left py-2 pr-3">Reported</th>
                      <th className="text-left py-2 pr-3">Duration</th>
                      <th className="text-left py-2 pr-3">Confirms</th>
                      <th className="text-left py-2">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {outages.map(o => (
                      <tr key={o.id} className="border-b border-slate-700/40 hover:bg-slate-700/30">
                        <td className="py-2 pr-3 font-mono text-slate-400">
                          {o.lat !== null && o.lng !== null
                            ? `${o.lat.toFixed(4)}, ${o.lng.toFixed(4)}`
                            : o.h3_index.slice(0, 8) + "…"}
                        </td>
                        <td className="py-2 pr-3">{formatTime(o.reported_at)}</td>
                        <td className="py-2 pr-3">{formatDuration(o.duration_minutes)}</td>
                        <td className="py-2 pr-3">{o.verification_count}</td>
                        <td className="py-2">
                          <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${o.resolved_at ? "bg-green-900/50 text-green-400" : "bg-red-900/50 text-red-400"}`}>
                            {o.resolved_at ? "Resolved" : "Active"}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}

      {!apiKey && (
        <div className="bg-slate-800 rounded-2xl p-10 text-center text-slate-500 flex flex-col gap-2">
          <p className="text-4xl">🏢</p>
          <p className="font-semibold text-slate-400">Utility Company Portal</p>
          <p className="text-sm">Enter your API key to see crowd-reported outages before your call center does.</p>
        </div>
      )}
    </div>
  );
}
