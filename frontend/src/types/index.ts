// Typy odpowiadające schematom Pydantic backendu (app/schemas).

export type RefereeRole = "MAIN" | "ASSISTANT_1" | "ASSISTANT_2" | "FOURTH" | "OBSERVER";
export type MatchStatus = "UNASSIGNED" | "PARTIALLY_ASSIGNED" | "ASSIGNED" | "CANCELLED";
export type GenerationMode = "KEEP_MANUAL" | "FULL";

export interface RefereeInput {
  first_name: string;
  last_name: string;
  city: string;
  address: string;
  licenses: string[];
  active: boolean;
  preferred_matches_per_day: number;
  max_matches_per_day: number;
  preferred_matches_per_weekend: number;
  max_matches_per_weekend: number;
  notes: string | null;
  /** Preferowane poziomy rozgrywek, np. ["IV liga"]; puste = bez preferencji. */
  preferred_leagues: string[];
  /** Kluby, których mecze sędzia woli omijać (kara w generatorze). */
  avoided_clubs: string[];
  /** Kluby, z którymi sędzia jest związany — nigdy ich nie sędziuje. */
  conflict_clubs: string[];
  own_region_only: boolean;
}

export interface Referee extends RefereeInput {
  id: number;
  district: string;
  /** "Warszawa, Mokotów" albo samo miasto. */
  location_label: string;
  /** Podokręg MZPN, np. "Płock". */
  region: string;
  /** Najwyższa klasa rozgrywkowa jako sędzia główny, np. "IV liga". */
  license_class: string;
  /** Do sortowania klas: mniej = wyższa liga. */
  license_class_rank: number;
  latitude: number;
  longitude: number;
}

export interface DayLoad {
  date: string;
  availability: string;
  matches: number;
}

export interface RefereeOverview {
  referee: Referee;
  days: DayLoad[];
  matches_in_period: number;
}

export interface VenueInput {
  name: string;
  city: string;
  address: string;
  postal_code: string;
}

export interface Venue extends VenueInput {
  id: number;
  latitude: number;
  longitude: number;
  /** Podokręg MZPN (najbliższa siedziba). */
  region: string;
}

export interface GeocodeResult {
  latitude: number;
  longitude: number;
  city: string;
  district: string;
  formatted_address: string;
}

export interface MatchInput {
  external_id: string | null;
  date: string;
  start_time: string;
  estimated_end_time: string;
  league: string;
  home_team: string;
  away_team: string;
  venue_id: number;
  required_referees: number;
  status?: MatchStatus | null;
}

export interface MatchAssignmentBrief {
  id: number;
  referee_id: number;
  referee_name: string;
  role: RefereeRole;
  manually_modified: boolean;
  score: number | null;
  distance_km: number | null;
  travel_minutes: number | null;
}

export interface Match extends MatchInput {
  id: number;
  status: MatchStatus;
  venue: Venue;
  assignments: MatchAssignmentBrief[];
}

export interface Availability {
  id?: number;
  referee_id: number;
  date: string;
  available_from: string | null;
  available_to: string | null;
  available: boolean;
  declared_by_referee?: boolean;
  declared_at?: string | null;
}

export interface OwnAvailabilitySave {
  items: { date: string; available: boolean; available_from: string | null; available_to: string | null }[];
  cleared: string[];
}

export interface MyMatch {
  match_id: number;
  date: string;
  start_time: string;
  league: string;
  home_team: string;
  away_team: string;
  venue_name: string;
  venue_address: string;
  cancelled: boolean;
  role: RefereeRole;
  role_label: string;
  distance_km: number | null;
  crew: { role: RefereeRole; role_label: string; referee_name: string | null }[];
  version: number;
  published_at: string;
}

export interface Explanation {
  reasons: string[];
  score_breakdown?: Record<string, number>;
  origin?: string;
  rejection?: string | null;
  manual?: boolean;
}

export interface Assignment {
  id: number;
  match_id: number;
  referee_id: number;
  referee_name: string;
  referee_licenses: string[];
  referee_location: string;
  role: RefereeRole;
  manually_modified: boolean;
  score: number | null;
  distance_km: number | null;
  travel_minutes: number | null;
  explanation: Explanation | null;
  conflict: string | null;
}

export interface BoardItem {
  match_id: number;
  date: string;
  start_time: string;
  estimated_end_time: string;
  league: string;
  home_team: string;
  away_team: string;
  venue_name: string;
  status: MatchStatus;
  required_roles: RefereeRole[];
  assignments: Assignment[];
}

export interface Candidate {
  referee_id: number;
  referee_name: string;
  referee_licenses: string[];
  referee_location: string;
  feasible: boolean;
  score: number | null;
  distance_km: number | null;
  travel_minutes: number | null;
  reasons: string[];
  rejection: string | null;
  score_breakdown: Record<string, number>;
}

