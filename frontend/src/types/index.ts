// Typy odpowiadające schematom Pydantic backendu (app/schemas).

export type RefereeRole = "MAIN" | "ASSISTANT_1" | "ASSISTANT_2" | "FOURTH" | "OBSERVER";
export type MatchStatus = "UNASSIGNED" | "PARTIALLY_ASSIGNED" | "ASSIGNED" | "CANCELLED";
export type GenerationMode = "KEEP_MANUAL" | "FULL";

export interface RefereeInput {
  first_name: string;
  last_name: string;
  city: string;
  address: string;
  latitude: number;
  longitude: number;
  active: boolean;
  preferred_matches_per_day: number;
  max_matches_per_day: number;
  preferred_matches_per_weekend: number;
  max_matches_per_weekend: number;
  notes: string | null;
}

export interface Referee extends RefereeInput {
  id: number;
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
  latitude: number;
  longitude: number;
}

export interface Venue extends VenueInput {
  id: number;
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
  arrival_before_minutes: number;
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
