import React from "react";
import "./CheckpointList.css";

function formatTime(iso) {
  return new Date(iso).toLocaleTimeString("en-GB", { hour12: false }); // HH:MM:SS
}

export default function CheckpointList({ checkpoints }) {
  // The API returns most-recent-first (see GET /checkpoints). A terminal
  // reads oldest -> newest, top -> bottom, with the newest line arriving
  // at the bottom -- so we reverse for display here.
  const chronological = [...checkpoints].reverse();

  return (
    <div className="checkpoint-log mono" role="log" aria-label="Checkpoint log">
      {chronological.length === 0 && (
        <div className="checkpoint-line checkpoint-line--empty">no checkpoints yet</div>
      )}
      {chronological.map((cp, index) => {
        const passed = cp.test_result.passed;
        return (
          <div
            key={cp.git_commit_sha ?? `${cp.file}-${cp.timestamp}`}
            className={`checkpoint-line ${passed ? "is-pass" : "is-fail"}`}
            style={{ animationDelay: `${index * 60}ms` }}
          >
            <span className="checkpoint-line__prompt" aria-hidden="true">
              &gt;
            </span>
            <span className="checkpoint-line__time">{formatTime(cp.timestamp)}</span>
            <span className="checkpoint-line__action">migrate {cp.file.split("/").pop()}</span>
            <span className="checkpoint-line__result" aria-label={passed ? "passed" : "failed"}>
              {passed ? "\u2713" : "\u2717"}
            </span>
            <span className="checkpoint-line__sha">
              {cp.git_commit_sha ? cp.git_commit_sha.slice(0, 7) : "--------"}
            </span>
          </div>
        );
      })}
    </div>
  );
}