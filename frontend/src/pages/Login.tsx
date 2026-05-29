import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { loginUser, getMe } from "../services/api";
import { useUserStore } from "../store/user";

export default function Login() {
  const navigate = useNavigate();
  const { setToken, setUser } = useUserStore();

  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const { data } = await loginUser({ phone, password });
      setToken(data.access_token);
      const { data: me } = await getMe();
      setUser(me);
      navigate("/");
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "Invalid phone or password.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4">
      <div className="w-full max-w-sm flex flex-col gap-6">

        <div className="text-center">
          <p className="text-4xl mb-2">⚡</p>
          <h1 className="text-2xl font-bold text-white">Welcome back</h1>
          <p className="text-slate-400 text-sm mt-1">Log in to see your area's risk</p>
        </div>

        <form onSubmit={handleSubmit} className="bg-slate-800 rounded-2xl p-6 flex flex-col gap-4">

          {/* Phone */}
          <div className="flex flex-col gap-1">
            <label className="text-xs text-slate-400 font-medium">Phone number</label>
            <input
              type="tel"
              placeholder="+250788123456"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              className="bg-slate-700 text-white rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>

          {/* Password */}
          <div className="flex flex-col gap-1">
            <label className="text-xs text-slate-400 font-medium">Password</label>
            <input
              type="password"
              placeholder="Your password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="bg-slate-700 text-white rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>

          {error && (
            <p className="text-red-400 text-xs bg-red-900/30 rounded-lg px-3 py-2">{error}</p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-bold py-3 rounded-xl transition-colors mt-1"
          >
            {loading ? "Logging in..." : "Log in"}
          </button>
        </form>

        <p className="text-center text-slate-400 text-sm">
          Don't have an account?{" "}
          <Link to="/register" className="text-blue-400 hover:text-blue-300 font-medium">
            Create one
          </Link>
        </p>
      </div>
    </div>
  );
}
