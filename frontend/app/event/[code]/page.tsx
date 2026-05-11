import fs from "fs";
import path from "path";
import { notFound } from "next/navigation";
import type { EventDetail, EventSummary } from "@/lib/types";
import { EventClient } from "./EventClient";

const DATA = path.join(process.cwd(), "public", "data");

export function generateStaticParams(): { code: string }[] {
  try {
    const raw = fs.readFileSync(path.join(DATA, "events.json"), "utf8");
    const events: EventSummary[] = JSON.parse(raw);
    return events.map((e) => ({ code: e.event_code }));
  } catch {
    return [];
  }
}

export default async function EventPage({
  params,
}: {
  params: Promise<{ code: string }>;
}) {
  const { code } = await params;

  let data: EventDetail;
  try {
    const raw = fs.readFileSync(path.join(DATA, "event", `${code}.json`), "utf8");
    data = JSON.parse(raw);
  } catch {
    notFound();
  }

  return <EventClient data={data!} />;
}
