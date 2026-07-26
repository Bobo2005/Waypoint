import React from "react";
import "./PlanProgressBar.css";

// Order matters: this array IS the plan order, rendered left to right.
// hollow ring = pending, filled amber + pulsing = in_progress,
// filled green check = done, red X = failed.
const STATUS_META = {
  pending: { label: "pending", symbol: null },
  in_progress: { label: "in progress", symbol: null },
  done: { label: "done", symbol: "\u2713" },
  failed: { label: "failed", symbol: "\u2715" },
};

function fileLabel(path) {
  const base = path.split("/").pop() || path;
  return base.replace(/\.py$/, "");
}

export default function PlanProgressBar({ tasks, currentFile }) {
  return (
    <ol className="waypoint-trail" aria-label="Migration route, in plan order">
      {tasks.map((task) => {
        const meta = STATUS_META[task.status] ?? STATUS_META.pending;
        const isActive = task.path === currentFile;

        return (
          <li
            key={task.path}
            className={`waypoint-node waypoint-node--${task.status}`}
            aria-current={isActive ? "step" : undefined}
          >
            <span
              className="waypoint-node__dot"
              role="img"
              aria-label={`${task.path}: ${meta.label}`}
              title={`${task.path} \u2014 ${meta.label}`}
            >
              {meta.symbol}
            </span>
            {/* Reduced-motion fallback: hidden by default, shown by CSS
                only under prefers-reduced-motion, alongside a static ring
                instead of the pulsing fill. */}
            <span className="waypoint-node__status-text mono" aria-hidden="true">
              ACTIVE
            </span>
            <span className="waypoint-node__file mono">{fileLabel(task.path)}</span>
          </li>
        );
      })}
    </ol>
  );
}