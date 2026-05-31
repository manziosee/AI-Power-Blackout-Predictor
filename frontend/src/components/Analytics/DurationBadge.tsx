import type { DurationPrediction } from "../../hooks/useAnalytics";

const CONFIDENCE_COLOR = { low: "text-slate-400", medium: "text-yellow-400", high: "text-green-400" };

interface Props { data: DurationPrediction | null }

export default function DurationBadge({ data }: Props) {
  if (!data) return (
    <div className="bg-slate-800 rounded-2xl p-5 animate-pulse h-28" />
  );

  return (
    <div className="bg-slate-800 rounded-2xl p-5 flex flex-col gap-3">
      <div className="flex justify-between items-start">
        <p className="text-xs text-slate-400 uppercase tracking-widest">Expected Duration</p>
        <span className={`text-xs font-semibold ${CONFIDENCE_COLOR[data.confidence]}`}>
          {data.confidence} confidence
        </span>
      </div>

      <p className="text-3xl font-bold text-white">{data.label}</p>

      {/* Range bar */}
      <div className="flex items-center gap-2 text-xs text-slate-400">
        <span>{data.min_minutes}m</span>
        <div className="flex-1 bg-slate-700 rounded-full h-2 relative">
          <div className="absolute inset-y-0 bg-blue-500 rounded-full" style={{
            left: "0%",
            right: `${100 - Math.min(100, (data.max_minutes / 360) * 100)}%`,
          }} />
          <div className="absolute inset-y-0 w-2 h-2 bg-white rounded-full top-0" style={{
            left: `${Math.min(96, (data.median_minutes / 360) * 100)}%`,
          }} />
        </div>
        <span>{Math.floor(data.max_minutes / 60)}h</span>
      </div>

      <p className="text-xs text-slate-500">
        Based on {data.sample_size} historical outage{data.sample_size !== 1 ? "s" : ""} in this area
      </p>
    </div>
  );
}
