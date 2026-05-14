"use client";

import Link from "next/link";
import type { TeamDetail, TeamEventResult, EventMatch } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend,
} from "recharts";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";

function matchLabel(m: EventMatch) {
  if (m.tournament_level === "QUALIFICATION") return `Q${m.match_number}`;
  return `E${m.match_number}`;
}

function TeamLink({ num }: { num: number | null }) {
  if (!num) return <span className="text-muted-foreground">—</span>;
  return (
    <Link href={`/team/${num}`} className="text-blue-400 hover:underline font-mono">
      {num}
    </Link>
  );
}

function EventCard({ ev }: { ev: TeamEventResult }) {
  const rec = ev.record;
  const epa = ev.epa_end;

  return (
    <Card>
      <CardHeader className="pb-2 pt-4 px-4">
        <div className="flex items-start justify-between gap-2 flex-wrap">
          <div>
            <Link
              href={`/event/${ev.event_code}`}
              className="font-semibold text-sm hover:underline"
            >
              {ev.name}
            </Link>
            <p className="text-xs text-muted-foreground mt-0.5">
              {[ev.city, ev.state_prov].filter(Boolean).join(", ")}
              {" · "}
              {ev.start_date?.slice(0, 10)}
            </p>
          </div>
          <Badge variant="secondary" className="shrink-0">{ev.type}</Badge>
        </div>
      </CardHeader>

      <CardContent className="px-4 pb-4 space-y-4">
        {/* Stats row */}
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
          <div>
            <p className="text-[10px] uppercase tracking-wide text-muted-foreground">Record</p>
            <p className="font-mono font-bold text-sm">{rec.wins}-{rec.losses}-{rec.ties}</p>
          </div>
          {epa && (
            <>
              <div>
                <p className="text-[10px] uppercase tracking-wide text-muted-foreground">EPA</p>
                <p className="font-mono font-bold text-sm">{epa.total_epa.toFixed(1)}</p>
              </div>
              <div>
                <p className="text-[10px] uppercase tracking-wide text-muted-foreground text-green-400">Auto</p>
                <p className="font-mono font-bold text-sm text-green-400">{epa.auto_epa.toFixed(1)}</p>
              </div>
              <div>
                <p className="text-[10px] uppercase tracking-wide text-muted-foreground text-blue-400">Teleop</p>
                <p className="font-mono font-bold text-sm text-blue-400">{epa.teleop_epa.toFixed(1)}</p>
              </div>
              <div>
                <p className="text-[10px] uppercase tracking-wide text-muted-foreground text-purple-400">Endgame</p>
                <p className="font-mono font-bold text-sm text-purple-400">{epa.endgame_epa.toFixed(1)}</p>
              </div>
            </>
          )}
        </div>

        {/* Match table */}
        {ev.matches.length > 0 && (
          <div className="rounded-md border border-border overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow className="text-xs text-muted-foreground">
                  <TableHead className="w-12">Match</TableHead>
                  <TableHead>Alliance</TableHead>
                  <TableHead>Partner</TableHead>
                  <TableHead>Opponents</TableHead>
                  <TableHead className="text-right">Score</TableHead>
                  <TableHead className="text-right hidden sm:table-cell">Predicted</TableHead>
                  <TableHead className="text-center w-12">Result</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {ev.matches.map((m, i) => {
                  const isRed = m.alliance === "RED";
                  const allianceColor = isRed ? "text-red-400" : "text-blue-400";
                  const resultColor =
                    m.result === "W" ? "text-green-400" :
                    m.result === "L" ? "text-red-400" :
                    "text-muted-foreground";

                  return (
                    <TableRow key={i} className="text-sm">
                      <TableCell className="font-mono text-muted-foreground">
                        {matchLabel(m)}
                      </TableCell>
                      <TableCell>
                        <span className={`font-semibold text-xs ${allianceColor}`}>
                          {m.alliance}
                        </span>
                      </TableCell>
                      <TableCell>
                        <TeamLink num={m.partner} />
                      </TableCell>
                      <TableCell>
                        <span className="flex gap-2">
                          <TeamLink num={m.opp1} />
                          <TeamLink num={m.opp2} />
                        </span>
                      </TableCell>
                      <TableCell className="text-right font-mono">
                        {m.alliance_score ?? "—"}
                        <span className="text-muted-foreground"> – </span>
                        {m.opp_score ?? "—"}
                      </TableCell>
                      <TableCell className="text-right font-mono text-muted-foreground hidden sm:table-cell">
                        {m.predicted_alliance?.toFixed(0) ?? "—"}
                        <span> – </span>
                        {m.predicted_opp?.toFixed(0) ?? "—"}
                      </TableCell>
                      <TableCell className="text-center">
                        <span className={`font-bold text-xs ${resultColor}`}>
                          {m.result ?? "—"}
                        </span>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

const EPA_LINES = [
  { key: "total_epa" as const, label: "Total EPA", color: "#60a5fa" },
  { key: "auto_epa" as const, label: "Auto", color: "#4ade80" },
  { key: "teleop_epa" as const, label: "Teleop", color: "#818cf8" },
  { key: "endgame_epa" as const, label: "Endgame", color: "#c084fc" },
];

export function TeamClient({ team }: { team: TeamDetail }) {
  const chartData = team.epa_history.map((pt, i) => ({
    match: i + 1,
    label: `${pt.event_code} Q${pt.match_number}`,
    total_epa: pt.total_epa,
    auto_epa: pt.auto_epa,
    teleop_epa: pt.teleop_epa,
    endgame_epa: pt.endgame_epa,
  }));

  const record = `${team.wins}-${team.losses}-${team.ties}`;

  return (
    <div className="space-y-6">
      <div>
        <Link href="/" className="text-xs text-muted-foreground hover:text-foreground">
          ← Rankings
        </Link>
        <h1 className="text-2xl font-bold mt-1">
          Team {team.team_number}
          {team.name && (
            <span className="ml-2 text-muted-foreground font-normal text-lg">{team.name}</span>
          )}
        </h1>
        <p className="text-sm text-muted-foreground">
          {[team.city, team.state_prov, team.country].filter(Boolean).join(", ")}
          {team.team_info?.rookie_year && (
            <span className="ml-2">· Rookie {team.team_info.rookie_year}</span>
          )}
        </p>
      </div>

      <div className="grid grid-cols-3 gap-4">
        {[
          { label: "World Rank", rank: team.rank, total: team.world_total, sub: null },
          { label: "Country Rank", rank: team.country_rank, total: team.country_total, sub: team.country },
          { label: "State / Province Rank", rank: team.state_rank, total: team.state_total, sub: team.state_prov },
        ].map(({ label, rank, total, sub }) => (
          <Card key={label}>
            <CardHeader className="pb-1 pt-4 px-4">
              <CardTitle className="text-xs text-muted-foreground font-medium uppercase tracking-wide">
                {label}
              </CardTitle>
            </CardHeader>
            <CardContent className="px-4 pb-4">
              <p className="text-2xl font-bold font-mono">#{rank ?? "—"}</p>
              <p className="text-xs text-muted-foreground">
                of {total?.toLocaleString() ?? "—"}{sub ? ` · ${sub}` : ""}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[
          { label: "EPA", value: team.total_epa, color: "text-foreground" },
          { label: "Auto EPA", value: team.auto_epa, color: "text-green-400" },
          { label: "Teleop EPA", value: team.teleop_epa, color: "text-blue-400" },
          { label: "Endgame EPA", value: team.endgame_epa, color: "text-purple-400" },
        ].map(({ label, value, color }) => (
          <Card key={label}>
            <CardHeader className="pb-1 pt-4 px-4">
              <CardTitle className="text-xs text-muted-foreground font-medium uppercase tracking-wide">
                {label}
              </CardTitle>
            </CardHeader>
            <CardContent className="px-4 pb-4">
              <p className={`text-2xl font-bold font-mono ${color}`}>{value?.toFixed(2) ?? "—"}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[
          { label: "Movement RP%", value: team.movement_rp },
          { label: "Goal RP%", value: team.goal_rp },
          { label: "Pattern RP%", value: team.pattern_rp },
        ].map(({ label, value }) => (
          <Card key={label}>
            <CardHeader className="pb-1 pt-4 px-4">
              <CardTitle className="text-xs text-muted-foreground font-medium uppercase tracking-wide">
                {label}
              </CardTitle>
            </CardHeader>
            <CardContent className="px-4 pb-4">
              <p className="text-2xl font-bold font-mono">{((value ?? 0) * 100).toFixed(1)}%</p>
            </CardContent>
          </Card>
        ))}
        <Card>
          <CardHeader className="pb-1 pt-4 px-4">
            <CardTitle className="text-xs text-muted-foreground font-medium uppercase tracking-wide">
              Record
            </CardTitle>
          </CardHeader>
          <CardContent className="px-4 pb-4">
            <p className="text-2xl font-bold font-mono">{record}</p>
            <p className="text-xs text-muted-foreground">{team.qual_n} qual matches</p>
          </CardContent>
        </Card>
      </div>

      {chartData.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">EPA Over Season</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={chartData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                <XAxis dataKey="match" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} width={45} />
                <Tooltip
                  contentStyle={{ background: "#1e1e1e", border: "1px solid #333", fontSize: 12 }}
                  labelFormatter={(v) => chartData[Number(v) - 1]?.label ?? v}
                />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                {EPA_LINES.map(({ key, label, color }) => (
                  <Line
                    key={key}
                    type="monotone"
                    dataKey={key}
                    name={label}
                    stroke={color}
                    dot={false}
                    strokeWidth={2}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      {team.events?.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-lg font-semibold">Events</h2>
          {team.events.map((ev) => (
            <EventCard key={ev.event_code} ev={ev} />
          ))}
        </div>
      )}
    </div>
  );
}
