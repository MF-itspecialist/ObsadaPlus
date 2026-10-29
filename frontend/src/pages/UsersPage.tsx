import { KeyRound, Plus } from "lucide-react";
import { useMemo, useState, type FormEvent } from "react";

import { ErrorBanner, Loading, PageHeader } from "../components/Feedback";
import Modal from "../components/Modal";
import RowActions from "../components/RowActions";
import { Tag } from "../components/StatusBadge";
import { useAuth } from "../context/AuthContext";
import { useAsync } from "../hooks/useAsync";
import { api } from "../services/api";
import { USER_ROLE_LABELS, type Referee, type User, type UserRole, type UserWithPassword } from "../types";

export default function UsersPage() {
  const { user: me } = useAuth();
  const users = useAsync(() => api.users(), []);
  const referees = useAsync(() => api.referees(), []);
  const [editing, setEditing] = useState<User | "new" | null>(null);
  const [issued, setIssued] = useState<UserWithPassword | null>(null);
  const [error, setError] = useState<string | null>(null);

  const resetPassword = async (u: User) => {
    if (!confirm(`Wygenerować nowe hasło dla ${u.login}? Obecne przestanie działać.`)) return;
    try {
      setIssued(await api.resetPassword(u.id));
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const remove = async (u: User) => {
    if (!confirm(`Usunąć konto ${u.login}?`)) return;
    try {
      await api.deleteUser(u.id);
      users.reload();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  return (
    <div>
      <PageHeader title="Użytkownicy" subtitle="Konta obsadzających i sędziów. Sędzia widzi tylko swoje dane.">
        <button className="btn-primary" onClick={() => setEditing("new")}>
          <Plus className="size-4" /> Dodaj konto
        </button>
      </PageHeader>
      <ErrorBanner message={error ?? users.error} onClose={() => setError(null)} />
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          {users.loading && !users.data ? (
            <Loading />
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>Login</th>
                  <th>Nazwa</th>
                  <th>Rola</th>
                  <th>Sędzia</th>
                  <th>Ostatnie logowanie</th>
                  <th className="text-right">Akcje</th>
                </tr>
              </thead>
              <tbody>
                {(users.data ?? []).map((u) => (
                  <tr key={u.id} className={u.active ? "" : "opacity-60"}>
                    <td className="font-medium">
                      {u.login}
                      {u.id === me?.id && <span className="ml-2 text-xs text-zinc-400">(to Ty)</span>}
                    </td>
                    <td>{u.display_name}</td>
                    <td>
                      <Tag tone={u.role === "ADMIN" ? "brand" : "slate"}>{USER_ROLE_LABELS[u.role]}</Tag>
                      {!u.active && (
                        <span className="ml-1.5">
                          <Tag tone="red">wyłączone</Tag>
                        </span>
                      )}
                    </td>
                    <td>{u.referee_name ?? "—"}</td>
                    <td className="text-zinc-500">
                      {u.last_login_at ? new Date(u.last_login_at).toLocaleString("pl-PL", { dateStyle: "short", timeStyle: "short" }) : "nigdy"}
                    </td>
                    <td>
                      <div className="flex justify-end gap-1">
                        <button className="icon-btn" onClick={() => resetPassword(u)} aria-label="Nowe hasło" title="Nowe hasło">
                          <KeyRound className="size-4" />
                        </button>
                        <RowActions onEdit={() => setEditing(u)} onDelete={() => remove(u)} />
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {editing && (
        <UserForm
          initial={editing === "new" ? undefined : editing}
          referees={referees.data ?? []}
          takenReferees={new Set((users.data ?? []).filter((u) => u.referee_id && u !== editing).map((u) => u.referee_id!))}
          onClose={() => setEditing(null)}
          onSaved={(result) => {
            setEditing(null);
            users.reload();
            if (result?.password) setIssued(result);
          }}
        />
      )}
      {issued && (
        <Modal title="Hasło do przekazania" subtitle="Zapisz je teraz — nie będzie ponownie widoczne." onClose={() => setIssued(null)}>
          <div className="space-y-3 text-sm">
            <div>
              Login: <strong>{issued.user.login}</strong>
            </div>
            <div className="rounded-xl bg-zinc-50 px-4 py-3 font-mono text-lg tracking-wider ring-1 ring-zinc-950/5 select-all">{issued.password}</div>
            <p className="text-zinc-500">Po pierwszym logowaniu warto zmienić hasło (menu po lewej: „Zmień hasło”).</p>
          </div>
        </Modal>
      )}
    </div>
  );
}

function UserForm({
  initial,
  referees,
  takenReferees,
  onClose,
  onSaved,
}: {
  initial?: User;
  referees: Referee[];
  takenReferees: Set<number>;
  onClose: () => void;
  onSaved: (result: UserWithPassword | null) => void;
}) {
  const [form, setForm] = useState({
    login: initial?.login ?? "",
    display_name: initial?.display_name ?? "",
    role: (initial?.role ?? "REFEREE") as UserRole,
    referee_id: initial?.referee_id ?? null,
    active: initial?.active ?? true,
    password: "",
  });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const options = useMemo(
    () =>
      referees
        .filter((r) => !takenReferees.has(r.id) || r.id === initial?.referee_id)
        .sort((a, b) => `${a.last_name} ${a.first_name}`.localeCompare(`${b.last_name} ${b.first_name}`, "pl")),
    [referees, takenReferees, initial],
  );

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      const data = { display_name: form.display_name, role: form.role, referee_id: form.role === "REFEREE" ? form.referee_id : null, active: form.active };
      if (initial) {
        await api.updateUser(initial.id, data);
        onSaved(null);
      } else {
        onSaved(await api.createUser({ ...data, login: form.login, password: form.password || null }));
      }
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  };

  return (
    <Modal title={initial ? `Konto ${initial.login}` : "Nowe konto"} onClose={onClose}>
      <form onSubmit={submit} className="space-y-4">
        <ErrorBanner message={error} />
        <div className="grid grid-cols-2 gap-3">
          <label className="block">
            <span className="label">Login</span>
            <input
              className="input"
              required
              disabled={!!initial}
              value={form.login}
              onChange={(e) => setForm({ ...form, login: e.target.value })}
              placeholder="np. j.kowalski"
            />
          </label>
          <label className="block">
            <span className="label">Rola</span>
            <select className="input" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value as UserRole })}>
              <option value="REFEREE">{USER_ROLE_LABELS.REFEREE}</option>
              <option value="ADMIN">{USER_ROLE_LABELS.ADMIN}</option>
            </select>
          </label>
        </div>
        {form.role === "REFEREE" && (
          <label className="block">
            <span className="label">Sędzia</span>
            <select
              className="input"
              required
              value={form.referee_id ?? ""}
              onChange={(e) => setForm({ ...form, referee_id: e.target.value ? Number(e.target.value) : null })}
            >
              <option value="">Wybierz sędziego…</option>
              {options.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.last_name} {r.first_name} ({r.city})
                </option>
              ))}
            </select>
          </label>
        )}
        <label className="block">
          <span className="label">Nazwa wyświetlana</span>
          <input
            className="input"
            value={form.display_name}
            onChange={(e) => setForm({ ...form, display_name: e.target.value })}
            placeholder={form.role === "REFEREE" ? "domyślnie imię i nazwisko sędziego" : "np. Maciej"}
          />
        </label>
        {!initial && (
          <label className="block">
            <span className="label">Hasło</span>
            <input
              className="input"
              type="password"
              autoComplete="new-password"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              placeholder="puste = wygeneruj losowe hasło"
            />
          </label>
        )}
        {initial && (
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={form.active} onChange={(e) => setForm({ ...form, active: e.target.checked })} />
            Konto aktywne (wyłączone nie może się zalogować)
          </label>
        )}
        <div className="flex justify-end gap-2">
          <button type="button" className="btn-secondary" onClick={onClose}>
            Anuluj
          </button>
          <button className="btn-primary" disabled={busy}>
            {initial ? "Zapisz" : "Utwórz konto"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
