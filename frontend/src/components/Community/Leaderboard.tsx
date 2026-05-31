import { useState } from "react";
import type { LeaderboardEntry } from "../../hooks/useCommunity";

const RANK_STYLE: Record<number, string> = {
  1: "bg-yellow-500 text-black font-black",
  2: "bg-slate-400 text-black font-bold",
  3: "bg-orange-700 text-white font-bold",
};

interface Props {
  entries: LeaderboardEntry[];
  onPeriodChange?: (p: "weekly" | "monthly") => void;
}

export default function Leaderboard({ entries, onPeriodChange }: Props) {
  const [period, setPeriod] = useState<"weekly" | "monthly">("weekly");

  function handlePeriod(p: "weekly" | "monthly") {
    setPeriod(p);
    onPeriodChange?.(p);
  }

  return (
    <div className="bg-slate-800 rounded-2xl p-5 flex flex-col gap-4">
      {/* Header + toggle */}
      <div className="flex items-center justify-between">
        <p className="text-xs text-slate-400 uppercase tracking-widest">Top Reporters</p>
        <div className="flex bg-slate-700 rounded-lg p-0.5 text-xs">
          {(["weekly", "monthly"] as const).map(p => (
            <button
              key={p}
              onClick={() => handlePeriod(p)}
              className={`px-3 py-1 rounded-md capitalize transition-colors ${period === p ? "bg-blue-600 text-white" : "text-slate-400"}`}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      {entries.length === 0 ? (
        <p className="text-slate-500 text-sm text-center py-6">
          No reporters yet this week — be the first! 🏆
        </p>
      ) : (
        <div className="flex flex-col gap-1">
          {entries.slice(0, 10).map(entry => (
            <div key={entry.rank} className="flex items-center gap-3 py-2 border-b border-slate-700/50 last:border-0">
              <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs shrink-0 ${RANK_STYLE[entry.rank] ?? "bg-slate-700 text-slate-300"}`}>
                {entry.rank}
              </div>

              <div className="flex-1 min-w-0">
                <p className="text-sm font-mono text-white">{entry.phone_masked}</p>
                <p className="text-xs text-slate-400">{entry.level} · {entry.streak}🔥 streak</p>
              </div>

              <div className="text-right shrink-0">
                <p className="text-sm font-bold text-yellow-400">{entry.points} pts</p>
                <p className="text-xs text-slate-500">{entry.report_count} reports</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
