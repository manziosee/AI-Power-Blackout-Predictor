import { useState } from "react";
import { useWebhooks } from "../../hooks/useEnterprise";
import api from "../../services/api";

const EVENT_OPTIONS = [
  { key: "outage.predicted", label: "Outage predicted" },
  { key: "outage.confirmed", label: "Outage confirmed" },
  { key: "outage.resolved",  label: "Outage resolved"  },
];

interface CreateForm {
  h3_index: string;
  url: string;
  threshold_probability: number;
  events: string[];
}

const DEFAULT_FORM: CreateForm = {
  h3_index: "",
  url: "",
  threshold_probability: 0.7,
  events: ["outage.predicted"],
};

export default function WebhookManager() {
  const { subs, create, remove, test, refetch } = useWebhooks();
  const [form, setForm] = useState<CreateForm>(DEFAULT_FORM);
  const [creating, setCreating] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [feedback, setFeedback] = useState<{ id: string; msg: string } | null>(null);
  const [events, setEvents] = useState<Record<string, { success: boolean; fired_at: string; response_status: number | null }[]>>({});

  function toggleEvent(key: string) {
    setForm(f => ({
      ...f,
      events: f.events.includes(key) ? f.events.filter(e => e !== key) : [...f.events, key],
    }));
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!form.url || !form.h3_index || form.events.length === 0) return;
    setCreating(true);
    try {
      await create(form);
      setForm(DEFAULT_FORM);
      setShowForm(false);
    } catch {}
    setCreating(false);
  }

  async function handleTest(id: string) {
    try {
      const result = await test(id);
      setFeedback({ id, msg: result.success ? "Test delivered ✓" : `Failed: ${result.error ?? "unknown"}` });
    } catch {
      setFeedback({ id, msg: "Request failed" });
    }
    setTimeout(() => setFeedback(null), 4000);
  }

  async function loadEvents(id: string) {
    if (events[id]) { setEvents(prev => { const n = { ...prev }; delete n[id]; return n; }); return; }
    const { data } = await api.get(`/webhooks/${id}/events`);
    setEvents(prev => ({ ...prev, [id]: data }));
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <p className="text-xs text-slate-400 uppercase tracking-widest">Webhook Subscriptions</p>
        <button
          onClick={() => setShowForm(v => !v)}
          className="text-xs bg-blue-600 hover:bg-blue-700 text-white px-3 py-1.5 rounded-lg transition-colors"
        >
          {showForm ? "Cancel" : "+ Add"}
        </button>
      </div>

      {/* Create form */}
      {showForm && (
        <form onSubmit={handleCreate} className="bg-slate-800 rounded-2xl p-5 flex flex-col gap-3">
          <p className="text-sm font-semibold text-white">New Webhook</p>

          <label className="flex flex-col gap-1 text-xs text-slate-400">
            H3 area index
            <input
              type="text"
              value={form.h3_index}
              onChange={e => setForm(f => ({ ...f, h3_index: e.target.value }))}
              placeholder="8928308280fffff"
              required
              className="bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 outline-none focus:border-blue-500"
            />
          </label>

          <label className="flex flex-col gap-1 text-xs text-slate-400">
            Target URL
            <input
              type="url"
              value={form.url}
              onChange={e => setForm(f => ({ ...f, url: e.target.value }))}
              placeholder="https://your-server.com/hook"
              required
              className="bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 outline-none focus:border-blue-500"
            />
          </label>

          <label className="flex flex-col gap-1 text-xs text-slate-400">
            Probability threshold: {Math.round(form.threshold_probability * 100)}%
            <input
              type="range"
              min={0.3} max={0.95} step={0.05}
              value={form.threshold_probability}
              onChange={e => setForm(f => ({ ...f, threshold_probability: Number(e.target.value) }))}
              className="accent-blue-500"
            />
          </label>

          <div className="flex flex-col gap-1">
            <p className="text-xs text-slate-400">Events to subscribe</p>
            <div className="flex gap-2 flex-wrap">
              {EVENT_OPTIONS.map(ev => (
                <button
                  key={ev.key}
                  type="button"
                  onClick={() => toggleEvent(ev.key)}
                  className={`px-3 py-1 rounded-lg text-xs border transition-colors ${form.events.includes(ev.key) ? "bg-blue-600 border-blue-500 text-white" : "bg-slate-700 border-slate-600 text-slate-400"}`}
                >
                  {ev.label}
                </button>
              ))}
            </div>
          </div>

          <button
            type="submit"
            disabled={creating}
            className="bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white font-semibold py-2 rounded-xl text-sm transition-colors"
          >
            {creating ? "Creating…" : "Create Webhook"}
          </button>
        </form>
      )}

      {/* Subscription list */}
      {subs.length === 0 ? (
        <div className="bg-slate-800 rounded-2xl p-8 text-center text-slate-500 flex flex-col gap-2">
          <p className="text-3xl">🔗</p>
          <p className="text-sm">No webhooks yet. Add one to trigger smart home hubs or generators when an outage is predicted.</p>
        </div>
      ) : (
        subs.map(sub => (
          <div key={sub.id} className="bg-slate-800 rounded-2xl p-4 flex flex-col gap-3">
            <div className="flex items-start justify-between gap-2">
              <div className="flex flex-col gap-0.5 min-w-0">
                <p className="text-sm font-mono text-blue-400 truncate">{sub.url}</p>
                <p className="text-xs text-slate-500">Area: {sub.h3_index.slice(0, 10)}… · threshold {Math.round(sub.threshold_probability * 100)}%</p>
                <div className="flex gap-1 flex-wrap mt-1">
                  {sub.events.map(ev => (
                    <span key={ev} className="text-xs bg-slate-700 text-slate-300 px-2 py-0.5 rounded">{ev}</span>
                  ))}
                </div>
              </div>
              <span className={`shrink-0 text-xs px-2 py-0.5 rounded-full ${sub.is_active ? "bg-green-900/50 text-green-400" : "bg-slate-700 text-slate-500"}`}>
                {sub.is_active ? "Active" : "Paused"}
              </span>
            </div>

            {sub.last_triggered_at && (
              <p className="text-xs text-slate-500">
                Last triggered: {new Date(sub.last_triggered_at).toLocaleString()}
              </p>
            )}

            {feedback?.id === sub.id && (
              <p className={`text-xs ${feedback.msg.includes("✓") ? "text-green-400" : "text-red-400"}`}>{feedback.msg}</p>
            )}

            {/* Recent events */}
            {events[sub.id] && (
              <div className="flex flex-col gap-1">
                <p className="text-xs text-slate-500 uppercase">Recent deliveries</p>
                {events[sub.id].slice(0, 5).map((ev, i) => (
                  <div key={i} className={`flex justify-between text-xs px-2 py-1 rounded ${ev.success ? "bg-green-900/20 text-green-400" : "bg-red-900/20 text-red-400"}`}>
                    <span>{ev.fired_at ? new Date(ev.fired_at).toLocaleTimeString() : "—"}</span>
                    <span>{ev.success ? `HTTP ${ev.response_status}` : "Failed"}</span>
                  </div>
                ))}
              </div>
            )}

            <div className="flex gap-2">
              <button
                onClick={() => handleTest(sub.id)}
                className="flex-1 bg-slate-700 hover:bg-slate-600 text-slate-200 text-xs py-1.5 rounded-lg transition-colors"
              >
                Test
              </button>
              <button
                onClick={() => loadEvents(sub.id)}
                className="flex-1 bg-slate-700 hover:bg-slate-600 text-slate-200 text-xs py-1.5 rounded-lg transition-colors"
              >
                {events[sub.id] ? "Hide logs" : "View logs"}
              </button>
              <button
                onClick={() => remove(sub.id)}
                className="flex-1 bg-red-900/50 hover:bg-red-800/60 text-red-300 text-xs py-1.5 rounded-lg transition-colors"
              >
                Delete
              </button>
            </div>
          </div>
        ))
      )}
    </div>
  );
}
