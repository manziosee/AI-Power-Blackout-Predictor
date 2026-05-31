import type { Badge } from "../../hooks/useCommunity";

const ALL_BADGES = [
  { key: "first_report",   name: "First Responder",     emoji: "🚨", description: "First to report an outage" },
  { key: "reporter_10",    name: "Reliable Reporter",    emoji: "📡", description: "10 verified reports" },
  { key: "reporter_50",    name: "Field Agent",          emoji: "🕵️", description: "50 verified reports" },
  { key: "confirmer_25",   name: "Truth Seeker",         emoji: "✅", description: "25 confirmations" },
  { key: "streak_7",       name: "Streak Keeper",        emoji: "🔥", description: "7-day streak" },
  { key: "streak_30",      name: "Guardian",             emoji: "🛡️", description: "30-day streak" },
  { key: "community_100",  name: "Community Champion",   emoji: "🏆", description: "100+ points" },
  { key: "community_500",  name: "Power Hero",           emoji: "⚡", description: "500+ points" },
];

interface Props { earned: Badge[] }

export default function BadgeCollection({ earned }: Props) {
  const earnedKeys = new Set(earned.map(b => b.key));

  return (
    <div className="bg-slate-800 rounded-2xl p-5 flex flex-col gap-4">
      <div className="flex justify-between items-center">
        <p className="text-xs text-slate-400 uppercase tracking-widest">Badges</p>
        <span className="text-xs text-slate-500">{earned.length}/{ALL_BADGES.length} earned</span>
      </div>

      <div className="grid grid-cols-4 gap-3">
        {ALL_BADGES.map(badge => {
          const isEarned = earnedKeys.has(badge.key);
          const earnedData = earned.find(b => b.key === badge.key);

          return (
            <div
              key={badge.key}
              title={`${badge.name}: ${badge.description}${earnedData ? ` — earned ${new Date(earnedData.earned_at).toLocaleDateString()}` : " (locked)"}`}
              className={`flex flex-col items-center gap-1 p-2 rounded-xl text-center transition-all ${isEarned ? "bg-yellow-900/40 border border-yellow-700" : "bg-slate-700/40 opacity-35"}`}
            >
              <span className="text-2xl">{badge.emoji}</span>
              <span className="text-[10px] text-slate-300 leading-tight">{badge.name}</span>
            </div>
          );
        })}
      </div>

      {earned.length === 0 && (
        <p className="text-xs text-slate-500 text-center">
          Report your first outage to earn the First Responder badge 🚨
        </p>
      )}
    </div>
  );
}
