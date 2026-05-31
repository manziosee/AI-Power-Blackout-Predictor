import { Link } from "react-router-dom";
import { useGeolocation } from "../hooks/useGeolocation";
import { useUserStore } from "../store/user";
import {
  useDuration,
  useAccuracy,
  useRankings,
  useCellRank,
} from "../hooks/useAnalytics";
import DurationBadge from "../components/Analytics/DurationBadge";
import AccuracyCard from "../components/Analytics/AccuracyCard";
import NeighborhoodRanking from "../components/Analytics/NeighborhoodRanking";
import OutageCalendar from "../components/Calendar/OutageCalendar";

export default function AnalyticsPage() {
  const user = useUserStore((s) => s.user);
  const { h3Index } = useGeolocation();
  const countryCode = user?.country_code ?? "RW";

  const duration = useDuration(h3Index ?? "", countryCode);
  const accuracy = useAccuracy(h3Index ?? "", 30);
  const rankings = useRankings(countryCode, 20);
  const cellRank = useCellRank(h3Index ?? "");

  return (
    <div className="min-h-screen bg-slate-900 pb-8">
      <header className="flex items-center gap-3 px-4 pt-6 pb-4">
        <Link to="/" className="text-slate-400 hover:text-white text-lg">←</Link>
        <div>
          <h1 className="text-xl font-bold">Analytics</h1>
          <p className="text-xs text-slate-400">Intelligence for your area</p>
        </div>
      </header>

      {!h3Index ? (
        <div className="px-4">
          <div className="bg-slate-800 rounded-2xl p-8 text-center text-slate-500">
            <p className="text-3xl mb-2">📍</p>
            <p>Allow location access to see analytics for your area</p>
          </div>
        </div>
      ) : (
        <div className="px-4 flex flex-col gap-4 max-w-lg mx-auto">

          {/* 1. Duration Predictor */}
          <section>
            <p className="text-xs text-slate-500 uppercase tracking-widest mb-2 px-1">
              How long will an outage last?
            </p>
            <DurationBadge data={duration} />
          </section>

          {/* 2. Outage Calendar */}
          <section>
            <p className="text-xs text-slate-500 uppercase tracking-widest mb-2 px-1">
              Monthly calendar
            </p>
            <OutageCalendar h3_index={h3Index} />
          </section>

          {/* 3. Prediction Accuracy */}
          <section>
            <p className="text-xs text-slate-500 uppercase tracking-widest mb-2 px-1">
              How accurate are our predictions?
            </p>
            <AccuracyCard data={accuracy} />
          </section>

          {/* 4. Neighborhood Ranking */}
          <section>
            <p className="text-xs text-slate-500 uppercase tracking-widest mb-2 px-1">
              Most affected neighborhoods — {countryCode}
            </p>
            <NeighborhoodRanking rankings={rankings} userRank={cellRank} />
          </section>

        </div>
      )}
    </div>
  );
}
