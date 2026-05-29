import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { createSubscription, deleteSubscription, getSubscriptions } from "../services/api";
import { useAlertsStore } from "../store/alerts";
import { useGeolocation } from "../hooks/useGeolocation";

export default function AlertSettingsPage() {
  const { subscriptions, setSubscriptions, addSubscription, removeSubscription } = useAlertsStore();
  const { h3Index } = useGeolocation();
  const [threshold, setThreshold] = useState(0.7);
  const [channels, setChannels] = useState<string[]>(["sms", "push"]);

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
        <div className="flex gap-2">
          {["sms", "push", "email"].map((ch) => (
            <label key={ch} className="flex items-center gap-1 text-xs text-slate-300">
              <input
                type="checkbox" checked={channels.includes(ch)}
                onChange={(e) => setChannels(e.target.checked ? [...channels, ch] : channels.filter((x) => x !== ch))}
              />
              {ch.toUpperCase()}
            </label>
          ))}
        </div>
        <button onClick={handleAdd} className="bg-blue-600 hover:bg-blue-700 text-white py-2 rounded-lg text-sm font-semibold">
          Add Alert
        </button>
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
