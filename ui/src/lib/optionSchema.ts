export type ModeId =
  | "generate-one"
  | "generate-batch"
  | "generate-dataset"
  | "generate-yaml"
  | "validate"
  | "manifest"
  | "score"
  | "doc-types";

export type FieldType =
  | "text"
  | "number"
  | "decimal"
  | "path"
  | "toggle"
  | "chaosLevel"
  | "chaosRange";

export type FormValue = string | number | boolean | null;
export type FormState = Record<string, FormValue>;

export interface FieldDefinition {
  key: string;
  label: string;
  flag?: string;
  type: FieldType;
  required?: boolean;
  helper?: string;
  min?: number;
  max?: number;
}

export interface ModeDefinition {
  id: ModeId;
  label: string;
  description: string;
  commandName: string;
  fields: FieldDefinition[];
}

export const severityLabels: Record<number, string> = {
  0: "Clean export",
  1: "Minor formatting mess",
  2: "Common finance team mess",
  3: "Messy audit season file",
  4: "Highly chaotic client submission",
  5: "Nightmare PBC file",
};

export const probabilityKeys = [
  "merged_cells",
  "hidden_rows",
  "hidden_columns",
  "duplicated_headers",
  "inserted_notes",
  "subtotal_rows",
  "wrong_period_rows",
  "renamed_columns",
  "stringified_numbers",
  "formula_errors",
  "multiple_tables_in_one_sheet",
  "old_version_tabs",
  "hidden_reconciliation_tabs",
  "pbc_request_list",
  "tracker_status_noise",
  "tracker_deadline_noise",
  "tracker_visible_comments",
  "tracker_update_highlights",
  "tracker_instruction_blocks",
] as const;

