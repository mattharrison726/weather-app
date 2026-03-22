import type { PipelineRun } from "../types/weather";

interface Props {
  runs: PipelineRun[];
  triggering: boolean;
  lastRefreshed: Date | null;
  onTrigger: () => void;
  onRefresh: () => void;
}

function StatusBadge({ status }: { status: string }) {
  return <span className={`badge badge-${status}`}>{status}</span>;
}

function formatDuration(seconds: number | null): string {
  if (seconds === null) return "—";
  return `${seconds.toFixed(2)}s`;
}

function formatRelative(isoString: string): string {
  const diff = Date.now() - new Date(isoString).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export function PipelineStatus({
  runs,
  triggering,
  lastRefreshed,
  onTrigger,
  onRefresh,
}: Props) {
  return (
    <div className="card pipeline-card">
      <div className="pipeline-header">
        <h3>Pipeline Status</h3>
        <div className="pipeline-actions">
          <button
            className="btn btn-secondary"
            onClick={onRefresh}
            disabled={triggering}
          >
            Reload UI
          </button>
          <button
            className="btn btn-primary"
            onClick={onTrigger}
            disabled={triggering}
          >
            {triggering ? "Running…" : "Refresh Data"}
          </button>
        </div>
      </div>

      {lastRefreshed && (
        <p className="last-refreshed">
          UI last refreshed: {lastRefreshed.toLocaleTimeString()}
        </p>
      )}

      {runs.length === 0 ? (
        <p className="empty-state">No pipeline runs yet.</p>
      ) : (
        <div className="runs-table-wrapper">
          <table className="runs-table">
            <thead>
              <tr>
                <th>Started</th>
                <th>Triggered by</th>
                <th>Status</th>
                <th>Fetched</th>
                <th>Transformed</th>
                <th>Failed</th>
                <th>Duration</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((run) => (
                <tr key={run.run_id}>
                  <td title={run.started_at}>
                    {formatRelative(run.started_at)}
                  </td>
                  <td>{run.triggered_by}</td>
                  <td>
                    <StatusBadge status={run.status} />
                  </td>
                  <td>{run.rows_fetched}</td>
                  <td>{run.rows_transformed}</td>
                  <td className={run.rows_failed > 0 ? "failed-count" : ""}>
                    {run.rows_failed}
                  </td>
                  <td>{formatDuration(run.duration_seconds)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
