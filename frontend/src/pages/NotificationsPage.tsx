import { ChevronDown, Mail, Send } from "lucide-react";
import { Fragment, useEffect, useState } from "react";

import { EmptyState, ErrorBanner, InfoBanner, Loading, PageHeader } from "../components/Feedback";
import { Field } from "../components/RefereeForm";
import { Tag } from "../components/StatusBadge";
import { useAsync } from "../hooks/useAsync";
import { api } from "../services/api";
import type { OutboxMessage, SystemSettings } from "../types";

const KIND: Record<OutboxMessage["kind"], string> = {
  publication: "obsada",
  availability_reminder: "przypomnienie",
  test: "próbna",
};
const WEEKDAYS = ["poniedziałek", "wtorek", "środa", "czwartek"];

function when(iso: string): string {
  return new Date(iso).toLocaleString("pl-PL", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
}

/** Powiadomienia e-mail: stan skrzynki, ustawienia przypomnień i skrzynka nadawcza. */
export default function NotificationsPage() {
  const status = useAsync(() => api.notificationStatus(), []);
  const messages = useAsync(() => api.notifications(), []);
  const loaded = useAsync(() => api.settings(), []);
  const [form, setForm] = useState<SystemSettings | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [testTo, setTestTo] = useState("");
  const [open, setOpen] = useState<number | null>(null);
  const st = status.data;

  useEffect(() => {
    if (loaded.data) setForm(loaded.data);
  }, [loaded.data]);

  const refresh = () => {
    status.reload();
    messages.reload();
  };
  const act = async (fn: () => Promise<string>) => {
    try {
      setInfo(await fn());
      refresh();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  return (
    <div className="max-w-5xl">
      <PageHeader title="Powiadomienia" subtitle="E-maile do sędziów: obsada po publikacji i przypomnienia o dyspozycyjności">
        <button
          className="btn-primary"
          disabled={!st?.smtp_configured || !st.pending}
          onClick={() => act(async () => {
            const r = await api.sendPending();
            return `Wysłano ${r.sent}${r.failed ? `, nie udało się ${r.failed}` : ""}.`;
          })}
        >
          <Send className="size-4" /> Wyślij oczekujące{st?.pending ? ` (${st.pending})` : ""}
        </button>
      </PageHeader>
      <ErrorBanner message={error ?? status.error} onClose={() => setError(null)} />
      <InfoBanner message={info} onClose={() => setInfo(null)} />

      <div className="mb-6 grid gap-4 md:grid-cols-2">
        <div className="card p-6">
          <h2 className="mb-3 text-sm font-semibold">Skrzynka do wysyłki</h2>
          {!st ? (
            <Loading />
          ) : st.smtp_configured ? (
            <p className="text-sm">
              <Tag tone="emerald">skonfigurowana</Tag> <span className="ml-1 text-zinc-600">{st.smtp_from}</span>
            </p>
          ) : (
            <p className="text-sm text-zinc-600">
              <Tag tone="amber">brak</Tag> Wiadomości czekają tutaj i wyjdą po uzupełnieniu <code>SMTP_HOST</code>, <code>SMTP_USER</code> i{" "}
              <code>SMTP_PASSWORD</code> w pliku <code>.env</code> (instrukcja w zadaniu 019).
            </p>
          )}
          {st && (
            <p className="mt-3 text-sm text-zinc-600">
              Adres e-mail ma <span className="font-medium text-zinc-900">{st.referees_with_email}</span> z {st.active_referees} aktywnych sędziów.
              {!st.app_url && " Brak APP_URL w .env, więc wiadomości nie zawierają linku do aplikacji."}
            </p>
          )}
          <div className="mt-4 flex gap-2">
            <input className="input" type="email" placeholder="adres do wiadomości próbnej" value={testTo} onChange={(e) => setTestTo(e.target.value)} />
            <button
              className="btn-secondary whitespace-nowrap"
              disabled={!testTo}
              onClick={() => act(async () => {
                const m = await api.sendTestMail(testTo);
                return m.status === "sent" ? "Wiadomość próbna wysłana." : m.status === "failed" ? `Nie udało się: ${m.error}` : "Wiadomość czeka w skrzynce (brak konfiguracji).";
              })}
            >
              <Mail className="size-4" /> Wyślij próbną
            </button>
          </div>
        </div>

        {form && (
          <div className="card p-6">
            <h2 className="mb-3 text-sm font-semibold">Kiedy wysyłać</h2>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={form.notify_on_publish} onChange={(e) => setForm({ ...form, notify_on_publish: e.target.checked })} />
              Po publikacji obsady (przy kolejnej wersji tylko do sędziów, u których coś się zmieniło)
            </label>
            <label className="mt-2 flex items-center gap-2 text-sm">
              <input type="checkbox" checked={form.availability_reminder_enabled} onChange={(e) => setForm({ ...form, availability_reminder_enabled: e.target.checked })} />
              Przypomnienie o dyspozycyjności na najbliższy weekend (do tych, którzy jej nie zgłosili)
            </label>
            <div className="mt-3 grid grid-cols-3 gap-3">
              <Field label="Dzień">
                <select className="input" value={form.reminder_weekday} onChange={(e) => setForm({ ...form, reminder_weekday: Number(e.target.value) })}>
                  {WEEKDAYS.map((d, i) => (
                    <option key={d} value={i}>
                      {d}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Godzina">
                <select className="input" value={form.reminder_hour} onChange={(e) => setForm({ ...form, reminder_hour: Number(e.target.value) })}>
                  {Array.from({ length: 24 }, (_, h) => (
                    <option key={h} value={h}>
                      {String(h).padStart(2, "0")}:00
                    </option>
                  ))}
                </select>
              </Field>
              <div className="flex items-end">
                <button
                  className="btn-secondary w-full"
                  onClick={() => act(async () => {
                    setForm(await api.saveSettings(form));
                    return "Zapisano.";
                  })}
                >
                  Zapisz
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {messages.loading && !messages.data ? (
        <Loading />
      ) : !messages.data?.length ? (
        <EmptyState title="Brak wiadomości" hint="Pojawią się po publikacji obsady albo przy przypomnieniu o dyspozycyjności." />
      ) : (
        <div className="card overflow-hidden">
          <table className="table">
            <thead>
              <tr>
                <th>Kiedy</th>
                <th>Do</th>
                <th>Temat</th>
                <th>Stan</th>
              </tr>
            </thead>
            <tbody>
              {messages.data.map((m) => (
                <MessageRow key={m.id} m={m} open={open === m.id} onToggle={() => setOpen(open === m.id ? null : m.id)} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function MessageRow({ m, open, onToggle }: { m: OutboxMessage; open: boolean; onToggle: () => void }) {
  return (
    <Fragment>
      <tr className="cursor-pointer" onClick={onToggle}>
        <td className="whitespace-nowrap tabular-nums">
          <div className="flex items-center gap-2">
            <ChevronDown className={`size-4 text-zinc-400 transition ${open ? "rotate-180" : ""}`} />
            {when(m.created_at)}
          </div>
        </td>
        <td>
          <div className="font-medium">{m.to_name || m.to_email}</div>
          {m.to_name && <div className="text-xs text-zinc-500">{m.to_email}</div>}
        </td>
        <td>
          <span className="mr-2 text-xs text-zinc-500">{KIND[m.kind]}</span>
          {m.subject}
        </td>
        <td>
          {m.status === "sent" ? <Tag tone="emerald">wysłana</Tag> : m.status === "failed" ? <Tag tone="red">błąd</Tag> : <Tag tone="amber">czeka</Tag>}
        </td>
      </tr>
      {open && (
        <tr>
          <td colSpan={4} className="bg-zinc-50">
            {m.error && <div className="mb-2 text-sm text-red-700">{m.error}</div>}
            <pre className="whitespace-pre-wrap font-sans text-sm text-zinc-700">{m.body}</pre>
          </td>
        </tr>
      )}
    </Fragment>
  );
}
