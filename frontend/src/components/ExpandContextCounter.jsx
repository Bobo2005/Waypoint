import React from "react";

// Shares .stat-tile / .section-label / .stat-number with the other three
// stat-strip tiles (tokens/cost/compression, rendered in App.jsx) so all
// four read as one family, exactly like the wireframe's single stat row.
export default function ExpandContextCounter({ count }) {
  return (
    <div className="stat-tile">
      <div className="section-label">Recalls</div>
      <div className="stat-number">{count}</div>
    </div>
  );
}