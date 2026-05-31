import type { AccuracyMetrics } from "../../hooks/useAnalytics";

const GRADE_COLOR: Record<string, string> = {
  A: "text-green-400", B: "text-blue-400", C: "text-yellow-400",
  D: "text-orange-400", F: "text-red-400", "N/A": "text-slate-500",
};

interface Props { data: AccuracyMetrics | null }

export default function AccuracyCard({ data }: Props) {
  if (!data) return <div className="bg-slate-800 rounded-2xl p-5 animate-pulse h-40" />;

  const pct = data.accuracy_pct;

  return (
    <div className="bg-slate-800 rounded-2xl p-5 flex flex-col gap-4">
      <p className="text-xs text-slate-400 uppercase tracking-widest">Prediction Accuracy</p>

      <div className="flex items-end gap-4">
        <span className={`text-5xl font-black ${GRADE_COLOR[data.grade]}`}>{data.grade}</span>
        <div className="flex flex-col pb-1">
          <span className="text-2xl font-bold text-white">
            {pct !== null ? `${pct}%` : "—"}
          </span>
          <span className="text-xs text-slate-400">last {data.period_days} days</span>
        </div>
      </div>

      {/* Confusion matrix mini */}
      {data.total_predictions > 0 && (
        <div className="grid grid-cols-2 gap-2 text-xs">
          <div className="bg-green-900/40 rounded-lg p-2 text-center">
            <p className="text-green-400 font-bold text-lg">{data.true_positives}</p>
            <p className="text-slate-400">Correct alerts</p>
          </div>
          <div className="bg-red-900/40 rounded-lg p-2 text-center">
            <p className="text-red-400 font-bold text-lg">{data.false_positives}</p>
            <p className="text-slate-400">False alarms</p>
          </div>
          <div className="bg-slate-700/40 rounded-lg p-2 text-center">
            <p className="text-slate-300 font-bold text-lg">{data.true_negatives}</p>
            <p className="text-slate-400">Correct silence</p>
          </div>
          <div className="bg-yellow-900/40 rounded-lg p-2 text-center">
            <p className="text-yellow-400 font-bold text-lg">{data.false_negatives}</p>
            <p className="text-slate-400">Missed outages</p>
          </div>
        </div>
      )}

      <p className="text-xs text-slate-400 italic">{data.verdict}</p>
    </div>
  );
}
