import { useState } from "react";
import { Link } from "react-router-dom";
import { useGeolocation } from "../hooks/useGeolocation";
import { useUserStore } from "../store/user";
import {
  useMyStats,
  useLeaderboard,
  useCommunityNotes,
} from "../hooks/useCommunity";
import PointsDisplay from "../components/Community/PointsDisplay";
import BadgeCollection from "../components/Community/BadgeCollection";
import Leaderboard from "../components/Community/Leaderboard";
import CommunityNotes from "../components/Community/CommunityNotes";

type Tab = "profile" | "leaderboard" | "notes";

export default function CommunityPage() {
  const [tab, setTab] = useState<Tab>("profile");
  const [lbPeriod, setLbPeriod] = useState<"weekly" | "monthly">("weekly");

  const user = useUserStore((s) => s.user);
  const { h3Index } = useGeolocation();
  const countryCode = user?.country_code ?? "RW";

  const { data: stats } = useMyStats();
  const leaderboard = useLeaderboard(countryCode, lbPeriod);
  const { notes, loading: notesLoading, addNote, upvote, remove } = useCommunityNotes(h3Index ?? "");

  const TABS: { key: Tab; label: string; icon: string }[] = [
    { key: "profile",     label: "My Profile",  icon: "👤" },
    { key: "leaderboard", label: "Rankings",     icon: "🏆" },
    { key: "notes",       label: "Community",    icon: "💬" },
  ];

  return (
    <div className="min-h-screen bg-slate-900 pb-8">
      {/* Header */}
      <header className="flex items-center gap-3 px-4 pt-6 pb-2">
        <Link to="/" className="text-slate-400 hover:text-white text-lg">←</Link>
        <div>
          <h1 className="text-xl font-bold">Community</h1>
          <p className="text-xs text-slate-400">
            {stats ? `${stats.total_points} points · ${stats.level.name} ${stats.level.emoji}` : "Loading..."}
          </p>
        </div>
      </header>

      {/* Tab bar */}
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

      <div className="px-4 max-w-lg mx-auto flex flex-col gap-4">

        {/* ── My Profile tab ── */}
        {tab === "profile" && (
          <>
            {stats ? (
              <>
                <PointsDisplay stats={stats} />
                <BadgeCollection earned={stats.badges} />
              </>
            ) : (
              <div className="bg-slate-800 rounded-2xl p-8 text-center text-slate-500">
                <p className="text-3xl mb-2">📍</p>
                <p>Log in and report an outage to start earning points</p>
              </div>
            )}

            {/* How to earn points */}
            <div className="bg-slate-800 rounded-2xl p-5 flex flex-col gap-3">
              <p className="text-xs text-slate-400 uppercase tracking-widest">How to earn points</p>
              <div className="flex flex-col gap-2 text-sm">
                {[
                  ["Report an outage",        "+10 pts", "⚡"],
                  ["First reporter in area",  "+15 pts", "🚨"],
                  ["Confirm a neighbor's report", "+5 pts", "✅"],
                  ["Resolve an outage",       "+3 pts",  "🔧"],
                  ["Add a community note",    "+2 pts",  "💬"],
                  ["7-day streak bonus",      "+10 pts", "🔥"],
                ].map(([action, pts, icon]) => (
                  <div key={action} className="flex justify-between items-center py-1 border-b border-slate-700/50 last:border-0">
                    <span className="text-slate-300">{icon} {action}</span>
                    <span className="text-yellow-400 font-semibold">{pts}</span>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}

        {/* ── Leaderboard tab ── */}
        {tab === "leaderboard" && (
          <Leaderboard
            entries={leaderboard}
            onPeriodChange={setLbPeriod}
          />
        )}

        {/* ── Community Notes tab ── */}
        {tab === "notes" && (
          !h3Index ? (
            <div className="bg-slate-800 rounded-2xl p-8 text-center text-slate-500">
              <p className="text-3xl mb-2">📍</p>
              <p>Allow location access to see notes for your area</p>
            </div>
          ) : (
            <CommunityNotes
              notes={notes}
              loading={notesLoading}
              onAdd={addNote}
              onUpvote={upvote}
              onDelete={remove}
            />
          )
        )}

      </div>
    </div>
  );
}
