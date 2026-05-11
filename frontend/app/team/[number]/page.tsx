import fs from "fs";
import path from "path";
import { notFound } from "next/navigation";
import type { TeamDetail, TeamSummary } from "@/lib/types";
import { TeamClient } from "./TeamClient";

const DATA = path.join(process.cwd(), "public", "data");

export function generateStaticParams(): { number: string }[] {
  try {
    const raw = fs.readFileSync(path.join(DATA, "teams.json"), "utf8");
    const teams: TeamSummary[] = JSON.parse(raw);
    return teams.map((t) => ({ number: String(t.team_number) }));
  } catch {
    return [];
  }
}

export default async function TeamPage({
  params,
}: {
  params: Promise<{ number: string }>;
}) {
  const { number } = await params;

  let team: TeamDetail;
  try {
    const raw = fs.readFileSync(path.join(DATA, "team", `${number}.json`), "utf8");
    team = JSON.parse(raw);
  } catch {
    notFound();
  }

  return <TeamClient team={team!} />;
}
