import { AlertTriangle, Info, ShieldCheck } from "lucide-react";
import {
  FieldDefinition,
  FormState,
  ModeDefinition,
  generationModeIds,
  probabilityKeys,
  severityLabels,
} from "../lib/optionSchema";
import { MetadataPayload } from "../lib/api";

interface OptionPanelProps {
  mode: ModeDefinition;
  values: FormState;
  errors: string[];
  metadata: MetadataPayload | null;
  onChange: (key: string, value: string | number | boolean) => void;
}

export function OptionPanel({ mode, values, errors, metadata, onChange }: OptionPanelProps) {
  const isGeneration = generationModeIds.includes(mode.id);
  const selectedLevel =
    mode.id === "generate-dataset" ? Number(values.maxChaos ?? 5) : Number(values.chaosLevel ?? 3);
  const probabilityDefaults = metadata?.probabilityDefaults?.[String(selectedLevel)];

  return (
    <main className="workspace" aria-label="Command options">
      <div className="workspaceHeader">
        <div>
          <h2>{mode.label}</h2>
          <p>{mode.description}</p>
        </div>
        {isGeneration ? (
          <div className="severityReadout">
            <ShieldCheck size={17} />
            <span>
              Level {selectedLevel}: {severityLabels[selectedLevel] ?? "Custom"}
            </span>
          </div>
        ) : null}
      </div>

      {errors.length ? (
        <div className="alert errorAlert">
          <AlertTriangle size={17} />
          <div>
            <strong>{errors.length} option issue{errors.length === 1 ? "" : "s"}</strong>
            <span>{errors[0]}</span>
          </div>
        </div>
      ) : (
        <div className="alert">
          <Info size={17} />
          <span>Options are valid and the command preview is ready to run.</span>
        </div>
      )}

      <div className="fieldGrid">
        {mode.fields.map((field) => (
          <FieldControl
            field={field}
            key={field.key}
            onChange={onChange}
            values={values}
          />
        ))}
        {!mode.fields.length ? (
          <div className="emptyMode">
            <ListPreview documentTypes={metadata?.documentTypes ?? []} />
          </div>
        ) : null}
      </div>

      {isGeneration ? (
        <section className="profilePanel">
          <div className="sectionTitle">
            <h3>Chaos Level Visualization</h3>
            <span>Read-only severity profile</span>
          </div>
          <div className="severityScale">
            {Object.entries(severityLabels).map(([level, label]) => (
              <button
                className={Number(level) === selectedLevel ? "levelChip active" : "levelChip"}
                key={level}
                onClick={() => {
                  if (mode.id === "generate-dataset") {
                    onChange("maxChaos", Number(level));
                  } else if (mode.id !== "generate-yaml") {
                    onChange("chaosLevel", Number(level));
                  }
                }}
                type="button"
              >
                <strong>{level}</strong>
                <span>{label}</span>
              </button>
            ))}
          </div>
          <div className="probabilityTable" aria-label="Probability profile">
            <div className="probabilityHeader">
              <span>Probability key</span>
              <span>Level {selectedLevel}</span>
            </div>
            {(metadata?.probabilityKeys ?? probabilityKeys).map((key) => (
              <div className="probabilityRow" key={key}>
                <code>{key}</code>
                <span>{formatProbability(probabilityDefaults?.[key])}</span>
              </div>
            ))}
          </div>
        </section>
      ) : null}
    </main>
  );
}

function FieldControl({
  field,
  values,
  onChange,
}: {
  field: FieldDefinition;
  values: FormState;
  onChange: (key: string, value: string | number | boolean) => void;
}) {
  if (field.type === "toggle") {
    return (
      <label className="toggleField">
        <span>
          <strong>{field.label}</strong>
          {field.helper ? <small>{field.helper}</small> : null}
        </span>
        <input
          checked={Boolean(values[field.key])}
          onChange={(event) => onChange(field.key, event.target.checked)}
          type="checkbox"
        />
      </label>
    );
  }

  if (field.type === "chaosLevel") {
    return (
      <div className="fieldBlock wide">
        <label>{field.label}</label>
        <div className="segmented">
          {[0, 1, 2, 3, 4, 5].map((level) => (
            <button
              className={Number(values[field.key]) === level ? "segment active" : "segment"}
              key={level}
              onClick={() => onChange(field.key, level)}
              type="button"
              title={severityLabels[level]}
            >
              {level}
            </button>
          ))}
        </div>
      </div>
    );
  }

  if (field.type === "chaosRange") {
    return (
      <div className="fieldBlock wide">
        <label>{field.label}</label>
        <div className="rangeGrid">
          <div>
            <small>Minimum chaos</small>
            <div className="segmented">
              {[0, 1, 2, 3, 4, 5].map((level) => (
                <button
                  className={Number(values.minChaos) === level ? "segment active" : "segment"}
                  key={level}
                  onClick={() => onChange("minChaos", level)}
                  type="button"
                >
                  {level}
                </button>
              ))}
            </div>
          </div>
          <div>
            <small>Maximum chaos</small>
            <div className="segmented">
              {[0, 1, 2, 3, 4, 5].map((level) => (
                <button
                  className={Number(values.maxChaos) === level ? "segment active" : "segment"}
                  key={level}
                  onClick={() => onChange("maxChaos", level)}
                  type="button"
                >
                  {level}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <label className={field.type === "path" ? "fieldBlock wide" : "fieldBlock"}>
      <span>
        {field.label}
        {field.required ? <em>required</em> : null}
      </span>
      <input
        inputMode={field.type === "number" || field.type === "decimal" ? "decimal" : "text"}
        onChange={(event) => onChange(field.key, field.type === "number" ? Number(event.target.value) : event.target.value)}
        type={field.type === "number" || field.type === "decimal" ? "number" : "text"}
        value={String(values[field.key] ?? "")}
      />
      {field.helper ? <small>{field.helper}</small> : null}
    </label>
  );
}

function ListPreview({ documentTypes }: { documentTypes: string[] }) {
  return (
    <>
      <h3>Supported document type identifiers</h3>
      <div className="docTypeGrid">
        {documentTypes.map((item) => (
          <code key={item}>{item}</code>
        ))}
      </div>
    </>
  );
}

function formatProbability(value: number | undefined): string {
  if (value === undefined) return "Inherited";
  return `${Math.round(value * 100)}%`;
}

