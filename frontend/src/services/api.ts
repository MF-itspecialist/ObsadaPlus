// Klient REST API backendu. Jedno miejsce z adresami endpointów.
import type {
  Assignment,
  Availability,
  BoardItem,
  Candidate,
  ConfirmResponse,
  DashboardStats,
  GenerationMode,
  GenerationPreview,
  GeocodeResult,
  LicenseGroup,
  ImportResult,
  ManualAssignmentResult,
  Match,
  MatchInput,
  MyMatch,
  OwnAvailabilitySave,
  PeriodStatistics,
  Referee,
  RefereeInput,
  RefereeOverview,
  Publication,
  PublicationSummary,
  RefereeRole,
  SystemSettings,
  User,
  UserInput,
  UserWithPassword,
  Venue,
  VenueInput,
} from "../types";

const BASE_URL: string = import.meta.env.VITE_API_URL ?? "";

export const UNAUTHORIZED_EVENT = "obsada:unauthorized";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

type Query = Record<string, string | number | boolean | undefined | null>;

function buildUrl(path: string, query?: Query): string {
  const params = new URLSearchParams();
  Object.entries(query ?? {}).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") params.set(k, String(v));
  });
  const qs = params.toString();
  return `${BASE_URL}${path}${qs ? `?${qs}` : ""}`;
}

function errorMessage(body: unknown, fallback: string): string {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail.map((d: { loc?: unknown[]; msg?: string }) => `${(d.loc ?? []).slice(1).join(".")}: ${d.msg}`).join("; ");
    }
  }
  return fallback;
}

async function request<T>(method: string, path: string, opts: { query?: Query; body?: unknown; form?: FormData } = {}): Promise<T> {
  const init: RequestInit = { method, headers: {}, credentials: "include" };
  if (opts.form) {
    init.body = opts.form;
  } else if (opts.body !== undefined) {
    init.body = JSON.stringify(opts.body);
    (init.headers as Record<string, string>)["Content-Type"] = "application/json";
  }
  const res = await fetch(buildUrl(path, opts.query), init);
  if (res.status === 204) return undefined as T;
  const body = await res.json().catch(() => null);
  // Sesja wygasła / wylogowano w innej karcie — AuthContext pokaże ekran logowania.
  if (res.status === 401 && !path.startsWith("/api/auth/")) window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
  if (!res.ok) throw new ApiError(res.status, errorMessage(body, `Błąd ${res.status}`));
  return body as T;
}

/** Adres pliku do pobrania (eksport) — otwierany zwykłym linkiem, nie przez fetch. */
export function fileUrl(path: string, query?: Query): string {
  return buildUrl(path, query);
}

export interface Period {
  date_from: string;
  date_to: string;
}

