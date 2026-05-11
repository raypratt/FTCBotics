"use client";

import Link from "next/link";
import type { TeamDetail } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend,
} from "recharts";

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
        <div>
          <h2 className="text-lg font-semibold mb-3">Events</h2>
          <div className="space-y-2">
            {team.events.map((ev) => (
              <Link
                key={ev.event_code}
                href={`/event/${ev.event_code}`}
                className="flex items-center justify-between p-3 rounded-md border border-border hover:bg-muted/50 transition-colors"
              >
                <div>
                  <p className="font-medium text-sm">{ev.name}</p>
                  <p className="text-xs text-muted-foreground">
                    {ev.city && `${ev.city}, `}{ev.state_prov} · {ev.start_date?.slice(0, 10)}
                  </p>
                </div>
                <Badge variant="secondary">{ev.type}</Badge>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
