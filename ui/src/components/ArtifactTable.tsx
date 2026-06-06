import { FileArchive, FolderOpen } from "lucide-react";
import { Artifact, RunSnapshot } from "../lib/api";

interface ArtifactTableProps {
  run: RunSnapshot | null;
}

export function ArtifactTable({ run }: ArtifactTableProps) {
  const artifacts = dedupeArtifacts(run?.artifacts ?? []);
  const result = run?.result ?? null;
  return (
    <section className="artifactPane" aria-label="Output artifacts">
      <div className="sectionTitle">
        <h2>Artifacts</h2>
        <span>{artifacts.length} file record{artifacts.length === 1 ? "" : "s"}</span>
      </div>
      <div className="artifactTable">
        <div className="artifactHeader">
          <span>Type</span>
          <span>Path</span>
          <span>Size</span>
        </div>
        {artifacts.length ? (
          artifacts.map((artifact) => (
            <div className="artifactRow" key={`${artifact.type}-${artifact.path}`}>
              <span>
                <FileArchive size={15} />
                {artifact.type}
              </span>
              <code title={artifact.path}>{artifact.path}</code>
              <span>{formatSize(artifact.size)}</span>
            </div>
          ))
        ) : (
          <div className="artifactEmpty">
            <FolderOpen size={18} />
            <span>Artifacts will appear as soon as the runner writes them.</span>
          </div>
        )}
      </div>
      {result ? <ResultSummary result={result} /> : null}
    </section>
  );
}

function ResultSummary({ result }: { result: Record<string, unknown> }) {
  if (result.mode === "doc-types") {
    const documentTypes = Array.isArray(result.document_types) ? result.document_types : [];
    return (
      <div className="resultSummary">
        <h3>Document Types</h3>
        <div className="docTypeGrid compact">
          {documentTypes.map((item) => (
            <code key={String(item)}>{String(item)}</code>
          ))}
        </div>
      </div>
    );
  }
  if (result.mode === "validate") {
    const issues = Array.isArray(result.issues) ? result.issues : [];
    return (
      <div className={result.passed ? "resultSummary passed" : "resultSummary failed"}>
        <h3>{result.passed ? "Validation passed" : "Validation failed"}</h3>
        <p>
          {String(result.workbook_count ?? 0)} workbook(s) checked in {String(result.run_path ?? "")}
        </p>
        {issues.length ? (
          <ul>
            {issues.map((issue, index) => (
              <li key={index}>{String((issue as { message?: unknown }).message ?? issue)}</li>
            ))}
          </ul>
        ) : null}
      </div>
    );
  }
  if (result.mode === "score") {
    return (
      <div className="resultSummary passed">
        <h3>Score complete</h3>
        <p>Overall score: {Number(result.overall_score ?? 0).toFixed(3)}</p>
      </div>
    );
  }
  return (
    <div className="resultSummary">
      <h3>Run Summary</h3>
      <dl>
        <dt>Workbook count</dt>
        <dd>{String(result.workbook_count ?? "-")}</dd>
        <dt>Output directory</dt>
        <dd>{String(result.output_dir ?? "-")}</dd>
        <dt>Manifest path</dt>
        <dd>{String(result.manifest_path ?? "-")}</dd>
        <dt>Nightmare mode</dt>
        <dd>{result.nightmare_enabled ? "Enabled" : "Off"}</dd>
      </dl>
      {Array.isArray(result.warnings) && result.warnings.length ? (
        <ul className="warningList">
          {result.warnings.map((warning) => (
            <li key={String(warning)}>{String(warning)}</li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

function dedupeArtifacts(artifacts: Artifact[]): Artifact[] {
  const seen = new Set<string>();
  return artifacts.filter((artifact) => {
    const key = `${artifact.type}-${artifact.path}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function formatSize(size?: number | null): string {
  if (!size) return "-";
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

