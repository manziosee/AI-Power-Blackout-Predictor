import { useState } from "react";
import api from "../../services/api";
import type { ImpactScore } from "../../hooks/useEnterprise";

const BUSINESS_TYPES = [
  { key: "shop",       label: "Retail Shop",         icon: "🏪" },
  { key: "restaurant", label: "Restaurant",           icon: "🍽️" },
  { key: "office",     label: "Office",               icon: "🏢" },
  { key: "factory",    label: "Factory",              icon: "🏭" },
  { key: "hospital",   label: "Hospital / Clinic",    icon: "🏥" },
  { key: "other",      label: "Other",                icon: "💼" },
];

interface Props {
  h3_index: string;
  country_code: string;
  probability: number;
  duration_hours: number;
}

export default function BusinessImpactCard({ h3_index, country_code, probability, duration_hours }: Props) {
  const [type, setType] = useState("shop");
  const [result, setResult] = useState<ImpactScore | null>(null);
  const [loading, setLoading] = useState(false);

  async function estimate() {
    setLoading(true);
    try {
      const { data } = await api.get("/business/impact/estimate", {
        params: { business_type: type, country_code, duration_hours, probability },
      });
      setResult(data);
    } catch {}
    setLoading(false);
  }

  const riskColor = result
    ? result.expected_loss_usd >= 100 ? "text-red-400"
    : result.expected_loss_usd >= 30  ? "text-yellow-400"
    : "text-green-400"
    : "text-slate-400";

  return (
    <div className="bg-slate-800 rounded-2xl p-5 flex flex-col gap-4">
      <p className="text-xs text-slate-400 uppercase tracking-widest">Business Impact Score</p>

      {/* Type selector */}
      <div className="grid grid-cols-3 gap-2">
        {BUSINESS_TYPES.map(bt => (
          <button
            key={bt.key}
            onClick={() => setType(bt.key)}
            className={`flex flex-col items-center gap-1 py-2 rounded-xl text-xs transition-colors border ${type === bt.key ? "bg-blue-600 border-blue-500 text-white" : "bg-slate-700 border-slate-600 text-slate-400"}`}
          >
            <span className="text-lg">{bt.icon}</span>
            <span>{bt.label}</span>
          </button>
        ))}
      </div>

      <button
        onClick={estimate}
        disabled={loading}
        className="bg-orange-600 hover:bg-orange-700 disabled:opacity-50 text-white font-bold py-2.5 rounded-xl transition-colors"
      >
        {loading ? "Calculating..." : "Calculate Impact"}
      </button>

      {result && (
        <div className="flex flex-col gap-3">
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div className="bg-slate-700 rounded-xl p-3">
              <p className="text-slate-400 text-xs">Direct loss</p>
              <p className={`text-xl font-bold ${riskColor}`}>${result.direct_loss_usd}</p>
            </div>
            <div className="bg-slate-700 rounded-xl p-3">
              <p className="text-slate-400 text-xs">Expected loss</p>
              <p className={`text-xl font-bold ${riskColor}`}>${result.expected_loss_usd}</p>
            </div>
            <div className="bg-slate-700 rounded-xl p-3 col-span-2">
              <p className="text-slate-400 text-xs">Monthly risk exposure</p>
              <p className="text-lg font-bold text-white">${result.monthly_risk_usd}/month</p>
            </div>
          </div>

          <div className="bg-orange-900/30 border border-orange-700 rounded-xl p-3 text-xs text-orange-200">
            {result.recommendation}
          </div>

          <p className="text-xs text-slate-500 text-center">
            Based on {result.income_group ?? "regional"} average rates · {result.duration_hours}h at {Math.round(result.probability * 100)}% probability
          </p>
        </div>
      )}
    </div>
  );
}