export const modeDefinitions: ModeDefinition[] = [
  {
    id: "generate-one",
    label: "Generate One",
    description: "One workbook for one named company.",
    commandName: "generate-one",
    fields: [
      { key: "company", label: "Company name", flag: "--company", type: "text", required: true },
      { key: "period", label: "Period", flag: "--period", type: "text", required: true, helper: "FY2025 or 2025" },
      { key: "chaosLevel", label: "Chaos level", flag: "--chaos-level", type: "chaosLevel", required: true, min: 0, max: 5 },
      { key: "seed", label: "Seed", flag: "--seed", type: "number", helper: "Optional deterministic seed" },
      { key: "output", label: "Output directory", flag: "--output", type: "path", helper: "Defaults to outputs" },
      { key: "unreproducibleNightmare", label: "Unreproducible nightmare", flag: "--unreproducible-nightmare", type: "toggle" },
    ],
  },
  {
    id: "generate-batch",
    label: "Generate Batch",
    description: "Many simulated companies at one chaos level.",
    commandName: "generate-batch",
    fields: [
      { key: "companies", label: "Companies", flag: "--companies", type: "number", required: true, min: 1 },
      { key: "period", label: "Period", flag: "--period", type: "text", required: true, helper: "FY2025 or 2025" },
      { key: "chaosLevel", label: "Chaos level", flag: "--chaos-level", type: "chaosLevel", required: true, min: 0, max: 5 },
      { key: "seed", label: "Seed", flag: "--seed", type: "number", helper: "Defaults to 1" },
      { key: "output", label: "Output directory", flag: "--output", type: "path", required: true },
      { key: "unreproducibleNightmare", label: "Unreproducible nightmare", flag: "--unreproducible-nightmare", type: "toggle" },
    ],
  },
  {
    id: "generate-dataset",
    label: "Generate Dataset",
    description: "Many simulated companies across a chaos range.",
    commandName: "generate-dataset",
    fields: [
      { key: "companies", label: "Companies", flag: "--companies", type: "number", required: true, min: 1 },
      { key: "chaosRange", label: "Chaos range", type: "chaosRange", required: true, min: 0, max: 5 },
      { key: "period", label: "Period", flag: "--period", type: "text", helper: "Defaults to FY2025" },
      { key: "seed", label: "Seed", flag: "--seed", type: "number", helper: "Defaults to 1" },
      { key: "output", label: "Output directory", flag: "--output", type: "path", required: true },
      { key: "unreproducibleNightmare", label: "Unreproducible nightmare", flag: "--unreproducible-nightmare", type: "toggle" },
    ],
  },
  {
    id: "generate-yaml",
    label: "Generate From YAML",
    description: "Legacy config-based generation.",
    commandName: "generate",
    fields: [
      { key: "config", label: "Config file", flag: "--config", type: "path", helper: "Defaults to configs/default.yaml" },
      { key: "unreproducibleNightmare", label: "Unreproducible nightmare", flag: "--unreproducible-nightmare", type: "toggle" },
    ],
  },
  {
    id: "validate",
    label: "Validate",
    description: "Validate generated workbooks and sidecars.",
    commandName: "validate",
    fields: [{ key: "input", label: "Input directory", flag: "--input", type: "path", required: true }],
  },
  {
    id: "manifest",
    label: "Manifest",
    description: "Rebuild or export a manifest CSV.",
    commandName: "manifest",
    fields: [
      { key: "input", label: "Input directory", flag: "--input", type: "path", required: true },
      { key: "output", label: "Output manifest path", flag: "--output", type: "path", required: true },
    ],
  },
  {
    id: "score",
    label: "Score Extraction",
    description: "Score external extraction output against ground truth.",
    commandName: "score",
    fields: [
      { key: "groundtruth", label: "Ground truth file", flag: "--groundtruth", type: "path", required: true },
      { key: "extraction", label: "Extraction output", flag: "--extraction", type: "path", required: true },
      { key: "outputJson", label: "JSON report path", flag: "--output-json", type: "path", helper: "Defaults to score_report.json" },
      { key: "outputMd", label: "Markdown report path", flag: "--output-md", type: "path", helper: "Defaults to score_report.md" },
      { key: "fuzzyColumnThreshold", label: "Fuzzy column threshold", flag: "--fuzzy-column-threshold", type: "decimal", helper: "Defaults to 0.82" },
      { key: "numericAbsTolerance", label: "Numeric absolute tolerance", flag: "--numeric-abs-tolerance", type: "decimal", helper: "Defaults to 0.01" },
      { key: "numericRelTolerance", label: "Numeric relative tolerance", flag: "--numeric-rel-tolerance", type: "decimal", helper: "Defaults to 0.0001" },
    ],
  },
  {
    id: "doc-types",
    label: "Document Types",
    description: "List supported document type identifiers.",
    commandName: "list-doc-types",
    fields: [],
  },
];

export const defaultForms: Record<ModeId, FormState> = {
  "generate-one": {
    company: "ABC Sdn Bhd",
    period: "FY2025",
    chaosLevel: 3,
    seed: 42,
    output: "./data/generated",
    unreproducibleNightmare: false,
  },
  "generate-batch": {
    companies: 10,
    period: "FY2025",
    chaosLevel: 3,
    seed: 1,
    output: "./data/generated",
    unreproducibleNightmare: false,
  },
  "generate-dataset": {
    companies: 25,
    minChaos: 0,
    maxChaos: 5,
    period: "FY2025",
    seed: 1,
    output: "./data/dataset",
    unreproducibleNightmare: false,
  },
  "generate-yaml": {
    config: "configs/default.yaml",
    unreproducibleNightmare: false,
  },
  validate: {
    input: "./data/generated",
  },
  manifest: {
    input: "./data/generated",
    output: "manifest.csv",
  },
  score: {
    groundtruth: "./data/generated/ABC.groundtruth.json",
    extraction: "./outputs/extraction_output.json",
    outputJson: "score_report.json",
    outputMd: "score_report.md",
    fuzzyColumnThreshold: "0.82",
    numericAbsTolerance: "0.01",
    numericRelTolerance: "0.0001",
  },
  "doc-types": {},
};

export const generationModeIds: ModeId[] = [
  "generate-one",
  "generate-batch",
  "generate-dataset",
  "generate-yaml",
];

export function getMode(id: ModeId): ModeDefinition {
  const mode = modeDefinitions.find((definition) => definition.id === id);
  if (!mode) {
    throw new Error(`Unknown mode: ${id}`);
  }
  return mode;
}

