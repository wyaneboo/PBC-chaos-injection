import { FormState, ModeId } from "./optionSchema";

const periodPattern = /^(FY)?\d{4}$/i;
const decimalPattern = /^-?\d+(\.\d+)?$/;

export function buildCommand(mode: ModeId, values: FormState): string {
  const parts = ["pbc-chaos"];
  if (mode === "doc-types") {
    parts.push("list-doc-types");
    return parts.join(" ");
  }

  parts.push(mode === "generate-yaml" ? "generate" : mode);
  if (mode === "generate-one") {
    add(parts, "--company", values.company);
    add(parts, "--period", values.period);
    add(parts, "--chaos-level", values.chaosLevel);
    addOptional(parts, "--seed", values.seed);
    addOptional(parts, "--output", values.output || "outputs");
    addBoolean(parts, "--unreproducible-nightmare", values.unreproducibleNightmare);
  }
  if (mode === "generate-batch") {
    add(parts, "--companies", values.companies);
    add(parts, "--period", values.period);
    add(parts, "--chaos-level", values.chaosLevel);
    addOptional(parts, "--seed", values.seed || 1);
    add(parts, "--output", values.output);
    addBoolean(parts, "--unreproducible-nightmare", values.unreproducibleNightmare);
  }
  if (mode === "generate-dataset") {
    add(parts, "--companies", values.companies);
    addOptional(parts, "--min-chaos", valueOrDefault(values.minChaos, 0));
    addOptional(parts, "--max-chaos", valueOrDefault(values.maxChaos, 5));
    addOptional(parts, "--period", values.period || "FY2025");
    addOptional(parts, "--seed", values.seed || 1);
    add(parts, "--output", values.output);
    addBoolean(parts, "--unreproducible-nightmare", values.unreproducibleNightmare);
  }
  if (mode === "generate-yaml") {
    addOptional(parts, "--config", values.config || "configs/default.yaml");
    addBoolean(parts, "--unreproducible-nightmare", values.unreproducibleNightmare);
  }
  if (mode === "validate") {
    add(parts, "--input", values.input);
  }
  if (mode === "manifest") {
    add(parts, "--input", values.input);
    add(parts, "--output", values.output);
  }
  if (mode === "score") {
    add(parts, "--groundtruth", values.groundtruth);
    add(parts, "--extraction", values.extraction);
    addOptional(parts, "--output-json", values.outputJson || "score_report.json");
    addOptional(parts, "--output-md", values.outputMd || "score_report.md");
    addOptional(parts, "--fuzzy-column-threshold", values.fuzzyColumnThreshold || "0.82");
    addOptional(parts, "--numeric-abs-tolerance", values.numericAbsTolerance || "0.01");
    addOptional(parts, "--numeric-rel-tolerance", values.numericRelTolerance || "0.0001");
  }
  return parts.join(" ");
}

export function validateOptions(mode: ModeId, values: FormState): string[] {
  const errors: string[] = [];
  const required = (key: string, label: string) => {
    if (values[key] === undefined || values[key] === null || String(values[key]).trim() === "") {
      errors.push(`${label} is required.`);
    }
  };
  const positiveInt = (key: string, label: string) => {
    const value = Number(values[key]);
    if (!Number.isInteger(value) || value < 1) errors.push(`${label} must be a positive integer.`);
  };
  const integerRange = (key: string, label: string, min: number, max: number) => {
    const value = Number(values[key]);
    if (!Number.isInteger(value) || value < min || value > max) {
      errors.push(`${label} must be an integer from ${min} to ${max}.`);
    }
  };
  const period = (key: string, label: string, requiredValue = true) => {
    const value = String(values[key] ?? "").trim();
    if (!value && !requiredValue) return;
    if (!periodPattern.test(value)) errors.push(`${label} must use FY2025 or 2025 format.`);
  };
  const decimal = (key: string, label: string) => {
    const value = String(values[key] ?? "").trim();
    if (value && !decimalPattern.test(value)) errors.push(`${label} must be a decimal value.`);
  };

  if (mode === "generate-one") {
    required("company", "Company name");
    period("period", "Period");
    integerRange("chaosLevel", "Chaos level", 0, 5);
  }
  if (mode === "generate-batch") {
    positiveInt("companies", "Companies");
    period("period", "Period");
    integerRange("chaosLevel", "Chaos level", 0, 5);
    required("output", "Output directory");
  }
  if (mode === "generate-dataset") {
    positiveInt("companies", "Companies");
    integerRange("minChaos", "Minimum chaos", 0, 5);
    integerRange("maxChaos", "Maximum chaos", 0, 5);
    if (Number(values.minChaos) > Number(values.maxChaos)) {
      errors.push("Minimum chaos must be less than or equal to maximum chaos.");
    }
    period("period", "Period", false);
    required("output", "Output directory");
  }
  if (mode === "validate") {
    required("input", "Input directory");
  }
  if (mode === "manifest") {
    required("input", "Input directory");
    required("output", "Output manifest path");
  }
  if (mode === "score") {
    required("groundtruth", "Ground truth file");
    required("extraction", "Extraction output");
    if (String(values.groundtruth ?? "") && !String(values.groundtruth).endsWith(".groundtruth.json")) {
      errors.push("Ground truth should end with .groundtruth.json.");
    }
    decimal("fuzzyColumnThreshold", "Fuzzy column threshold");
    decimal("numericAbsTolerance", "Numeric absolute tolerance");
    decimal("numericRelTolerance", "Numeric relative tolerance");
  }
  return errors;
}

function add(parts: string[], flag: string, value: unknown): void {
  parts.push(flag, quote(value));
}

function addOptional(parts: string[], flag: string, value: unknown): void {
  if (value === undefined || value === null || value === "") return;
  add(parts, flag, value);
}

function addBoolean(parts: string[], flag: string, value: unknown): void {
  if (value === true) parts.push(flag);
}

function valueOrDefault(value: unknown, fallback: number): unknown {
  return value === undefined || value === null || value === "" ? fallback : value;
}

function quote(value: unknown): string {
  const text = String(value ?? "");
  if (!text) return '""';
  return /\s/.test(text) ? `"${text.replaceAll('"', '\\"')}"` : text;
}

