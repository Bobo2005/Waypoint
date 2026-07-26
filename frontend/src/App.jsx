import React, { useState } from "react";
import PlanProgressBar from "./components/PlanProgressBar.jsx";
import TokenSavingsChart from "./components/TokenSavingsChart.jsx";
import CheckpointList from "./components/CheckpointList.jsx";
import ExpandContextCounter from "./components/ExpandContextCounter.jsx";
import ControlPanel from "./components/ControlPanel.jsx";
import {
  mockRunStatus,
  mockCheckpoints,
  mockStats,
  mockTokenSavingsSeries,
} from "./mockData.js";
import "./App.css";

function formatTokens(value) {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `${Math.round(value / 1000)}K`;
  return String(value);
}

export default function App() {
  // Local-only for this step (mock data, no backend yet) -- just enough
  // state for the control buttons to demonstrate their enabled/disabled
  // states and the mission bar's LIVE indicator to react to them.
  const [status, setStatus] = useState(mockRunStatus.overall_status);
  const isRunning = status === "in_progress";

  const { paritok, expand_context_calls } = mockStats;

  return (
    <div className="app-shell">
      <header className="mission-bar">
        <div className="mission-bar__brand mono">WAYPOINT</div>
        <div className="mission-bar__task mono">demo-repo &middot; requests &rarr; httpx</div>
        <div className={`mission-bar__status mono ${isRunning ? "is-live" : ""}`}>
          <span className="mission-bar__dot" aria-hidden="true" />
          {isRunning ? "LIVE" : status.replace(/_/g, " ").toUpperCase()}
        </div>
      </header>

      <section className="stat-strip" aria-label="Run statistics">
        <div className="stat-tile">
          <div className="section-label">Tokens saved</div>
          <div className="stat-number">
            {formatTokens(paritok.tokens_saved)}
            <span className="stat-number__sub"> &middot; {(paritok.tokens_saved_pct * 100).toFixed(0)}%</span>
          </div>
        </div>
        <div className="stat-tile">
          <div className="section-label">Cost saved</div>
          <div className="stat-number">${paritok.estimated_cost_saved_usd.toFixed(2)}</div>
        </div>
        <div className="stat-tile">
          <div className="section-label">Compression</div>
          <div className="stat-number">{(paritok.compression_ratio * 100).toFixed(1)}%</div>
        </div>
        <ExpandContextCounter count={expand_context_calls} />
      </section>

      <main className="main-grid">
        <section className="panel route-panel" aria-label="Migration route">
          <div className="section-label">Route</div>
          <PlanProgressBar tasks={mockRunStatus.tasks} currentFile={mockRunStatus.current_file} />
          <ControlPanel
            status={status}
            onAction={(action) => {
              if (action === "start") setStatus("in_progress");
              if (action === "pause") setStatus("paused");
              if (action === "resume") setStatus("in_progress");
            }}
          />
        </section>

        <div className="side-column">
          <section className="panel" aria-label="Token savings over time">
            <div className="section-label">Token savings over time</div>
            <TokenSavingsChart data={mockTokenSavingsSeries} />
          </section>

          <section className="panel" aria-label="Checkpoint log">
            <div className="section-label">Checkpoint log</div>
            <CheckpointList checkpoints={mockCheckpoints} />
          </section>
        </div>
      </main>
    </div>
  );
}