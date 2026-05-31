import { useState } from "react";
import { useCalendar } from "../../hooks/useAnalytics";

const RISK_BG: Record<string, string> = {
  none:     "bg-slate-700",
  low:      "bg-green-900/60 border border-green-700",
  medium:   "bg-yellow-900/60 border border-yellow-700",
  high:     "bg-red-900/60 border border-red-700",
  critical: "bg-purple-900/60 border border-purple-700",
};

const OUTAGE_DOT: Record<number, string> = {
  0: "",
  1: "bg-orange-400",
  2: "bg-red-400",
  3: "bg-red-600",
};

interface Props { h3_index: string }

export default function OutageCalendar({ h3_index }: Props) {
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1);
  const data = useCalendar(h3_index, year, month);

  function prev() {
    if (month === 1) { setMonth(12); setYear(y => y - 1); }
    else setMonth(m => m - 1);
  }
  function next() {
    if (month === 12) { setMonth(1); setYear(y => y + 1); }
    else setMonth(m => m + 1);
  }

  const weekDays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
  const firstDay = new Date(year, month - 1, 1).getDay();
  const offset = firstDay === 0 ? 6 : firstDay - 1;  // ISO week: Mon=0

  return (
    <div className="bg-slate-800 rounded-2xl p-5 flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <p className="text-xs text-slate-400 uppercase tracking-widest">Outage Calendar</p>
        <div className="flex items-center gap-2">
          <button onClick={prev} className="text-slate-400 hover:text-white px-2 py-1 rounded" aria-label="Previous month">‹</button>
          <span className="text-sm font-semibold text-white min-w-[110px] text-center">
            {data?.month_name ?? "—"} {year}
          </span>
          <button onClick={next} className="text-slate-400 hover:text-white px-2 py-1 rounded" aria-label="Next month">›</button>
        </div>
      </div>

      {/* Summary */}
      {data && (
        <p className="text-xs text-slate-400">
          {data.total_outages > 0
            ? `${data.total_outages} confirmed outage${data.total_outages !== 1 ? "s" : ""} this month`
            : "No confirmed outages this month"}
        </p>
      )}

      {/* Grid */}
      <div className="grid grid-cols-7 gap-1 text-xs">
        {weekDays.map(d => (
          <div key={d} className="text-slate-500 text-center pb-1 font-medium">{d}</div>
        ))}

        {/* Offset cells */}
        {Array.from({ length: offset }).map((_, i) => <div key={`pad-${i}`} />)}

        {/* Day cells */}
        {(data?.days ?? []).map(day => {
          const dotColor = OUTAGE_DOT[Math.min(day.outage_count, 3)];
          const bg = day.outage_count > 0
            ? "bg-red-900/50 border border-red-700"
            : RISK_BG[day.is_future ? day.risk_level : "none"];

          const isToday = day.date === now.toISOString().slice(0, 10);

          return (
            <div
              key={day.day}
              className={`rounded-lg p-1 flex flex-col items-center min-h-[36px] relative ${bg} ${isToday ? "ring-2 ring-blue-500" : ""}`}
              title={day.outage_count > 0
                ? `${day.outage_count} outage(s), ${day.total_duration_minutes}min total`
                : day.is_future && day.max_probability > 0
                  ? `${Math.round(day.max_probability * 100)}% risk predicted`
                  : ""}
            >
              <span className={`text-xs font-medium ${isToday ? "text-blue-400" : "text-slate-300"}`}>
                {day.day}
              </span>
              {day.outage_count > 0 && dotColor && (
                <span className={`w-1.5 h-1.5 rounded-full mt-0.5 ${dotColor}`} />
              )}
              {day.is_future && day.max_probability >= 0.65 && day.outage_count === 0 && (
                <span className="text-[8px] text-yellow-400 leading-none">⚡</span>
              )}
            </div>
          );
        })}
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-3 text-xs text-slate-400 pt-1 border-t border-slate-700">
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-400 inline-block" /> Outage occurred</span>
        <span className="flex items-center gap-1"><span className="text-yellow-400">⚡</span> High risk predicted</span>
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded bg-green-900/60 border border-green-700 inline-block" /> Low risk</span>
      </div>
    </div>
  );
}
