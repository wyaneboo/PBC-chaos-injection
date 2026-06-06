import { Activity, CheckCircle2, Circle, Clock3, SkipForward, XCircle } from "lucide-react";
import { useState } from "react";
import { RunEvent, RunSnapshot } from "../lib/api";
import { ModeId } from "../lib/optionSchema";
import { lastEventByStage, latestEvent, stagesForMode } from "../lib/progressEvents";

interface ProgressTimelineProps {
  mode: ModeId;
  run: RunSnapshot | null;
}

export function ProgressTimeline({ mode, run }: ProgressTimelineProps) {
  const events = run?.events ?? [];
  const latest = latestEvent(events);
  const byStage = lastEventByStage(events);
  const percent = latest?.overall_percent ?? 0;
  const activeWorkbook = [...events].reverse().find((event) => event.workbook)?.workbook;

  return (
    <section className="progressPane" aria-label="Pipeline progress">
      <div className="runHeader">
        <div>
          <h2>Pipeline Progress</h2>
          <p>{run ? `${run.status.toUpperCase()} · ${run.run_id}` : "Ready to run"}</p>
        </div>
        <div className="percentReadout">{Math.round(percent)}%</div>
      </div>
      <div className="progressBar" aria-label="Overall progress">
        <span style={{ width: `${percent}%` }} />
      </div>
      <div className="progressGrid">
        <ol className="timeline">
          {stagesForMode(mode).map((stage) => {
            const event = byStage.get(stage.id);
            const status = event?.status ?? "queued";
            const Icon = statusIcon(status);
            return (
              <li className={`timelineItem ${status}`} key={stage.id}>
                <Icon size={16} />
                <div>
                  <strong>{stage.label}</strong>
                  <span>{event?.message ?? "Queued"}</span>
                </div>
              </li>
            );
          })}
        </ol>
        <div className="activeWorkbook">
          <h3>Active Workbook</h3>
          {activeWorkbook ? (
            <>
              <strong>{activeWorkbook.company_name}</strong>
              <span>
                Workbook {activeWorkbook.index} of {activeWorkbook.total} · chaos {activeWorkbook.chaos_level}
              </span>
              <div className="miniBar">
                <span style={{ width: `${Math.round(activeWorkbook.stage_percent * 100)}%` }} />
              </div>
            </>
          ) : (
            <>
              <strong>No active workbook</strong>
              <span>Batch and dataset runs will show company-level progress here.</span>
              <div className="miniBar">
                <span style={{ width: "0%" }} />
              </div>
            </>
          )}
          <EventLog events={events} />
        </div>
      </div>
    </section>
  );
}

function EventLog({ events }: { events: RunEvent[] }) {
  const levels = ["all", "info", "warning", "error"];
  const [activeLevel, setActiveLevel] = useEventFilter();
  const filtered = activeLevel === "all" ? events : events.filter((event) => event.severity === activeLevel);

  return (
    <div className="eventLog">
      <div className="eventToolbar">
        <h3>Event Log</h3>
        <div>
          {levels.map((level) => (
            <button
              className={activeLevel === level ? "tinyTab active" : "tinyTab"}
              key={level}
              onClick={() => setActiveLevel(level)}
              type="button"
            >
              {level}
            </button>
          ))}
        </div>
      </div>
      <div className="eventRows">
        {filtered.length ? (
          filtered.slice(-8).map((event, index) => (
            <div className={`eventRow ${event.severity ?? "info"}`} key={`${event.stage_id}-${index}`}>
              <time>{event.timestamp?.split("T").at(-1) ?? "--:--"}</time>
              <span>{event.stage_label}</span>
              <p>{event.message}</p>
            </div>
          ))
        ) : (
          <p className="emptyText">No events yet.</p>
        )}
      </div>
    </div>
  );
}

function statusIcon(status: string) {
  if (status === "succeeded") return CheckCircle2;
  if (status === "failed") return XCircle;
  if (status === "running") return Activity;
  if (status === "skipped") return SkipForward;
  if (status === "warning") return Clock3;
  return Circle;
}

function useEventFilter(): [string, (value: string) => void] {
  return useState("all");
}
