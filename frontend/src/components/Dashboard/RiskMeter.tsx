const RISK_CONFIG = {
  low:      { color: "text-risk-low",      bg: "bg-risk-low",      label: "LOW",      pct: 15 },
  medium:   { color: "text-risk-medium",   bg: "bg-risk-medium",   label: "MEDIUM",   pct: 55 },
  high:     { color: "text-risk-high",     bg: "bg-risk-high",     label: "HIGH",     pct: 78 },
  critical: { color: "text-risk-critical", bg: "bg-risk-critical", label: "CRITICAL", pct: 95 },
} as const;

interface Props {
  probability: number;
  riskLevel: keyof typeof RISK_CONFIG;
}

export default function RiskMeter({ probability, riskLevel }: Props) {
  const cfg = RISK_CONFIG[riskLevel] ?? RISK_CONFIG.low;

  return (
    <div className="flex flex-col items-center gap-2">
      <span className={`text-4xl font-bold ${cfg.color}`}>{Math.round(probability * 100)}%</span>
      <span className={`text-xs font-bold px-3 py-1 rounded-full ${cfg.bg} text-black`}>{cfg.label}</span>
      <div className="w-full bg-slate-700 rounded-full h-2">
        <div
          className={`h-2 rounded-full transition-all duration-500 ${cfg.bg}`}
          style={{ width: `${Math.round(probability * 100)}%` }}
        />
      </div>
    </div>
  );
}
