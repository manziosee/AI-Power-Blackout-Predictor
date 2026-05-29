import { Link } from "react-router-dom";
import ReportOutageForm from "../components/Report/ReportOutageForm";

export default function ReportOutagePage() {
  return (
    <div className="min-h-screen bg-slate-900 p-4 max-w-md mx-auto flex flex-col gap-4">
      <header className="flex items-center gap-3 pt-4">
        <Link to="/" className="text-slate-400 hover:text-white">←</Link>
        <h1 className="text-xl font-bold">Report Outage</h1>
      </header>
      <ReportOutageForm />
    </div>
  );
}
