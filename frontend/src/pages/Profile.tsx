import { Link } from "react-router-dom";
import LanguageSwitcher from "../components/common/LanguageSwitcher";
import { useUserStore } from "../store/user";

export default function ProfilePage() {
  const { user, logout } = useUserStore();

  return (
    <div className="min-h-screen bg-slate-900 p-4 max-w-md mx-auto flex flex-col gap-4">
      <header className="flex items-center gap-3 pt-4">
        <Link to="/" className="text-slate-400 hover:text-white">←</Link>
        <h1 className="text-xl font-bold">Profile</h1>
      </header>

      <div className="bg-slate-800 rounded-xl p-4 flex flex-col gap-3">
        <p className="text-sm text-slate-400">Phone</p>
        <p className="font-mono">{user?.phone ?? "Not logged in"}</p>
        <p className="text-sm text-slate-400 mt-2">Language</p>
        <LanguageSwitcher />
      </div>

      {user && (
        <button onClick={logout} className="bg-red-800 hover:bg-red-700 text-white py-2 rounded-xl text-sm font-semibold">
          Log Out
        </button>
      )}
    </div>
  );
}
