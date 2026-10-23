import { LogIn } from "lucide-react";
import { useState, type FormEvent } from "react";

import { ErrorBanner } from "../components/Feedback";
import { useAuth } from "../context/AuthContext";

export default function LoginPage() {
  const { login } = useAuth();
  const [form, setForm] = useState({ login: "", password: "" });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(form.login, form.password);
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <form onSubmit={submit} className="card w-full max-w-sm space-y-4 p-7">
        <div className="mb-2 flex items-center gap-2.5">
          <div className="flex size-9 items-center justify-center rounded-xl bg-gradient-to-br from-brand-500 to-violet-500 text-lg font-bold text-white shadow-md shadow-brand-500/30">
            +
          </div>
          <div className="leading-tight">
            <div className="text-[15px] font-semibold tracking-tight">Obsada+</div>
            <div className="text-[11px] text-zinc-500">Zaloguj się, aby kontynuować</div>
          </div>
        </div>
        <ErrorBanner message={error} />
        <label className="block">
          <span className="label">Login</span>
          <input
            className="input"
            autoComplete="username"
            autoFocus
            required
            value={form.login}
            onChange={(e) => setForm({ ...form, login: e.target.value })}
          />
        </label>
        <label className="block">
          <span className="label">Hasło</span>
          <input
            className="input"
            type="password"
            autoComplete="current-password"
            required
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
          />
        </label>
        <button className="btn-primary w-full justify-center" disabled={busy}>
          <LogIn className="size-4" /> {busy ? "Logowanie…" : "Zaloguj"}
        </button>
      </form>
    </div>
  );
}
