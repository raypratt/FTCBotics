import type { TeamSummary, TeamDetail, EventSummary, EventDetail, Meta } from "./types";

const BASE = `${process.env.NEXT_PUBLIC_BASE_PATH ?? ""}/data`;

async function fetchJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`Failed to fetch ${path}: ${res.status}`);
  return res.json() as Promise<T>;
}

export const getMeta = () => fetchJSON<Meta>("/meta.json");
export const getTeams = () => fetchJSON<TeamSummary[]>("/teams.json");
export const getEvents = () => fetchJSON<EventSummary[]>("/events.json");
export const getTeam = (num: number) => fetchJSON<TeamDetail>(`/team/${num}.json`);
export const getEvent = (code: string) => fetchJSON<EventDetail>(`/event/${code}.json`);
