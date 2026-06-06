import { ModeId } from "./optionSchema";
import { StageDefinition, RunEvent } from "./api";

export const generationStages: StageDefinition[] = [
  { id: "validate_options", label: "Validate options" },
  { id: "resolve_config", label: "Resolve config" },
  { id: "prepare_companies", label: "Prepare companies" },
  { id: "parse_period", label: "Parse period" },
  { id: "build_financial_truth", label: "Build financial truth" },
  { id: "generate_documents", label: "Generate clean documents" },
  { id: "render_workbook", label: "Render workbook sheets" },
  { id: "apply_layout_chaos", label: "Apply layout chaos" },
  { id: "nightmare_post_pass", label: "Nightmare agent pass" },
  { id: "record_ground_truth", label: "Record ground truth" },
  { id: "save_artifacts", label: "Save artifacts" },
  { id: "write_manifest", label: "Write manifest" },
  { id: "complete", label: "Complete" },
];

const utilityStages: Record<ModeId, StageDefinition[]> = {
  "generate-one": generationStages,
  "generate-batch": generationStages,
  "generate-dataset": generationStages,
  "generate-yaml": generationStages,
  validate: [
    { id: "validate_options", label: "Validate options" },
    { id: "validate_outputs", label: "Validate outputs" },
    { id: "complete", label: "Complete" },
  ],
  manifest: [
    { id: "validate_options", label: "Validate options" },
    { id: "write_manifest", label: "Write manifest" },
    { id: "complete", label: "Complete" },
  ],
  score: [
    { id: "validate_options", label: "Validate options" },
    { id: "score_extraction", label: "Score extraction" },
    { id: "complete", label: "Complete" },
  ],
  "doc-types": [
    { id: "validate_options", label: "Validate options" },
    { id: "complete", label: "Complete" },
  ],
};

export function stagesForMode(mode: ModeId): StageDefinition[] {
  return utilityStages[mode];
}

export function lastEventByStage(events: RunEvent[]): Map<string, RunEvent> {
  const map = new Map<string, RunEvent>();
  for (const event of events) {
    map.set(event.stage_id, event);
  }
  return map;
}

export function latestEvent(events: RunEvent[]): RunEvent | undefined {
  return events.at(-1);
}
