import { Activity, CheckCircle2, Circle, Clock3, SkipForward, XCircle } from "lucide-react";
import { useState } from "react";
import type { RunEvent, RunSnapshot } from "../lib/api";
import type { ModeId } from "../lib/optionSchema";
import { lastEventByStage, latestEvent, stagesForMode } from "../lib/progressEvents";

type AgentAction = {
  tool?: string;
  sheet?: string;
  count?: number;
  row_count?: number;
  column_count?: number;
  cells?: string[];
  row?: number;
  request_id?: string;
  text?: string;
  reason?: string;
};

type AgentEventDetails = {
  phase?: string;
  agent_provider?: string;
  agent_error?: string | null;
  planned_actions?: AgentAction[];
  applied_actions?: AgentAction[];
  planned_action_count?: number;
  applied_action_count?: number;
  current_action?: AgentAction | null;
  action_index?: number | null;
  action_total?: number | null;
};

type AgentRunEvent = RunEvent & {
  details?: AgentEventDetails | null;
};

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
  const agentEvent: AgentRunEvent | undefined = [...events]
    .reverse()
    .find((event) => event.stage_id === "nightmare_post_pass" && event.status !== "skipped");
  const visibleStages = stagesForMode(mode).filter((stage) => {
    if (stage.id !== "nightmare_post_pass") return true;
    const event = byStage.get(stage.id);
    return Boolean(event && event.status !== "skipped");
  });

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
          {visibleStages.map((stage) => {
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
          <AgentActivity event={agentEvent} runStatus={run?.status} />
          <EventLog events={events} />
        </div>
      </div>
    </section>
  );
}

function AgentActivity({
  event,
  runStatus,
}: {
  event?: AgentRunEvent;
  runStatus?: RunSnapshot["status"];
}) {
  if (!event) return null;

  const details = event.details ?? {};
  const planned = details.planned_actions ?? [];
  const applied = details.applied_actions ?? [];
  const plannedCount = details.planned_action_count ?? planned.length;
  const appliedCount = details.applied_action_count ?? applied.length;
  const running = event.status === "running";
  const runFinished = runStatus === "succeeded" || runStatus === "failed";
  const finalTraceMissing = running && runFinished;
  const plannedLabel = running && !planned.length ? "Planning" : `${plannedCount} planned`;
  const appliedLabel = running && !applied.length ? "Pending" : `${appliedCount} applied`;

  return (
    <div className={`agentTrace ${event.severity ?? "info"}`}>
      <div className="agentTraceHeader">
        <h3>Agent Trace</h3>
        <span>{formatTraceStatus(details, running, finalTraceMissing)}</span>
      </div>
      <p className="agentStatus">
        {finalTraceMissing
          ? "The API did not return final agent details for this run. Rerun with the restarted API."
          : event.message}
      </p>
      {details.agent_error ? <p className="agentWarning">{details.agent_error}</p> : null}
      <div className="agentStats">
        <span>{plannedLabel}</span>
        <span>{appliedLabel}</span>
      </div>
      <ActionList
        actions={planned}
        emptyText={running ? "Trace will appear after workbook save" : "No plan recorded"}
        title="Thinking"
        total={plannedCount}
      />
      <ActionList
        actions={applied}
        emptyText={running ? "Waiting for final agent output" : "No changes recorded"}
        title="Changes"
        total={appliedCount}
      />
    </div>
  );
}

function ActionList({
  actions,
  emptyText,
  title,
  total,
}: {
  actions: AgentAction[];
  emptyText: string;
  title: string;
  total: number;
}) {
  const visibleActions = actions.slice(0, 8);
  return (
    <div className="agentActionBlock">
      <h4>{title}</h4>
      {visibleActions.length ? (
        <>
          <ol className="agentActionList">
            {visibleActions.map((action, index) => (
              <li key={`${action.tool ?? "action"}-${index}`}>
                <strong>{formatActionTitle(action)}</strong>
                <span>{formatActionMeta(action)}</span>
              </li>
            ))}
          </ol>
          {total > visibleActions.length ? (
            <p className="agentMore">+ {total - visibleActions.length} more</p>
          ) : null}
        </>
      ) : (
        <p className="emptyText">{emptyText}</p>
      )}
    </div>
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

function formatProvider(provider?: string): string {
  if (provider === "langgraph_gemini_generate_content") return "Gemini";
  if (provider === "langgraph_heuristic_fallback") return "Heuristic fallback";
  if (provider === "not_recorded") return "Not recorded";
  if (!provider || provider === "pending") return "Pending";
  return provider.replace(/^langgraph_/, "").replaceAll("_", " ");
}

function formatTraceStatus(
  details: AgentEventDetails,
  running: boolean,
  finalTraceMissing: boolean,
): string {
  if (finalTraceMissing) return "Trace missing";
  if (!running) return formatProvider(details.agent_provider);
  if (details.phase === "planned") return "Planning";
  if (details.phase === "applied") return "Applying";
  if (details.phase === "reviewing") return "Reviewing";
  return "Working";
}

function formatActionTitle(action: AgentAction): string {
  const tool = formatTool(action.tool);
  const sheet = action.sheet ? ` on ${action.sheet}` : "";
  const count = Number(action.count ?? 0);
  return `${tool}${sheet}${count > 1 ? ` x${count}` : ""}`;
}

function formatActionMeta(action: AgentAction): string {
  const parts: string[] = [];
  if (action.cells?.length) parts.push(`cells ${action.cells.slice(0, 3).join(", ")}`);
  if (action.request_id) parts.push(`request ${action.request_id}`);
  if (action.row) parts.push(`row ${action.row}`);
  if (action.row_count || action.column_count) {
    parts.push(`${Number(action.row_count ?? 0)} rows / ${Number(action.column_count ?? 0)} columns`);
  }
  if (action.reason) parts.push(action.reason);
  if (action.text) parts.push(action.text);
  return parts.join(" / ") || "Workbook-level action";
}

function formatTool(tool?: string): string {
  if (!tool) return "agent action";
  return tool.replaceAll("_", " ");
}

function useEventFilter(): [string, (value: string) => void] {
  return useState("all");
}
