import { useState } from "react";
import type { UserLocation } from "../../hooks/useLocations";

const CHANNEL_OPTIONS = [
  { key: "sms",   label: "SMS",   icon: "📱" },
  { key: "push",  label: "Push",  icon: "🔔" },
  { key: "email", label: "Email", icon: "✉️" },
];

interface Props {
  location: UserLocation;
  onUpdate: (id: string, patch: Partial<UserLocation>) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
}

export default function LocationCard({ location, onUpdate, onDelete }: Props) {
  const [expanded, setExpanded] = useState(false);
  const [threshold, setThreshold] = useState(location.alert_threshold);
  const [qStart, setQStart] = useState(location.quiet_hours_start ?? "");
  const [qEnd, setQEnd] = useState(location.quiet_hours_end ?? "");
  const [channels, setChannels] = useState<string[]>(location.notify_channels);
  const [saving, setSaving] = useState(false);

  function toggleChannel(key: string) {
    setChannels(prev => prev.includes(key) ? prev.filter(c => c !== key) : [...prev, key]);
  }

  async function save() {
    setSaving(true);
    await onUpdate(location.id, {
      alert_threshold: threshold,
      quiet_hours_start: qStart || null,
      quiet_hours_end: qEnd || null,
      notify_channels: channels,
    });
    setSaving(false);
    setExpanded(false);
  }

  const labelEmoji = location.is_primary ? "🏠" : "📍";

  return (
    <div className={`bg-slate-800 rounded-2xl p-4 flex flex-col gap-3 border ${location.is_active ? "border-slate-700" : "border-slate-700/40 opacity-60"}`}>
      {/* Header row */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-xl">{labelEmoji}</span>
          <div className="min-w-0">
            <p className="text-sm font-semibold text-white truncate">{location.label ?? "Unnamed location"}</p>
            <p className="text-xs text-slate-400 font-mono">{location.h3_index.slice(0, 10)}…</p>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {location.is_primary && (
            <span className="text-xs bg-blue-900/50 text-blue-300 px-2 py-0.5 rounded-full">Primary</span>
          )}
          <button
            onClick={() => onUpdate(location.id, { is_active: !location.is_active })}
            className={`text-xs px-2 py-0.5 rounded-full border transition-colors ${location.is_active ? "border-green-700 text-green-400" : "border-slate-600 text-slate-500"}`}
          >
            {location.is_active ? "Active" : "Paused"}
          </button>
        </div>
      </div>

      {/* Summary bar */}
      <div className="flex gap-3 text-xs text-slate-400">
        <span>Alert at {Math.round(location.alert_threshold * 100)}%</span>
        <span>·</span>
        <span>
          {location.quiet_hours_start && location.quiet_hours_end
            ? `Quiet ${location.quiet_hours_start.slice(0, 5)}–${location.quiet_hours_end.slice(0, 5)}`
            : "No quiet hours"}
        </span>
        <span>·</span>
        <span>{location.notify_channels.join(", ")}</span>
      </div>

      {/* Expand toggle */}
      <button
        onClick={() => setExpanded(v => !v)}
        className="text-xs text-blue-400 hover:text-blue-300 self-start transition-colors"
      >
        {expanded ? "▲ Collapse" : "▼ Edit settings"}
      </button>

      {/* Editable settings */}
      {expanded && (
        <div className="flex flex-col gap-4 pt-1 border-t border-slate-700">
          {/* Threshold */}
          <label className="flex flex-col gap-1 text-xs text-slate-400">
            Alert threshold: <span className="text-white font-semibold">{Math.round(threshold * 100)}%</span>
            <input
              type="range" min={0.3} max={0.95} step={0.05}
              value={threshold}
              onChange={e => setThreshold(Number(e.target.value))}
              className="accent-blue-500"
            />
          </label>

          {/* Quiet hours */}
          <div className="flex flex-col gap-1">
            <p className="text-xs text-slate-400">Quiet hours (no alerts)</p>
            <div className="flex items-center gap-2">
              <input
                type="time"
                value={qStart}
                onChange={e => setQStart(e.target.value)}
                className="bg-slate-700 border border-slate-600 rounded-lg px-2 py-1 text-sm text-white outline-none focus:border-blue-500"
              />
              <span className="text-slate-400 text-xs">to</span>
              <input
                type="time"
                value={qEnd}
                onChange={e => setQEnd(e.target.value)}
                className="bg-slate-700 border border-slate-600 rounded-lg px-2 py-1 text-sm text-white outline-none focus:border-blue-500"
              />
              {(qStart || qEnd) && (
                <button onClick={() => { setQStart(""); setQEnd(""); }} className="text-xs text-slate-500 hover:text-red-400">Clear</button>
              )}
            </div>
          </div>

          {/* Channels */}
          <div className="flex flex-col gap-1">
            <p className="text-xs text-slate-400">Notification channels</p>
            <div className="flex gap-2">
              {CHANNEL_OPTIONS.map(ch => (
                <button
                  key={ch.key}
                  type="button"
                  onClick={() => toggleChannel(ch.key)}
                  className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs border transition-colors ${channels.includes(ch.key) ? "bg-blue-600 border-blue-500 text-white" : "bg-slate-700 border-slate-600 text-slate-400"}`}
                >
                  <span>{ch.icon}</span> {ch.label}
                </button>
              ))}
            </div>
          </div>

          {/* Set primary */}
          {!location.is_primary && (
            <button
              onClick={() => onUpdate(location.id, { is_primary: true })}
              className="text-xs text-blue-400 hover:text-blue-300 self-start"
            >
              Set as primary location
            </button>
          )}

          <div className="flex gap-2 mt-1">
            <button
              onClick={save}
              disabled={saving}
              className="flex-1 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-semibold py-2 rounded-xl transition-colors"
            >
              {saving ? "Saving…" : "Save"}
            </button>
            <button
              onClick={() => onDelete(location.id)}
              className="px-4 bg-red-900/50 hover:bg-red-800/60 text-red-300 text-sm rounded-xl transition-colors"
            >
              Delete
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
