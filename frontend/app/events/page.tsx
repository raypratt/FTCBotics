"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getEvents } from "@/lib/data";
import type { EventSummary } from "@/lib/types";
import { Badge } from "@/components/ui/badge";

export default function EventsPage() {
  const [events, setEvents] = useState<EventSummary[]>([]);

  useEffect(() => {
    getEvents().then(setEvents).catch(console.error);
  }, []);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">2025–26 Events</h1>

      {events.length === 0 && (
        <p className="text-muted-foreground">Loading...</p>
      )}

      <div className="space-y-2">
        {events.map((ev) => (
          <Link
            key={ev.event_code}
            href={`/event/${ev.event_code}`}
            className="flex items-center justify-between p-4 rounded-md border border-border hover:bg-muted/50 transition-colors"
          >
            <div>
              <p className="font-semibold">{ev.name}</p>
              <p className="text-sm text-muted-foreground">
                {[ev.city, ev.state_prov, ev.country].filter(Boolean).join(", ")}
                {" · "}
                {ev.start_date?.slice(0, 10)}
                {ev.end_date && ev.end_date !== ev.start_date && ` – ${ev.end_date.slice(0, 10)}`}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant="secondary" className="hidden sm:inline-flex">{ev.event_code}</Badge>
              <Badge>{ev.type}</Badge>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
