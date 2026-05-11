"use client";

import Link from "next/link";
import type { EventDetail, Match } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";

function MatchRow({ match }: { match: Match }) {
  const isQual = match.tournament_level === "QUALIFICATION";
  const redWon = (match.red_score ?? 0) > (match.blue_score ?? 0);
  const blueWon = (match.blue_score ?? 0) > (match.red_score ?? 0);

  return (
    <TableRow className="hover:bg-muted/50 text-sm">
      <TableCell className="text-muted-foreground whitespace-nowrap">
        {isQual ? `Q${match.match_number}` : `E${match.series}-${match.match_number}`}
      </TableCell>
      <TableCell>
        <span className={redWon ? "font-bold" : "text-muted-foreground"}>
          <Link href={`/team/${match.red1}`} className="hover:underline text-red-400">{match.red1}</Link>
          {" / "}
          <Link href={`/team/${match.red2}`} className="hover:underline text-red-400">{match.red2}</Link>
        </span>
      </TableCell>
      <TableCell className={`font-mono font-bold ${redWon ? "text-red-400" : "text-muted-foreground"}`}>
        {match.red_score ?? "—"}
      </TableCell>
      <TableCell className={`font-mono font-bold ${blueWon ? "text-blue-400" : "text-muted-foreground"}`}>
        {match.blue_score ?? "—"}
      </TableCell>
      <TableCell>
        <span className={blueWon ? "font-bold" : "text-muted-foreground"}>
          <Link href={`/team/${match.blue1}`} className="hover:underline text-blue-400">{match.blue1}</Link>
          {" / "}
          <Link href={`/team/${match.blue2}`} className="hover:underline text-blue-400">{match.blue2}</Link>
        </span>
      </TableCell>
      <TableCell className="text-xs text-muted-foreground hidden sm:table-cell">
        {match.actual_start?.slice(11, 16)}
      </TableCell>
    </TableRow>
  );
}

export function EventClient({ data }: { data: EventDetail }) {
  const { event, matches, team_epas } = data;
  const quals = matches.filter((m) => m.tournament_level === "QUALIFICATION");
  const playoffs = matches.filter((m) => m.tournament_level !== "QUALIFICATION");

  return (
    <div className="space-y-6">
      <div>
        <Link href="/events" className="text-xs text-muted-foreground hover:text-foreground">
          ← Events
        </Link>
        <h1 className="text-2xl font-bold mt-1">{event.name}</h1>
        <div className="flex items-center gap-2 mt-1 flex-wrap">
          <Badge>{event.type}</Badge>
          <span className="text-sm text-muted-foreground">
            {[event.city, event.state_prov].filter(Boolean).join(", ")}
            {" · "}
            {event.start_date?.slice(0, 10)}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-1 pt-4 px-4">
            <CardTitle className="text-xs text-muted-foreground font-medium uppercase tracking-wide">Teams</CardTitle>
          </CardHeader>
          <CardContent className="px-4 pb-4">
            <p className="text-2xl font-bold">{team_epas.length}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-1 pt-4 px-4">
            <CardTitle className="text-xs text-muted-foreground font-medium uppercase tracking-wide">Qual Matches</CardTitle>
          </CardHeader>
          <CardContent className="px-4 pb-4">
            <p className="text-2xl font-bold">{quals.length}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-1 pt-4 px-4">
            <CardTitle className="text-xs text-muted-foreground font-medium uppercase tracking-wide">Top EPA</CardTitle>
          </CardHeader>
          <CardContent className="px-4 pb-4">
            <p className="text-2xl font-bold font-mono">{team_epas[0]?.total_epa?.toFixed(1) ?? "—"}</p>
            {team_epas[0] && (
              <p className="text-xs text-muted-foreground">Team {team_epas[0].team_number}</p>
            )}
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="teams">
        <TabsList>
          <TabsTrigger value="teams">Team EPAs</TabsTrigger>
          <TabsTrigger value="quals">Qual Matches</TabsTrigger>
          {playoffs.length > 0 && <TabsTrigger value="playoffs">Playoffs</TabsTrigger>}
        </TabsList>

        <TabsContent value="teams">
          <div className="rounded-md border border-border overflow-hidden mt-4">
            <Table>
              <TableHeader>
                <TableRow className="text-xs text-muted-foreground">
                  <TableHead>Rank</TableHead>
                  <TableHead>Team</TableHead>
                  <TableHead>EPA</TableHead>
                  <TableHead>Auto</TableHead>
                  <TableHead>Teleop</TableHead>
                  <TableHead>Endgame</TableHead>
                  <TableHead>Matches</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {team_epas.map((t, i) => (
                  <TableRow key={t.team_number} className="hover:bg-muted/50">
                    <TableCell className="text-muted-foreground">{i + 1}</TableCell>
                    <TableCell>
                      <Link href={`/team/${t.team_number}`} className="font-semibold text-blue-400 hover:underline">
                        {t.team_number}
                      </Link>
                      <p className="text-xs text-muted-foreground truncate max-w-[140px]">{t.name}</p>
                    </TableCell>
                    <TableCell className="font-mono font-semibold">{t.total_epa?.toFixed(1)}</TableCell>
                    <TableCell className="font-mono text-green-400">{t.auto_epa?.toFixed(1)}</TableCell>
                    <TableCell className="font-mono text-blue-400">{t.teleop_epa?.toFixed(1)}</TableCell>
                    <TableCell className="font-mono text-purple-400">{t.endgame_epa?.toFixed(1)}</TableCell>
                    <TableCell className="text-muted-foreground">{t.qual_n}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </TabsContent>

        <TabsContent value="quals">
          <div className="rounded-md border border-border overflow-hidden mt-4">
            <Table>
              <TableHeader>
                <TableRow className="text-xs text-muted-foreground">
                  <TableHead>Match</TableHead>
                  <TableHead>Red Alliance</TableHead>
                  <TableHead>Red</TableHead>
                  <TableHead>Blue</TableHead>
                  <TableHead>Blue Alliance</TableHead>
                  <TableHead className="hidden sm:table-cell">Time</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {quals.map((m) => <MatchRow key={m.id} match={m} />)}
              </TableBody>
            </Table>
          </div>
        </TabsContent>

        {playoffs.length > 0 && (
          <TabsContent value="playoffs">
            <div className="rounded-md border border-border overflow-hidden mt-4">
              <Table>
                <TableHeader>
                  <TableRow className="text-xs text-muted-foreground">
                    <TableHead>Match</TableHead>
                    <TableHead>Red Alliance</TableHead>
                    <TableHead>Red</TableHead>
                    <TableHead>Blue</TableHead>
                    <TableHead>Blue Alliance</TableHead>
                    <TableHead className="hidden sm:table-cell">Time</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {playoffs.map((m) => <MatchRow key={m.id} match={m} />)}
                </TableBody>
              </Table>
            </div>
          </TabsContent>
        )}
      </Tabs>
    </div>
  );
}
