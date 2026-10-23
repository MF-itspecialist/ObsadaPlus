import { useState, type FormEvent } from "react";

import { api } from "../services/api";
import { ErrorBanner } from "./Feedback";
import Modal from "./Modal";

/** Zmiana własnego hasła. Pozostałe przeglądarki zostają wylogowane. */
export default function PasswordModal({ onClose, onDone }: { onClose: () => void; onDone: () => void }) {
  const [form, setForm] = useState({ current: "", next: "", repeat: "" });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (form.next !== form.repeat) return setError("Nowe hasła się różnią");
    setBusy(true);
    try {
      await api.changePassword(form.current, form.next);
      onDone();
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  };

  const field = (key: keyof typeof form, label: string, autoComplete: string) => (
    <label className="block">
      <span className="label">{label}</span>
      <input
        className="input"
        type="password"
        required
        autoComplete={autoComplete}
        value={form[key]}
        onChange={(e) => setForm({ ...form, [key]: e.target.value })}
      />
    </label>
  );

  return (
    <Modal title="Zmień hasło" subtitle="Co najmniej 8 znaków. Inne przeglądarki zostaną wylogowane." onClose={onClose}>
      <form onSubmit={submit} className="space-y-4">
        <ErrorBanner message={error} />
        {field("current", "Obecne hasło", "current-password")}
        {field("next", "Nowe hasło", "new-password")}
        {field("repeat", "Powtórz nowe hasło", "new-password")}
        <div className="flex justify-end gap-2">
          <button type="button" className="btn-secondary" onClick={onClose}>
            Anuluj
          </button>
          <button className="btn-primary" disabled={busy}>
            Zapisz hasło
          </button>
        </div>
      </form>
    </Modal>
  );
}
