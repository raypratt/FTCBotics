"use client";

import { useEffect, useState, useMemo, useRef, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { getTeams, getMeta, getEvents } from "@/lib/data";
import type { TeamSummary, Meta, EventSummary } from "@/lib/types";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const EPA_COLS = [
  { key: "total_epa" as const, label: "EPA" },
  { key: "auto_epa" as const, label: "Auto" },
  { key: "teleop_epa" as const, label: "Teleop" },
  { key: "endgame_epa" as const, label: "Endgame" },
];

type SortKey = "rank" | "total_epa" | "auto_epa" | "teleop_epa" | "endgame_epa" | "wins";

type SearchResult =
  | { kind: "team"; href: string; primary: string; secondary: string }
  | { kind: "event"; href: string; primary: string; secondary: string; badge: string };

export default function Home() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const [teams, setTeams] = useState<TeamSummary[]>([]);
  const [events, setEvents] = useState<EventSummary[]>([]);
  const [meta, setMeta] = useState<Meta | null>(null);
  const [search, setSearch] = useState("");
  const [open, setOpen] = useState(false);
  const [activeIdx, setActiveIdx] = useState(-1);
  const [sortKey, setSortKey] = useState<SortKey>("rank");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");

  useEffect(() => {
    getTeams().then(setTeams).catch(console.error);
    getMeta().then(setMeta).catch(console.error);
    getEvents().then(setEvents).catch(console.error);
  }, []);

  const results: SearchResult[] = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return [];

    const teamHits: SearchResult[] = teams
      .filter(
        (t) =>
          String(t.team_number).includes(q) ||
          t.name?.toLowerCase().includes(q) ||
          t.city?.toLowerCase().includes(q) ||
          t.state_prov?.toLowerCase().includes(q)
      )
      .slice(0, 5)
      .map((t) => ({
        kind: "team",
        href: `/team/${t.team_number}`,
        primary: `${t.team_number} – ${t.name || "Unknown"}`,
        secondary: [t.city, t.state_prov, t.country].filter(Boolean).join(", "),
      }));

    const eventHits: SearchResult[] = events
      .filter(
        (e) =>
          e.event_code.toLowerCase().includes(q) ||
          e.name?.toLowerCase().includes(q) ||
          e.city?.toLowerCase().includes(q) ||
          e.state_prov?.toLowerCase().includes(q)
      )
      .slice(0, 5)
      .map((e) => ({
        kind: "event",
        href: `/event/${e.event_code}`,
        primary: e.name || e.event_code,
        secondary: [e.city, e.state_prov, e.start_date?.slice(0, 10)].filter(Boolean).join(" · "),
        badge: e.event_code,
      }));

    return [...teamHits, ...eventHits];
  }, [search, teams, events]);

  useEffect(() => { setActiveIdx(-1); }, [results]);

  const navigate = useCallback(
    (idx: number) => {
      const target = results[idx] ?? results[0];
      if (target) {
        setOpen(false);
        setSearch("");
        router.push(target.href);
      }
    },
    [results, router]
  );

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (!open) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIdx((i) => Math.min(i + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIdx((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      navigate(activeIdx >= 0 ? activeIdx : 0);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  }

  // Close dropdown when clicking outside
  useEffect(() => {
    function onPointerDown(e: PointerEvent) {
      if (
        !inputRef.current?.contains(e.target as Node) &&
        !dropdownRef.current?.contains(e.target as Node)
      ) {
        setOpen(false);
      }
    }
    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, []);

  const filtered = useMemo(() => {
    const q = search.toLowerCase();
    return teams.filter(
      (t) =>
        !q ||
        String(t.team_number).includes(q) ||
        t.name?.toLowerCase().includes(q) ||
        t.city?.toLowerCase().includes(q) ||
        t.state_prov?.toLowerCase().includes(q)
    );
  }, [teams, search]);

  const sorted = useMemo(() => {
    return [...filtered].sort((a, b) => {
      const v = (t: TeamSummary): number =>
        sortKey === "rank" ? t.rank : (t[sortKey as keyof TeamSummary] as number);
      return sortDir === "asc" ? v(a) - v(b) : v(b) - v(a);
    });
  }, [filtered, sortKey, sortDir]);

  function toggleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir(key === "rank" ? "asc" : "desc");
    }
  }

  function SortHead({ col, label }: { col: SortKey; label: string }) {
    const active = sortKey === col;
    return (
      <TableHead
        className="cursor-pointer select-none whitespace-nowrap hover:text-foreground"
        onClick={() => toggleSort(col)}
      >
        {label}
        {active && (
          <span className="ml-1 text-blue-400">{sortDir === "asc" ? "↑" : "↓"}</span>
        )}
      </TableHead>
    );
  }

  const updatedAt = meta?.updated_at
    ? new Date(meta.updated_at).toLocaleString()
    : null;

  const teamResults = results.filter((r) => r.kind === "team");
  const eventResults = results.filter((r) => r.kind === "event");

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold">2025–26 Team Rankings</h1>
          {updatedAt && (
            <p className="text-xs text-muted-foreground mt-1">Updated {updatedAt}</p>
          )}
        </div>

        {/* Search box with dropdown */}
        <div className="relative w-72">
          <input
            ref={inputRef}
            type="search"
            placeholder="Search teams or events..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setOpen(true);
            }}
            onFocus={() => { if (search.trim()) setOpen(true); }}
            onKeyDown={handleKeyDown}
            className="border border-border rounded-md px-3 py-1.5 text-sm bg-background w-full focus:outline-none focus:ring-1 focus:ring-blue-500"
          />

          {open && results.length > 0 && (
            <div
              ref={dropdownRef}
              className="absolute z-50 top-full mt-1 w-full rounded-md border border-border bg-background shadow-lg overflow-hidden"
            >
              {teamResults.length > 0 && (
                <>
                  <p className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground bg-muted/40">
                    Teams
                  </p>
                  {teamResults.map((r, localIdx) => {
                    const globalIdx = results.indexOf(r);
                    return (
                      <button
                        key={r.href}
                        className={`w-full text-left px-3 py-2 text-sm hover:bg-muted/50 transition-colors ${
                          globalIdx === activeIdx ? "bg-muted/70" : ""
                        }`}
                        onPointerEnter={() => setActiveIdx(globalIdx)}
                        onPointerDown={(e) => {
                          e.preventDefault();
                          navigate(globalIdx);
                        }}
                      >
                        <p className="font-medium truncate">{r.primary}</p>
                        {r.secondary && (
                          <p className="text-xs text-muted-foreground truncate">{r.secondary}</p>
                        )}
                      </button>
                    );
                  })}
                </>
              )}

              {eventResults.length > 0 && (
                <>
                  <p className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground bg-muted/40">
                    Events
                  </p>
                  {eventResults.map((r) => {
                    const globalIdx = results.indexOf(r);
                    return (
                      <button
                        key={r.href}
                        className={`w-full text-left px-3 py-2 text-sm hover:bg-muted/50 transition-colors ${
                          globalIdx === activeIdx ? "bg-muted/70" : ""
                        }`}
                        onPointerEnter={() => setActiveIdx(globalIdx)}
                        onPointerDown={(e) => {
                          e.preventDefault();
                          navigate(globalIdx);
                        }}
                      >
                        <div className="flex items-center gap-2">
                          <p className="font-medium truncate flex-1">{r.primary}</p>
                          {"badge" in r && (
                            <Badge variant="secondary" className="text-[10px] shrink-0">
                              {r.badge}
                            </Badge>
                          )}
                        </div>
                        {r.secondary && (
                          <p className="text-xs text-muted-foreground truncate">{r.secondary}</p>
                        )}
                      </button>
                    );
                  })}
                </>
              )}
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {EPA_COLS.map(({ key, label }) => {
          const vals = teams.map((t) => t[key]).filter((v) => v > 0);
          const avg = vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : 0;
          const max = vals.length ? Math.max(...vals) : 0;
          return (
            <Card key={key}>
              <CardHeader className="pb-1 pt-4 px-4">
                <CardTitle className="text-xs text-muted-foreground font-medium uppercase tracking-wide">
                  Avg {label} EPA
                </CardTitle>
              </CardHeader>
              <CardContent className="px-4 pb-4">
                <p className="text-2xl font-bold">{avg.toFixed(1)}</p>
                <p className="text-xs text-muted-foreground">Max {max.toFixed(1)}</p>
              </CardContent>
            </Card>
          );
        })}
      </div>

      <div className="rounded-md border border-border overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="text-xs text-muted-foreground">
              <SortHead col="rank" label="Rank" />
              <TableHead>Team</TableHead>
              <TableHead className="hidden sm:table-cell">Location</TableHead>
              <SortHead col="total_epa" label="EPA" />
              <SortHead col="auto_epa" label="Auto" />
              <SortHead col="teleop_epa" label="Teleop" />
              <SortHead col="endgame_epa" label="Endgame" />
              <SortHead col="wins" label="Record" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {sorted.length === 0 && (
              <TableRow>
                <TableCell colSpan={8} className="text-center text-muted-foreground py-12">
                  {teams.length === 0 ? "Loading..." : "No teams match your search."}
                </TableCell>
              </TableRow>
            )}
            {sorted.map((team) => (
              <TableRow key={team.team_number} className="hover:bg-muted/50">
                <TableCell className="font-mono text-muted-foreground w-12">
                  {team.rank}
                </TableCell>
                <TableCell>
                  <Link
                    href={`/team/${team.team_number}`}
                    className="font-semibold text-blue-400 hover:underline"
                  >
                    {team.team_number}
                  </Link>
                  <p className="text-xs text-muted-foreground truncate max-w-[160px]">
                    {team.name}
                  </p>
                </TableCell>
                <TableCell className="hidden sm:table-cell text-sm text-muted-foreground">
                  {[team.city, team.state_prov].filter(Boolean).join(", ")}
                </TableCell>
                <TableCell className="font-mono font-semibold">
                  {team.total_epa.toFixed(1)}
                </TableCell>
                <TableCell className="font-mono text-green-400">
                  {team.auto_epa.toFixed(1)}
                </TableCell>
                <TableCell className="font-mono text-blue-400">
                  {team.teleop_epa.toFixed(1)}
                </TableCell>
                <TableCell className="font-mono text-purple-400">
                  {team.endgame_epa.toFixed(1)}
                </TableCell>
                <TableCell className="text-sm text-muted-foreground whitespace-nowrap">
                  {team.wins}-{team.losses}-{team.ties}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
