import { FormState, ModeId } from "./optionSchema";

export interface MetadataPayload {
  severityLabels: Record<string, string>;
  probabilityKeys: string[];
  probabilityDefaults?: Record<string, Record<string, number>>;
  stages: StageDefinition[];
  documentTypes: string[];
  geminiConfigured: boolean;
}

export interface StageDefinition {
  id: string;
  label: string;
  weight?: number;
  notes?: string;
}

export interface RunEvent {
  run_id: string;
  command: string;
  status: string;
  stage_id: string;
  stage_label: string;
  message: string;
  overall_percent: number;
  severity?: string;
  timestamp?: string;
  workbook?: {
    index: number;
    total: number;
    company_name: string;
    chaos_level: number;
    stage_percent: number;
  } | null;
  artifact?: Artifact | null;
}

export interface Artifact {
  type: string;
  path: string;
  name: string;
  size?: number | null;
}

export interface RunSnapshot {
  run_id: string;
  mode: ModeId;
  command: string;
  status: "queued" | "running" | "succeeded" | "failed";
  events: RunEvent[];
  artifacts: Artifact[];
  result: Record<string, unknown> | null;
  error?: { message: string; traceback?: string } | null;
}

const API_BASE = import.meta.env.VITE_PBC_CHAOS_API ?? "http://127.0.0.1:8765";

export async function fetchMetadata(): Promise<MetadataPayload> {
  const response = await fetch(`${API_BASE}/api/metadata`);
  if (!response.ok) throw new Error(`Metadata request failed: ${response.status}`);
  return response.json();
}

export async function startRun(mode: ModeId, options: FormState, command: string): Promise<RunSnapshot> {
  const response = await fetch(`${API_BASE}/api/runs`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ mode, options, command }),
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error ?? `Run request failed: ${response.status}`);
  }
  return payload;
}

export async function fetchRun(runId: string): Promise<RunSnapshot> {
  const response = await fetch(`${API_BASE}/api/runs/${runId}`);
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error ?? `Run poll failed: ${response.status}`);
  }
  return payload;
}

