import { useState } from "react";
import { reportOutage } from "../../services/api";
import { queueOutageReport } from "../../services/offline";
import { useGeolocation } from "../../hooks/useGeolocation";

export default function ReportOutageForm() {
  const { h3Index, coords } = useGeolocation();
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit() {
    setSubmitting(true);
    const payload = { h3_index: h3Index ?? undefined, lat: coords?.lat, lng: coords?.lng, source: "app" };
    try {
      if (navigator.onLine) {
        await reportOutage(payload);
      } else {
        await queueOutageReport({ ...payload, source: "app" });
      }
      setSubmitted(true);
    } catch {
      await queueOutageReport({ ...payload, source: "app" });
      setSubmitted(true);
    } finally {
      setSubmitting(false);
    }
  }

  if (submitted) {
    return (
      <div className="bg-green-800 rounded-xl p-6 text-center">
        <p className="text-2xl mb-2">Thank you!</p>
        <p className="text-slate-300 text-sm">Your report helps improve predictions for your community.</p>
      </div>
    );
  }

  return (
    <div className="bg-slate-800 rounded-xl p-6 flex flex-col gap-4">
      <h2 className="text-lg font-bold">Report an Outage</h2>
      <p className="text-slate-400 text-sm">
        Is the power out in your area right now? Your report helps train the AI model.
      </p>
      {h3Index && (
        <p className="text-xs text-slate-500">Area detected: {h3Index.slice(0, 10)}...</p>
      )}
      <button
        onClick={handleSubmit}
        disabled={submitting}
        className="bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white font-bold py-3 rounded-xl transition-colors"
      >
        {submitting ? "Submitting..." : "Report Outage Now"}
      </button>
    </div>
  );
}
