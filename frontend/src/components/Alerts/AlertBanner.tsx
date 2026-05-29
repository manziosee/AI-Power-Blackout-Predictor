import { useTranslation } from "react-i18next";
import type { Prediction } from "../../store/predictions";

interface Props {
  prediction: Prediction | null;
}

const BG = { critical: "bg-purple-700", high: "bg-red-600", medium: "bg-yellow-500", low: "bg-green-600" };

export default function AlertBanner({ prediction }: Props) {
  const { t } = useTranslation();
  if (!prediction || prediction.risk_level === "low") return null;

  const bg = BG[prediction.risk_level as keyof typeof BG] ?? BG.medium;
  const time = new Date(prediction.window_start).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

  return (
    <div className={`${bg} text-white px-4 py-3 rounded-xl flex items-center gap-3 shadow-lg`}>
      <span className="text-2xl">⚡</span>
      <div>
        <p className="font-bold text-sm uppercase tracking-wide">{prediction.risk_level} outage risk</p>
        <p className="text-xs opacity-90">
          {Math.round(prediction.probability * 100)}% chance at {time}. Charge your devices now.
        </p>
      </div>
    </div>
  );
}
