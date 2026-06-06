import { Copy, Play, TerminalSquare } from "lucide-react";
import { ModeId } from "../lib/optionSchema";

interface CommandPreviewProps {
  command: string;
  errors: string[];
  isRunning: boolean;
  mode: ModeId;
  onRun: () => void;
}

export function CommandPreview({ command, errors, isRunning, mode, onRun }: CommandPreviewProps) {
  const disabled = errors.length > 0 || isRunning;
  const expectedOutput = expectedOutputForMode(mode);
  return (
    <aside className="commandPane" aria-label="Command preview">
      <div className="paneTitle">
        <TerminalSquare size={18} />
        <h2>Command Preview</h2>
      </div>
      <pre className="commandBlock">{command}</pre>
      <div className="commandActions">
        <button
          className="secondaryButton"
          onClick={() => navigator.clipboard?.writeText(command)}
          type="button"
          title="Copy command"
        >
          <Copy size={16} />
          Copy
        </button>
        <button className="primaryButton" disabled={disabled} onClick={onRun} type="button">
          <Play size={16} />
          {isRunning ? "Running" : "Run"}
        </button>
      </div>
      <section className="runNotes">
        <h3>Run Guardrails</h3>
        <ul>
          <li>CLI remains the source of truth.</li>
          <li>Invalid options block execution.</li>
          <li>Artifacts are reported as they are written.</li>
          <li>Nightmare fallback is shown as a warning.</li>
        </ul>
      </section>
      <section className="runNotes">
        <h3>Expected Output</h3>
        <ul>
          {expectedOutput.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </section>
    </aside>
  );
}

function expectedOutputForMode(mode: ModeId): string[] {
  if (mode.startsWith("generate")) {
    return ["`.xlsx` workbook files", "`.groundtruth.json` sidecars", "`manifest.csv` dataset manifest"];
  }
  if (mode === "validate") {
    return ["Pass/fail validation state", "Workbook count", "Structured issue list when validation fails"];
  }
  if (mode === "manifest") {
    return ["Rebuilt `manifest.csv`", "Manifest path", "Missing workbook or sidecar errors"];
  }
  if (mode === "score") {
    return ["Overall extraction score", "`score_report.json`", "`score_report.md`"];
  }
  return ["Supported document type identifiers", "Compact reference table"];
}
