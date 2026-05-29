import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { createSubscription, deleteSubscription, getSubscriptions } from "../services/api";
import api from "../services/api";
import { useAlertsStore } from "../store/alerts";
import { useGeolocation } from "../hooks/useGeolocation";
import { useUserStore } from "../store/user";
import { subscribeToPush, unsubscribeFromPush, isPushSubscribed } from "../services/push";

const CHANNEL_OPTIONS = [
  { key: "sms",       label: "SMS",       icon: "📱" },
  { key: "push",      label: "Push",      icon: "🔔" },
  { key: "whatsapp",  label: "WhatsApp",  icon: "💬" },
  { key: "telegram",  label: "Telegram",  icon: "✈️" },
];

export default function AlertSettingsPage() {
  const { subscriptions, setSubscriptions, addSubscription, removeSubscription } = useAlertsStore();
  const { h3Index } = useGeolocation();
  const [threshold, setThreshold] = useState(0.7);
  const [channels, setChannels] = useState<string[]>(["sms", "push"]);
  const [pushEnabled, setPushEnabled] = useState(false);
  const [pushLoading, setPushLoading] = useState(false);
  const [emailInput, setEmailInput] = useState("");
  const [emailStatus, setEmailStatus] = useState<"idle" | "sent" | "error">("idle");
  const user = useUserStore((s) => s.user);

  useEffect(() => {
    isPushSubscribed().then(setPushEnabled);
  }, []);

  async function handlePushToggle() {
    setPushLoading(true);
    try {
      if (pushEnabled) {
        await unsubscribeFromPush();
        setPushEnabled(false);
      } else {
        const ok = await subscribeToPush();
        setPushEnabled(ok);
      }
    } finally {
      setPushLoading(false);
    }
  }

  useEffect(() => {
    getSubscriptions()
      .then(({ data }) => setSubscriptions(data))
      .catch(() => {});
  }, []);

  async function handleAdd() {
    if (!h3Index) return;
    const { data } = await createSubscription({ h3_index: h3Index, threshold_probability: threshold, channels });
    addSubscription(data);
  }

  async function handleDelete(id: string) {
    await deleteSubscription(id);
    removeSubscription(id);
  }

  async function handleEmailSubscribe() {
    if (!emailInput || !h3Index) return;
    try {
      await api.post("/email/subscribe", { email: emailInput, h3_index: h3Index });
      setEmailStatus("sent");
    } catch {
      setEmailStatus("error");
    }
  }

  return (
    <div className="min-h-screen bg-slate-900 p-4 max-w-md mx-auto flex flex-col gap-4">
      <header className="flex items-center gap-3 pt-4">
        <Link to="/" className="text-slate-400 hover:text-white">←</Link>
        <h1 className="text-xl font-bold">Alert Settings</h1>
      </header>

      <div className="bg-slate-800 rounded-xl p-4 flex flex-col gap-3">
        <p className="text-sm font-semibold">Add Alert for Current Area</p>
        <label className="text-xs text-slate-400">
          Alert threshold: {Math.round(threshold * 100)}%
          <input
            type="range" min={0.3} max={0.95} step={0.05} value={threshold}
            onChange={(e) => setThreshold(Number(e.target.value))}
            className="w-full mt-1"
          />
        </label>
        <div className="flex flex-wrap gap-2">
          {CHANNEL_OPTIONS.map(({ key, label, icon }) => (
            <label key={key} className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full cursor-pointer border transition-colors ${channels.includes(key) ? "bg-blue-600 border-blue-500 text-white" : "bg-slate-700 border-slate-600 text-slate-300"}`}>
              <input
                type="checkbox"
                className="hidden"
                checked={channels.includes(key)}
                onChange={(e) => setChannels(e.target.checked ? [...channels, key] : channels.filter((x) => x !== key))}
              />
              {icon} {label}
            </label>
          ))}
        </div>
        <button onClick={handleAdd} className="bg-blue-600 hover:bg-blue-700 text-white py-2 rounded-lg text-sm font-semibold">
          Add Alert
        </button>
      </div>

      {/* Push notification toggle */}
      <div className="bg-slate-800 rounded-xl p-4 flex items-center justify-between">
        <div>
          <p className="text-sm font-semibold">Browser Push Notifications</p>
          <p className="text-xs text-slate-400 mt-0.5">
            {pushEnabled ? "You will receive push alerts in this browser" : "Enable alerts even when the app is closed"}
          </p>
        </div>
        <button
          onClick={handlePushToggle}
          disabled={pushLoading}
          aria-label={pushEnabled ? "Disable push notifications" : "Enable push notifications"}
          className={`relative w-12 h-6 rounded-full transition-colors duration-200 focus:outline-none disabled:opacity-50 ${pushEnabled ? "bg-blue-600" : "bg-slate-600"}`}
        >
          <span
            className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform duration-200 ${pushEnabled ? "translate-x-6" : "translate-x-0"}`}
          />
        </button>
      </div>

      {/* Weekly email digest */}
      <div className="bg-slate-800 rounded-xl p-4 flex flex-col gap-3">
        <div>
          <p className="text-sm font-semibold">📧 Weekly Email Digest</p>
          <p className="text-xs text-slate-400 mt-0.5">Every Monday — outages last week + predictions for the week ahead</p>
        </div>
        {emailStatus === "sent" ? (
          <p className="text-green-400 text-sm">✅ Subscribed! First digest arrives next Monday at 08:00 UTC.</p>
        ) : (
          <div className="flex gap-2">
            <input
              type="email"
              placeholder="your@email.com"
              value={emailInput}
              onChange={(e) => setEmailInput(e.target.value)}
              className="flex-1 bg-slate-700 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button
              onClick={handleEmailSubscribe}
              disabled={!emailInput || !h3Index}
              className="bg-blue-600 hover:bg-blue-700 disabled:opacity-40 text-white px-4 py-2 rounded-lg text-sm font-semibold"
            >
              Subscribe
            </button>
          </div>
        )}
        {emailStatus === "error" && <p className="text-red-400 text-xs">Failed to subscribe. Try again.</p>}
      </div>

      <div className="flex flex-col gap-2">
        {subscriptions.map((sub) => (
          <div key={sub.id} className="bg-slate-800 rounded-xl p-3 flex justify-between items-center">
            <div>
              <p className="text-sm font-mono">{sub.h3_index.slice(0, 10)}...</p>
              <p className="text-xs text-slate-400">≥{Math.round(sub.threshold_probability * 100)}% · {sub.channels.join(", ")}</p>
            </div>
            <button onClick={() => handleDelete(sub.id)} className="text-red-400 hover:text-red-300 text-sm">Remove</button>
          </div>
        ))}
      </div>
    </div>
  );
}
