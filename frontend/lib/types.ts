export interface TeamSummary {
  team_number: number;
  name: string;
  city: string;
  state_prov: string;
  country: string;
  home_region: string | null;
  total_epa: number;
  auto_epa: number;
  teleop_epa: number;
  endgame_epa: number;
  movement_rp: number;
  goal_rp: number;
  pattern_rp: number;
  qual_n: number;
  wins: number;
  losses: number;
  ties: number;
  avg_score: number;
  rank: number;
}

export interface EPAHistoryPoint {
  total_epa: number;
  auto_epa: number;
  teleop_epa: number;
  endgame_epa: number;
  movement_rp: number;
  goal_rp: number;
  pattern_rp: number;
  qual_n: number;
  event_code: string;
  match_number: number;
  tournament_level: string;
  actual_start: string | null;
}

export interface TeamDetail extends TeamSummary {
  team_info: {
    team_number: number;
    name: string;
    city: string;
    state_prov: string;
    country: string;
    rookie_year: number | null;
  };
  epa_history: EPAHistoryPoint[];
  events: EventSummary[];
}

export interface EventSummary {
  event_code: string;
  name: string;
  type: string;
  start_date: string;
  end_date: string;
  city: string;
  state_prov: string;
  country: string;
}

export interface Match {
  id: number;
  match_number: number;
  tournament_level: string;
  series: number;
  actual_start: string | null;
  red1: number;
  red2: number;
  blue1: number;
  blue2: number;
  red_score: number | null;
  blue_score: number | null;
  red_auto: number | null;
  blue_auto: number | null;
}

export interface EventTeamEPA {
  team_number: number;
  name: string;
  total_epa: number;
  auto_epa: number;
  teleop_epa: number;
  endgame_epa: number;
  qual_n: number;
}

export interface EventDetail {
  event: EventSummary;
  matches: Match[];
  team_epas: EventTeamEPA[];
}

export interface Meta {
  season: number;
  updated_at: string;
}
