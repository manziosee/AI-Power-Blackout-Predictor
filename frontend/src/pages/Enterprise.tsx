import { useState } from "react";
import { Link } from "react-router-dom";
import { useGeolocation } from "../hooks/useGeolocation";
import { useUserStore } from "../store/user";
import UtilityPortal from "../components/Enterprise/UtilityPortal";
import BusinessImpactCard from "../components/Enterprise/BusinessImpactCard";
import WebhookManager from "../components/Enterprise/WebhookManager";

type Tab = "utility" | "impact" | "webhooks";

const TABS: { key: Tab; label: string; icon: string }[] = [
  { key: "utility",  label: "Utility Portal", icon: "🏢" },
  { key: "impact",   label: "Business Impact", icon: "💰" },
  { key: "webhooks", label: "Webhooks",         icon: "🔗" },
];

export default function EnterprisePage() {
  const [tab, setTab] = useState<Tab>("utility");
  const user = useUserStore(s => s.user);
  const { h3Index } = useGeolocation();
  const countryCode = user?.country_code ?? "RW";

  return (
    <div className="min-h-screen bg-slate-900 pb-8">
      <header className="flex items-center gap-3 px-4 pt-6 pb-2">
        <Link to="/" className="text-slate-400 hover:text-white text-lg">←</Link>
        <div>
          <h1 className="text-xl font-bold">Enterprise</h1>
          <p className="text-xs text-slate-400">Utility dashboards · Business impact · IoT webhooks</p>
        </div>
      </header>

      <div className="flex mx-4 mt-3 mb-4 bg-slate-800 rounded-xl p-1 gap-1">
        {TABS.map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors flex items-center justify-center gap-1.5 ${tab === t.key ? "bg-blue-600 text-white" : "text-slate-400 hover:text-white"}`}
          >
            <span>{t.icon}</span>
            <span className="hidden sm:inline">{t.label}</span>
          </button>
        ))}
      </div>

      <div className="px-4 max-w-lg mx-auto">
        {tab === "utility"  && <UtilityPortal />}
        {tab === "impact"   && (
          h3Index
            ? <BusinessImpactCard h3_index={h3Index} country_code={countryCode} probability={0.7} duration_hours={2} />
            : <div className="bg-slate-800 rounded-2xl p-10 text-center text-slate-500 flex flex-col gap-2">
                <p className="text-4xl">📍</p>
                <p>Allow location access to calculate your business impact score.</p>
              </div>
        )}
        {tab === "webhooks" && <WebhookManager />}
      </div>
    </div>
  );
}
