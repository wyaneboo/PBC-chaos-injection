import {
  CheckCircle2,
  ClipboardList,
  FileJson2,
  Files,
  ListTree,
  ScrollText,
  Sheet,
  SlidersHorizontal,
} from "lucide-react";
import type { ComponentType } from "react";
import { ModeDefinition, ModeId } from "../lib/optionSchema";

interface ModeRailProps {
  modes: ModeDefinition[];
  activeMode: ModeId;
  onSelect: (mode: ModeId) => void;
}

const icons: Record<ModeId, ComponentType<{ size?: number }>> = {
  "generate-one": Sheet,
  "generate-batch": Files,
  "generate-dataset": SlidersHorizontal,
  "generate-yaml": ScrollText,
  validate: CheckCircle2,
  manifest: ClipboardList,
  score: FileJson2,
  "doc-types": ListTree,
};

export function ModeRail({ modes, activeMode, onSelect }: ModeRailProps) {
  return (
    <aside className="rail" aria-label="Run modes">
      <div className="brand">
        <div className="brandMark">PB</div>
        <div>
          <h1>PBC Chaos Simulator</h1>
          <span>Generator workspace</span>
        </div>
      </div>
      <nav className="modeList">
        {modes.map((mode) => {
          const Icon = icons[mode.id];
          return (
            <button
              className={mode.id === activeMode ? "modeButton active" : "modeButton"}
              key={mode.id}
              onClick={() => onSelect(mode.id)}
              type="button"
              title={mode.description}
            >
              <Icon size={18} />
              <span>{mode.label}</span>
            </button>
          );
        })}
      </nav>
    </aside>
  );
}
