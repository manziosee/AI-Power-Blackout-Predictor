import { useTranslation } from "react-i18next";
import type { Prediction } from "../../store/predictions";
import RiskMeter from "./RiskMeter";

interface Props {
  prediction: Prediction;
}

export default function PredictionCard({ prediction }: Props) {
  const { t } = useTranslation();
  const start = new Date(prediction.window_start).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  const end = new Date(prediction.window_end).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

  return (
    <div className="bg-slate-800 rounded-2xl p-5 shadow-lg flex flex-col gap-4">
      <div className="flex justify-between items-start">
        <div>
          <p className="text-slate-400 text-xs uppercase tracking-widest">{t("prediction.window")}</p>
          <p className="text-slate-100 font-semibold">
            {start} → {end}
          </p>
        </div>
        <span className="text-slate-500 text-xs">#{prediction.h3_index.slice(0, 8)}</span>
      </div>
      <RiskMeter probability={prediction.probability} riskLevel={prediction.risk_level as any} />
    </div>
  );
}
