import { useCallback, useEffect, useMemo, useState } from "react";
import { AlertTriangle, DatabaseZap, RefreshCw } from "lucide-react";
import { ArtifactTable } from "./components/ArtifactTable";
import { CommandPreview } from "./components/CommandPreview";
import { ModeRail } from "./components/ModeRail";
import { OptionPanel } from "./components/OptionPanel";
import { ProgressTimeline } from "./components/ProgressTimeline";
import { buildCommand, validateOptions } from "./lib/commandBuilder";
import { fetchMetadata, fetchRun, MetadataPayload, RunSnapshot, startRun } from "./lib/api";
import { defaultForms, FormState, getMode, ModeId, modeDefinitions } from "./lib/optionSchema";

function App() {
  const [activeMode, setActiveMode] = useState<ModeId>("generate-dataset");
  const [forms, setForms] = useState<Record<ModeId, FormState>>(defaultForms);
  const [metadata, setMetadata] = useState<MetadataPayload | null>(null);
  const [metadataError, setMetadataError] = useState<string | null>(null);
  const [runsByMode, setRunsByMode] = useState<Partial<Record<ModeId, RunSnapshot>>>({});
  const [runError, setRunError] = useState<string | null>(null);

  const values = forms[activeMode];
  const mode = getMode(activeMode);
  const command = useMemo(() => buildCommand(activeMode, values), [activeMode, values]);
  const errors = useMemo(() => validateOptions(activeMode, values), [activeMode, values]);
  const run = runsByMode[activeMode] ?? null;
  const isRunning = run?.status === "queued" || run?.status === "running";

  useEffect(() => {
    let cancelled = false;
    fetchMetadata()
      .then((payload) => {
        if (!cancelled) setMetadata(payload);
      })
      .catch((error: Error) => {
        if (!cancelled) setMetadataError(error.message);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!run || (run.status !== "queued" && run.status !== "running")) return undefined;
    const timer = window.setInterval(() => {
      fetchRun(run.run_id)
        .then((snapshot) =>
          setRunsByMode((current) => ({
            ...current,
            [activeMode]: snapshot,
          })),
        )
        .catch((error: Error) => setRunError(error.message));
    }, 450);
    return () => window.clearInterval(timer);
  }, [run]);

  const updateField = useCallback(
    (key: string, value: string | number | boolean) => {
      setForms((current) => ({
        ...current,
        [activeMode]: {
          ...current[activeMode],
          [key]: value,
        },
      }));
    },
    [activeMode],
  );

  const handleRun = useCallback(() => {
    if (errors.length) return;
    setRunError(null);
    startRun(activeMode, values, command)
      .then((snapshot) =>
        setRunsByMode((current) => ({
          ...current,
          [activeMode]: snapshot,
        })),
      )
      .catch((error: Error) => setRunError(error.message));
  }, [activeMode, command, errors.length, values]);

  const refreshRun = useCallback(() => {
    if (!run) return;
    fetchRun(run.run_id)
      .then((snapshot) =>
        setRunsByMode((current) => ({
          ...current,
          [activeMode]: snapshot,
        })),
      )
      .catch((error: Error) => setRunError(error.message));
  }, [run]);

  return (
    <div className="appShell">
      <ModeRail activeMode={activeMode} modes={modeDefinitions} onSelect={setActiveMode} />
      <OptionPanel
        errors={errors}
        metadata={metadata}
        mode={mode}
        onChange={updateField}
        values={values}
      />
      <CommandPreview
        command={command}
        errors={errors}
        isRunning={isRunning}
        mode={activeMode}
        onRun={handleRun}
      />
      <section className="statusStrip">
        <div className="statusItem">
          <DatabaseZap size={17} />
          <span>API</span>
          <strong>{metadata ? "Connected" : metadataError ? "Unavailable" : "Checking"}</strong>
        </div>
        <div className="statusItem">
          <span>Gemini key</span>
          <strong>{metadata?.geminiConfigured ? "Configured" : "Fallback ready"}</strong>
        </div>
        <button className="iconButton" disabled={!run} onClick={refreshRun} type="button" title="Refresh run">
          <RefreshCw size={16} />
        </button>
        {(metadataError || runError || run?.error) ? (
          <div className="inlineError">
            <AlertTriangle size={16} />
            <span>{metadataError ?? runError ?? run?.error?.message}</span>
          </div>
        ) : null}
      </section>
      <ProgressTimeline mode={activeMode} run={run} />
      <ArtifactTable run={run} />
    </div>
  );
}

export default App;
