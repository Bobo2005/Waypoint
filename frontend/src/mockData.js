// Mock data for the frontend-only step. Shapes match backend/main.py's real
// responses exactly (see step 3):
//   GET /run/status   -> mockRunStatus
//   GET /checkpoints  -> mockCheckpoints (most recent first, per the API contract)
//   GET /stats        -> mockStats
// mockTokenSavingsSeries has no backend equivalent yet (the real /stats
// endpoint returns a snapshot, not a time series) -- it's a plausible
// history leading up to that snapshot, for the chart to have something to
// draw. Swapping this file for real fetch calls is the next and final step.

export const mockRunStatus = {
  overall_status: "in_progress",
  current_file: "demo-repo/weather_client.py",
  is_running: true,
  expand_context_calls: 6,
  tasks: [
    { path: "demo-repo/file_downloader.py", status: "done", attempts: 1 },
    { path: "demo-repo/github_client.py", status: "done", attempts: 1 },
    { path: "demo-repo/status_reporter.py", status: "failed", attempts: 2 },
    { path: "demo-repo/weather_client.py", status: "in_progress", attempts: 1 },
    { path: "demo-repo/webhook_sender.py", status: "pending", attempts: 0 },
  ],
};

export const mockCheckpoints = [
  {
    file: "demo-repo/status_reporter.py",
    git_commit_sha: null,
    timestamp: "2026-07-26T14:05:02Z",
    test_result: {
      passed: false,
      summary: "FAILED test_check_health_unhealthy - AssertionError",
    },
  },
  {
    file: "demo-repo/github_client.py",
    git_commit_sha: "dc9ba208c77cb3b3b27e62fe08a7492dac48b381",
    timestamp: "2026-07-26T14:03:47Z",
    test_result: { passed: true, summary: "2 passed in 0.31s" },
  },
  {
    file: "demo-repo/file_downloader.py",
    git_commit_sha: "9694ebf201d180eb8889f8ce7e2b538e2cec8ca7",
    timestamp: "2026-07-26T14:02:11Z",
    test_result: { passed: true, summary: "2 passed in 0.28s" },
  },
];

export const mockStats = {
  paritok: {
    total_requests: 18,
    tokens_saved: 1200000,
    tokens_saved_pct: 0.74,
    compression_ratio: 0.257,
    estimated_cost_saved_usd: 3.41,
  },
  expand_context_calls: 6,
};

export const mockTokenSavingsSeries = [
  { time: "14:00", tokensSaved: 0 },
  { time: "14:01", tokensSaved: 180000 },
  { time: "14:02", tokensSaved: 410000 },
  { time: "14:03", tokensSaved: 640000 },
  { time: "14:04", tokensSaved: 890000 },
  { time: "14:05", tokensSaved: 1200000 },
];