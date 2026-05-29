import { useEffect, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { getCellOutages } from "../../services/api";

interface Props {
  h3_index: string;
}

export default function OutageHistory({ h3_index }: Props) {
  const [data, setData] = useState<{ day: string; outages: number }[]>([]);

  useEffect(() => {
    getCellOutages(h3_index)
      .then(({ data: reports }) => {
        const counts: Record<string, number> = {};
        reports.forEach((r: { reported_at: string }) => {
          const day = new Date(r.reported_at).toLocaleDateString("en", { weekday: "short" });
          counts[day] = (counts[day] ?? 0) + 1;
        });
        setData(Object.entries(counts).map(([day, outages]) => ({ day, outages })));
      })
      .catch(() => {});
  }, [h3_index]);

  return (
    <div className="bg-slate-800 rounded-2xl p-4">
      <p className="text-slate-400 text-xs uppercase tracking-widest mb-3">Recent Outages</p>
      <ResponsiveContainer width="100%" height={120}>
        <BarChart data={data}>
          <XAxis dataKey="day" stroke="#64748b" tick={{ fill: "#94a3b8", fontSize: 11 }} />
          <YAxis stroke="#64748b" tick={{ fill: "#94a3b8", fontSize: 11 }} allowDecimals={false} />
          <Tooltip contentStyle={{ background: "#1e293b", border: "none", borderRadius: 8 }} />
          <Bar dataKey="outages" fill="#3b82f6" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
