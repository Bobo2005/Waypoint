import React from "react";
import "./ControlPanel.css";

const ACTIONS = [
  { key: "start", label: "Start" },
  { key: "pause", label: "Pause" },
  { key: "resume", label: "Resume" },
];

export default function ControlPanel({ status, onAction }) {
  const isRunning = status === "in_progress";
  const isPaused = status === "paused";

  const disabledFor = {
    start: isRunning || isPaused,
    pause: !isRunning,
    resume: !isPaused,
  };

  return (
    <div className="control-panel" role="group" aria-label="Run controls">
      {ACTIONS.map((action) => (
        <button
          key={action.key}
          type="button"
          className="control-button mono"
          disabled={disabledFor[action.key]}
          onClick={() => onAction?.(action.key)}
        >
          {action.label}
        </button>
      ))}
    </div>
  );
}