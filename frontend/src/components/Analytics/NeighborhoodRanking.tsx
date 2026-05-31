import type { RankingEntry, CellRank } from "../../hooks/useAnalytics";

const RANK_BADGE: Record<number, string> = {
  1: "bg-yellow-500 text-black",
  2: "bg-slate-400 text-black",
  3: "bg-orange-700 text-white",
};

interface Props {
  rankings: RankingEntry[];
  userRank: CellRank | null;
}

export default function NeighborhoodRanking({ rankings, userRank }: Props) {
  return (
    <div className="bg-slate-800 rounded-2xl p-5 flex flex-col gap-4">
      <div className="flex justify-between items-center">
        <p className="text-xs text-slate-400 uppercase tracking-widest">Most Affected Areas</p>
        {userRank?.rank_in_country && (
          <span className="text-xs text-blue-400 font-semibold bg-blue-900/40 px-2 py-1 rounded-full">
            Your area: #{userRank.rank_in_country} of {userRank.total_ranked_cells}
          </span>
        )}
      </div>

      {/* User's own rank callout */}
      {userRank && userRank.rank_in_country && (
        <div className="bg-blue-900/30 border border-blue-700 rounded-xl px-4 py-3 flex justify-between items-center">
          <div>
            <p className="text-sm font-semibold text-white">{userRank.city}</p>
            <p className="text-xs text-slate-400">{userRank.outages_30d} outages last 30 days</p>
          </div>
          <div className="text-right">
            <p className="text-2xl font-black text-blue-400">#{userRank.rank_in_country}</p>
            {userRank.percentile !== null && (
              <p className="text-xs text-slate-400">top {100 - userRank.percentile}%</p>
            )}
          </div>
        </div>
      )}

      {/* Leaderboard */}
      <div className="flex flex-col gap-1">
        {rankings.slice(0, 10).map((entry) => (
          <div key={entry.h3_index} className="flex items-center gap-3 py-2 border-b border-slate-700/50 last:border-0">
            <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold shrink-0 ${RANK_BADGE[entry.rank] ?? "bg-slate-700 text-slate-300"}`}>
              {entry.rank}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-white truncate">{entry.city || entry.h3_index.slice(0, 10) + "…"}</p>
              <p className="text-xs text-slate-400">{entry.outages_7d} this week · {entry.outages_30d} this month</p>
            </div>
            <div className="text-right shrink-0">
              {entry.avg_duration_minutes && (
                <p className="text-xs text-slate-400">~{Math.round(entry.avg_duration_minutes / 60)}h avg</p>
              )}
            </div>
          </div>
        ))}

        {rankings.length === 0 && (
          <p className="text-slate-500 text-sm text-center py-6">
            No ranking data yet — stats refresh daily at 03:00 UTC.
          </p>
        )}
      </div>
    </div>
  );
}
