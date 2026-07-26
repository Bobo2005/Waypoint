import React from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";
import "./TokenSavingsChart.css";

// Recharts renders its own SVG text elements, which don't pick up our CSS
// classes reliably -- so token values are passed directly rather than via
// CSS variables (SVG attrs need real values at render time, not var()).
const BEACON = "#F2A93B";
const GRID_LINE = "#223140";
const TEXT_MUTED = "#7E8FA0";

function formatTokens(value) {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `${Math.round(value / 1000)}K`;
  return String(value);
}

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload || !payload.length) return null;
  return (
    <div className="token-chart__tooltip mono">
      <div className="token-chart__tooltip-time">{label}</div>
      <div className="token-chart__tooltip-value">{formatTokens(payload[0].value)} saved</div>
    </div>
  );
}

export default function TokenSavingsChart({ data }) {
  return (
    <div className="token-chart">
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid stroke={GRID_LINE} vertical={false} />
          <XAxis
            dataKey="time"
            tick={{ fill: TEXT_MUTED, fontFamily: "JetBrains Mono", fontSize: 11 }}
            axisLine={{ stroke: GRID_LINE }}
            tickLine={false}
          />
          <YAxis
            tickFormatter={formatTokens}
            tick={{ fill: TEXT_MUTED, fontFamily: "JetBrains Mono", fontSize: 11 }}
            axisLine={{ stroke: GRID_LINE }}
            tickLine={false}
            width={48}
          />
          <Tooltip content={<ChartTooltip />} cursor={{ stroke: GRID_LINE }} />
          <Line
            type="monotone"
            dataKey="tokensSaved"
            stroke={BEACON}
            strokeWidth={2}
            dot={{ r: 3, fill: BEACON, strokeWidth: 0 }}
            activeDot={{ r: 5, fill: BEACON }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}