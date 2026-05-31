import type { UserStats } from "../../hooks/useCommunity";

interface Props { stats: UserStats }

export default function PointsDisplay({ stats }: Props) {
  const { level } = stats;

  return (
    <div className="bg-slate-800 rounded-2xl p-5 flex flex-col gap-4">
      {/* Level + points */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-4xl">{level.emoji}</span>
          <div>
            <p className="text-lg font-bold text-white">{level.name}</p>
            <p className="text-xs text-slate-400">{stats.total_points.toLocaleString()} total points</p>
          </div>
        </div>
        <div className="text-right">
          <p className="text-2xl font-black text-yellow-400">{stats.weekly_points}</p>
          <p className="text-xs text-slate-400">this week</p>
        </div>
      </div>

      {/* Progress to next level */}
      {level.progress_pct !== null && level.next_at && (
        <div>
          <div className="flex justify-between text-xs text-slate-400 mb-1">
            <span>Progress to next level</span>
            <span>{level.next_at - stats.total_points} pts to go</span>
          </div>
          <div className="bg-slate-700 rounded-full h-2">
            <div
              className="h-2 rounded-full bg-gradient-to-r from-yellow-500 to-orange-400 transition-all duration-500"
              style={{ width: `${Math.min(100, level.progress_pct)}%` }}
            />
          </div>
        </div>
      )}

      {/* Stats grid */}
      <div className="grid grid-cols-3 gap-2 text-center text-xs">
        <div className="bg-slate-700 rounded-xl p-3">
          <p className="text-lg font-bold text-white">{stats.report_count}</p>
          <p className="text-slate-400">Reports</p>
        </div>
        <div className="bg-slate-700 rounded-xl p-3">
          <p className="text-lg font-bold text-white">{stats.confirm_count}</p>
          <p className="text-slate-400">Confirms</p>
        </div>
        <div className="bg-orange-900/50 rounded-xl p-3">
          <p className="text-lg font-bold text-orange-400">{stats.current_streak_days}</p>
          <p className="text-slate-400">Day streak</p>
        </div>
      </div>
    </div>
  );
}