export interface ManualAssignmentResult {
  assignment: Assignment;
  warning: string | null;
}

export interface MatchInfo {
  match_id: number;
  date: string;
  start_time: string;
  end_time: string;
  league: string;
  home_team: string;
  away_team: string;
  venue_name: string;
}

export interface ProposedAssignment {
  match: MatchInfo;
  role: RefereeRole;
  referee_id: number;
  referee_name: string;
  referee_licenses: string[];
  referee_location: string;
  score: number | null;
  distance_km: number | null;
  travel_minutes: number | null;
  manually_modified: boolean;
  explanation: Explanation;
  conflict: string | null;
}

export interface ReasonCount {
  code: string;
  label: string;
  count: number;
}

export interface UnassignedSlot {
  match: MatchInfo;
  role: RefereeRole;
  reasons: ReasonCount[];
  rejected_examples: { referee: string; reason: string }[];
}

export interface GenerationStats {
  matches_total: number;
  matches_assigned: number;
  matches_unassigned: number;
  slots_total: number;
  slots_assigned: number;
  active_referees: number;
  referees_used: number;
  avg_matches_per_referee: number;
  avg_distance_km: number;
  total_distance_km: number;
  conflicts: number;
}

export interface GenerationPreview {
  run_id: number;
  status: "PREVIEW" | "CONFIRMED" | "DISCARDED";
  params: { date_from: string; date_to: string; mode: GenerationMode };
  stats: GenerationStats;
  assignments: ProposedAssignment[];
  unassigned: UnassignedSlot[];
}

export interface ConfirmResponse {
  run_id: number;
  saved_assignments: number;
  kept_manual: number;
  skipped: number;
  stats: GenerationStats;
}

export interface DashboardStats {
  date_from: string;
  date_to: string;
  matches_total: number;
  matches_assigned: number;
  matches_unassigned: number;
  available_referees: number;
  active_referees: number;
  avg_matches_per_referee: number;
  total_distance_km: number;
  avg_distance_km: number;
  conflicts: number;
}

export interface SystemSettings {
  transport_safety_buffer_minutes: number;
  arrival_before_minutes: number;
  generator_max_matches_per_day: number;
  women_priority_penalty: number;
  crew_route_weight: number;
  preferred_league_penalty: number;
  avoided_club_penalty: number;
  distance_weight: number;
  travel_time_weight: number;
  daily_match_weight: number;
  weekend_match_weight: number;
  workload_balance_weight: number;
  within_preferred_factor: number;
  over_preferred_factor: number;
  distance_brackets: [number, number][];
  assume_available_without_entry: boolean;
  routing_road_factor: number;
  routing_avg_speed_kmh: number;
  default_match_duration_minutes: number;
}

export interface ImportResult {
  created: number;
  updated: number;
  errors: string[];
}

/** Licencja z katalogu backendu (app/optimization/licenses.py) z opisem uprawnień. */
export interface LicenseInfo {
  name: string;
  scope: string;
  assumption: string | null;
}

export interface LicenseGroup {
  title: string;
  licenses: LicenseInfo[];
}

export type UserRole = "ADMIN" | "REFEREE";

export const USER_ROLE_LABELS: Record<UserRole, string> = {
  ADMIN: "Obsadzający",
  REFEREE: "Sędzia",
};

export interface User {
  id: number;
  login: string;
  display_name: string;
  role: UserRole;
  referee_id: number | null;
  referee_name: string | null;
  active: boolean;
  last_login_at: string | null;
}

export interface UserInput {
  display_name: string;
  role: UserRole;
  referee_id: number | null;
  active: boolean;
}

export interface UserWithPassword {
  user: User;
  password: string | null;
}

export interface PublicationSummary {
  id: number;
  date_from: string;
  date_to: string;
  version: number;
  published_at: string;
  match_count: number;
  changed_matches: number[];
}

export interface PublishedCrewMember {
  role: RefereeRole;
  referee_id: number | null;
  referee_name: string | null;
  distance_km: number | null;
}

export interface PublishedRow {
  match_id: number;
  date: string;
  start_time: string;
  league: string;
  home_team: string;
  away_team: string;
  venue_name: string;
  venue_address: string;
  cancelled: boolean;
  crew: PublishedCrewMember[];
}

export interface Publication extends PublicationSummary {
  rows: PublishedRow[];
}

export const ROLE_LABELS: Record<RefereeRole, string> = {
  MAIN: "Sędzia główny",
  ASSISTANT_1: "Asystent 1",
  ASSISTANT_2: "Asystent 2",
  FOURTH: "Sędzia techniczny",
  OBSERVER: "Obserwator",
};

export const STATUS_LABELS: Record<MatchStatus, string> = {
  UNASSIGNED: "Brak obsady",
  PARTIALLY_ASSIGNED: "Częściowa obsada",
  ASSIGNED: "Obsadzony",
  CANCELLED: "Odwołany",
};