export const api = {
  // Logowanie i konta
  me: () => request<User>("GET", "/api/auth/me"),
  login: (login: string, password: string) => request<User>("POST", "/api/auth/login", { body: { login, password } }),
  logout: () => request<void>("POST", "/api/auth/logout"),
  changePassword: (current_password: string, new_password: string) =>
    request<void>("POST", "/api/auth/password", { body: { current_password, new_password } }),
  users: () => request<User[]>("GET", "/api/users"),
  createUser: (data: UserInput & { login: string; password?: string | null }) => request<UserWithPassword>("POST", "/api/users", { body: data }),
  updateUser: (id: number, data: UserInput) => request<User>("PUT", `/api/users/${id}`, { body: data }),
  resetPassword: (id: number) => request<UserWithPassword>("POST", `/api/users/${id}/reset-password`),
  deleteUser: (id: number) => request<void>("DELETE", `/api/users/${id}`),

  // Sędziowie
  referees: () => request<Referee[]>("GET", "/api/referees"),
  refereesOverview: (p: Period) => request<RefereeOverview[]>("GET", "/api/referees/overview", { query: { ...p } }),
  createReferee: (data: RefereeInput) => request<Referee>("POST", "/api/referees", { body: data }),
  updateReferee: (id: number, data: RefereeInput) => request<Referee>("PUT", `/api/referees/${id}`, { body: data }),
  deleteReferee: (id: number) => request<void>("DELETE", `/api/referees/${id}`),

  // Panel sędziego (konto sędziego)
  myMatches: () => request<MyMatch[]>("GET", "/api/me/matches"),
  myAvailability: (p: Period) => request<Availability[]>("GET", "/api/me/availability", { query: { ...p } }),
  saveMyAvailability: (data: OwnAvailabilitySave) => request<Availability[]>("PUT", "/api/me/availability", { body: data }),
  serverToday: () => request<{ today: string }>("GET", "/api/me/today"),

  // Obiekty
  venues: () => request<Venue[]>("GET", "/api/venues"),
  createVenue: (data: VenueInput) => request<Venue>("POST", "/api/venues", { body: data }),
  updateVenue: (id: number, data: VenueInput) => request<Venue>("PUT", `/api/venues/${id}`, { body: data }),
  deleteVenue: (id: number) => request<void>("DELETE", `/api/venues/${id}`),

  // Katalog licencji (nazwy i uprawnienia)
  licenses: () => request<LicenseGroup[]>("GET", "/api/licenses"),
  leagueLevels: () => request<string[]>("GET", "/api/licenses/levels"),
  clubs: () => request<string[]>("GET", "/api/matches/clubs"),

  // Lokalizacja adresu (podgląd w formularzach)
  geocode: (address: string, city: string) => request<GeocodeResult>("GET", "/api/geocode", { query: { address, city } }),

  // Mecze
  matches: (p?: Partial<Period>) => request<Match[]>("GET", "/api/matches", { query: { ...p } }),
  createMatch: (data: MatchInput) => request<Match>("POST", "/api/matches", { body: data }),
  updateMatch: (id: number, data: MatchInput) => request<Match>("PUT", `/api/matches/${id}`, { body: data }),
  deleteMatch: (id: number) => request<void>("DELETE", `/api/matches/${id}`),
  importMatches: (file: File, includePast = false) => {
    const form = new FormData();
    form.append("file", file);
    return request<ImportResult>("POST", "/api/matches/import", { form, query: { include_past: includePast || undefined } });
  },

  // Dyspozycyjność
  availability: (p: Period) => request<Availability[]>("GET", "/api/availability", { query: { ...p } }),
  saveAvailability: (items: Availability[]) => request<Availability[]>("POST", "/api/availability/bulk", { body: { items } }),

  // Obsada
  assignments: (p: Period) => request<Assignment[]>("GET", "/api/assignments", { query: { ...p } }),
  board: (p: Period) => request<BoardItem[]>("GET", "/api/assignments/board", { query: { ...p } }),
  candidates: (matchId: number, role: RefereeRole = "MAIN") =>
    request<Candidate[]>("GET", "/api/assignments/candidates", { query: { match_id: matchId, role } }),
  assign: (matchId: number, refereeId: number, role: RefereeRole = "MAIN") =>
    request<ManualAssignmentResult>("POST", "/api/assignments", { body: { match_id: matchId, referee_id: refereeId, role } }),
  deleteAssignment: (id: number) => request<void>("DELETE", `/api/assignments/${id}`),

  exportUrl: (p: Period, format: "pdf" | "xlsx") => fileUrl(`/api/assignments/export.${format}`, { ...p }),

  // Publikacja
  publish: (p: Period) => request<PublicationSummary>("POST", "/api/publications", { body: p }),
  latestPublication: (p: Period) => request<PublicationSummary | null>("GET", "/api/publications/latest", { query: { ...p } }),
  publication: (id: number) => request<Publication>("GET", `/api/publications/${id}`),
  publicationPdfUrl: (id: number) => fileUrl(`/api/publications/${id}/pdf`),

  // Generator
  generate: (p: Period, mode: GenerationMode) => request<GenerationPreview>("POST", "/api/optimization/generate", { body: { ...p, mode } }),
  confirm: (runId: number) => request<ConfirmResponse>("POST", "/api/optimization/confirm", { body: { run_id: runId } }),
  discard: (runId: number) => request<void>("POST", "/api/optimization/discard", { body: { run_id: runId } }),
  pendingPreview: (p: Period) => request<GenerationPreview | null>("GET", "/api/optimization/pending", { query: { ...p } }),

  // Ustawienia i statystyki
  settings: () => request<SystemSettings>("GET", "/api/settings"),
  saveSettings: (s: SystemSettings) => request<SystemSettings>("PUT", "/api/settings", { body: s }),
  dashboard: (p: Period) => request<DashboardStats>("GET", "/api/dashboard", { query: { ...p } }),
  statistics: (p: Period) => request<PeriodStatistics>("GET", "/api/statistics", { query: { ...p } }),
  mileageXlsxUrl: (p: Period) => fileUrl("/api/statistics/mileage.xlsx", { ...p }),
};
