import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { registerUser } from "../services/api";
import { useUserStore } from "../store/user";

const COUNTRIES = [
  { code: "RW", flag: "🇷🇼", name: "Rwanda", dial: "+250" },
  { code: "KE", flag: "🇰🇪", name: "Kenya", dial: "+254" },
  { code: "UG", flag: "🇺🇬", name: "Uganda", dial: "+256" },
  { code: "TZ", flag: "🇹🇿", name: "Tanzania", dial: "+255" },
  { code: "NG", flag: "🇳🇬", name: "Nigeria", dial: "+234" },
  { code: "GH", flag: "🇬🇭", name: "Ghana", dial: "+233" },
  { code: "ZA", flag: "🇿🇦", name: "South Africa", dial: "+27" },
  { code: "FR", flag: "🇫🇷", name: "France", dial: "+33" },
  { code: "GB", flag: "🇬🇧", name: "United Kingdom", dial: "+44" },
  { code: "US", flag: "🇺🇸", name: "United States", dial: "+1" },
  { code: "BR", flag: "🇧🇷", name: "Brazil", dial: "+55" },
  { code: "IN", flag: "🇮🇳", name: "India", dial: "+91" },
];

const LANG_OPTIONS = [
  { code: "en", label: "English" },
  { code: "fr", label: "Français" },
  { code: "sw", label: "Swahili" },
  { code: "rw", label: "Kinyarwanda" },
  { code: "ar", label: "العربية" },
  { code: "es", label: "Español" },
  { code: "pt", label: "Português" },
];

export default function Register() {
  const navigate = useNavigate();
  const { setToken, setUser } = useUserStore();

  const [countryCode, setCountryCode] = useState("RW");
  const [phone, setPhone] = useState("");
  const [language, setLanguage] = useState("en");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const selectedCountry = COUNTRIES.find((c) => c.code === countryCode)!;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");

    const fullPhone = `${selectedCountry.dial}${phone.replace(/^0/, "")}`;

    if (phone.length < 7) {
      setError("Enter a valid phone number.");
      return;
    }

    setLoading(true);
    try {
      const { data } = await registerUser({ phone: fullPhone, country_code: countryCode, language, password });
      setToken(data.access_token);
      setUser({ id: "", phone: fullPhone, country_code: countryCode, language });
      navigate("/");
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "Registration failed. Try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4">
      <div className="w-full max-w-sm flex flex-col gap-6">

        <div className="text-center">
          <p className="text-4xl mb-2">⚡</p>
          <h1 className="text-2xl font-bold text-white">Create account</h1>
          <p className="text-slate-400 text-sm mt-1">Get outage alerts for your area</p>
        </div>

        <form onSubmit={handleSubmit} className="bg-slate-800 rounded-2xl p-6 flex flex-col gap-4">

          {/* Country */}
          <div className="flex flex-col gap-1">
            <label className="text-xs text-slate-400 font-medium">Country</label>
            <select
              value={countryCode}
              onChange={(e) => setCountryCode(e.target.value)}
              className="bg-slate-700 text-white rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {COUNTRIES.map((c) => (
                <option key={c.code} value={c.code}>
                  {c.flag} {c.name} ({c.dial})
                </option>
              ))}
            </select>
          </div>

          {/* Phone */}
          <div className="flex flex-col gap-1">
            <label className="text-xs text-slate-400 font-medium">Phone number</label>
            <div className="flex gap-2 items-center bg-slate-700 rounded-lg px-3 py-2.5">
              <span className="text-slate-400 text-sm shrink-0">{selectedCountry.dial}</span>
              <input
                type="tel"
                placeholder="788 123 456"
                value={phone}
                onChange={(e) => setPhone(e.target.value.replace(/\D/g, ""))}
                className="bg-transparent text-white text-sm flex-1 focus:outline-none"
                required
              />
            </div>
          </div>

          {/* Language */}
          <div className="flex flex-col gap-1">
            <label className="text-xs text-slate-400 font-medium">Preferred language</label>
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              className="bg-slate-700 text-white rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {LANG_OPTIONS.map((l) => (
                <option key={l.code} value={l.code}>{l.label}</option>
              ))}
            </select>
          </div>

          {/* Password */}
          <div className="flex flex-col gap-1">
            <label className="text-xs text-slate-400 font-medium">Password</label>
            <input
              type="password"
              placeholder="Min. 8 characters"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              minLength={8}
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
            {loading ? "Creating account..." : "Create account"}
          </button>
        </form>

        <p className="text-center text-slate-400 text-sm">
          Already have an account?{" "}
          <Link to="/login" className="text-blue-400 hover:text-blue-300 font-medium">
            Log in
          </Link>
        </p>
      </div>
    </div>
  );
}
