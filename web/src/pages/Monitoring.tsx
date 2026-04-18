import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import Layout from "@/components/Layout";
import useAuth from "@/hooks/useAuth";
import { api, type ProjectResponse } from "@/lib/api";
import { FolderOpen, Activity, AlertTriangle, TrendingUp } from "lucide-react";

interface MonitoringMetric {
  project_id: string;
  project_name: string;
  status: "active" | "idle" | "error";
  last_trained: string;
  accuracy?: number;
  algorithm?: string;
  drift_detected: boolean;
  total_predictions: number;
  avg_response_time: number;
}

export default function Monitoring() {
  const navigate = useNavigate();
  const { accessToken } = useAuth();
  const [projects, setProjects] = useState<ProjectResponse[]>([]);
  const [metrics, setMetrics] = useState<MonitoringMetric[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedFilter, setSelectedFilter] = useState<
    "all" | "active" | "drift"
  >("all");

  useEffect(() => {
    if (!accessToken) return;

    const fetchData = async () => {
      try {
        const projectsData = await api.getProjects(accessToken);
        // Filter out deleted projects
        const activeProjects = projectsData.filter(p => p.status !== 'deleted');
        setProjects(activeProjects);

        // Create a set of active project IDs for quick lookup
        const activeProjectIds = new Set(activeProjects.map(p => p.id));

        // Get real monitoring data from API
        const monitoringData = await api.getMonitoringOverview(accessToken);
        const overviewMetrics: MonitoringMetric[] = monitoringData.overview
          .map((item: any) => ({
            project_id: item.project_id,
            project_name: item.project_name,
            status: item.status as "active" | "idle" | "error",
            last_trained: item.last_trained || new Date().toISOString(),
            accuracy: item.accuracy,
            algorithm: item.algorithm,
            drift_detected: item.drift_detected,
            total_predictions: item.total_predictions || 0,
            avg_response_time: 50, // Will be calculated from actual data
          }))
          .filter((metric: MonitoringMetric) => activeProjectIds.has(metric.project_id));
        setMetrics(overviewMetrics);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Failed to load monitoring data"
        );
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [accessToken]);

  const filteredMetrics = metrics.filter((metric) => {
    if (selectedFilter === "all") return true;
    if (selectedFilter === "active") return metric.status === "active";
    if (selectedFilter === "drift") return metric.drift_detected;
    return true;
  });

  const overallStats = {
    totalProjects: projects.length,
    activeProjects: metrics.filter((m) => m.status === "active").length,
    driftDetected: metrics.filter((m) => m.drift_detected).length,
    avgAccuracy:
      metrics.length > 0
        ? (
            (metrics.reduce((sum, m) => sum + (m.accuracy || 0), 0) /
              metrics.filter((m) => m.accuracy).length) *
            100
          ).toFixed(1)
        : "0",
  };

  return (
    <Layout>
      <div className="p-8">
        {/* Page Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-text-primary mb-2">
            System Monitoring
          </h1>
          <p className="text-text-muted">
            Real-time performance metrics and drift detection across all
            projects
          </p>
        </div>
        {/* Stats Overview */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <div className="card border-2 border-border p-6 bg-bg-secondary hover:border-purple-500/50 transition-all hover:-translate-y-1">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-text-muted mb-2 font-semibold uppercase tracking-wide">
                  Total Projects
                </p>
                <p className="text-3xl font-bold text-text-primary">
                  {overallStats.totalProjects}
                </p>
              </div>
              <div className="w-14 h-14 rounded-xl bg-purple-500/20 border-2 border-purple-500/40 flex items-center justify-center shadow-lg">
                <FolderOpen className="w-7 h-7 text-purple-400" />
              </div>
            </div>
          </div>

          <div className="card border-2 border-border p-6 bg-bg-secondary hover:border-emerald-500/50 transition-all hover:-translate-y-1">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-text-muted mb-2 font-semibold uppercase tracking-wide">
                  Active Projects
                </p>
                <p className="text-3xl font-bold text-emerald-400">
                  {overallStats.activeProjects}
                </p>
              </div>
              <div className="w-14 h-14 rounded-xl bg-emerald-500/20 border-2 border-emerald-500/40 flex items-center justify-center shadow-lg">
                <Activity className="w-7 h-7 text-emerald-400" />
              </div>
            </div>
          </div>

          <div className="card border-2 border-border p-6 bg-bg-secondary hover:border-amber-500/50 transition-all hover:-translate-y-1">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-text-muted mb-2 font-semibold uppercase tracking-wide">
                  Drift Alerts
                </p>
                <p className="text-3xl font-bold text-amber-400">
                  {overallStats.driftDetected}
                </p>
              </div>
              <div className="w-14 h-14 rounded-xl bg-amber-500/20 border-2 border-amber-500/40 flex items-center justify-center shadow-lg">
                <AlertTriangle className="w-7 h-7 text-amber-400" />
              </div>
            </div>
          </div>

          <div className="card border-2 border-border p-6 bg-bg-secondary hover:border-cyan-500/50 transition-all hover:-translate-y-1">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-text-muted mb-2 font-semibold uppercase tracking-wide">
                  Avg Accuracy
                </p>
                <p className="text-3xl font-bold text-cyan-400">
                  {overallStats.avgAccuracy}%
                </p>
              </div>
              <div className="w-14 h-14 rounded-xl bg-cyan-500/20 border-2 border-cyan-500/40 flex items-center justify-center shadow-lg">
                <TrendingUp className="w-7 h-7 text-cyan-400" />
              </div>
            </div>
          </div>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-3 mb-6">
          <span className="text-sm font-semibold text-text-primary">
            Filter:
          </span>
          <div className="flex gap-2">
            <button
              onClick={() => setSelectedFilter("all")}
              className={`px-4 py-2 text-sm font-medium rounded-lg transition-all border-2 shadow-sm ${
                selectedFilter === "all"
                  ? "bg-primary text-white border-primary shadow-lg shadow-primary/30"
                  : "bg-bg-secondary text-text-muted border-border hover:border-primary/40 hover:text-text-primary"
              }`}
            >
              All
            </button>
            <button
              onClick={() => setSelectedFilter("active")}
              className={`px-4 py-2 text-sm font-medium rounded-lg transition-all border-2 shadow-sm ${
                selectedFilter === "active"
                  ? "bg-primary text-white border-primary shadow-lg shadow-primary/30"
                  : "bg-bg-secondary text-text-muted border-border hover:border-primary/40 hover:text-text-primary"
              }`}
            >
              Active Only
            </button>
            <button
              onClick={() => setSelectedFilter("drift")}
              className={`px-4 py-2 text-sm font-medium rounded-lg transition-all border-2 shadow-sm ${
                selectedFilter === "drift"
                  ? "bg-primary text-white border-primary shadow-lg shadow-primary/30"
                  : "bg-bg-secondary text-text-muted border-border hover:border-primary/40 hover:text-text-primary"
              }`}
            >
              Drift Detected
            </button>
          </div>
        </div>

        {error && (
          <div className="bg-red-500/10 border border-[var(--color-error)] rounded-md p-3 mb-6 text-[var(--color-error)] text-sm">
            {error}
          </div>
        )}

        {/* Monitoring Table */}
        {loading ? (
          <div className="card border border-border p-6">
            <div className="animate-pulse space-y-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-16 bg-bg-secondary rounded"></div>
              ))}
            </div>
          </div>
        ) : filteredMetrics.length === 0 ? (
          <div className="text-center py-16">
            <svg
              className="mx-auto h-12 w-12 text-text-muted"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
              />
            </svg>
            <h3 className="mt-2 text-sm font-semibold text-text-primary">
              No monitoring data
            </h3>
            <p className="mt-1 text-sm text-text-muted">
              Create projects and train models to see monitoring data.
            </p>
          </div>
        ) : (
          <div className="card border-2 border-border overflow-hidden shadow-xl bg-bg-secondary">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-bg-primary border-b-2 border-border">
                  <tr>
                    <th className="px-6 py-4 text-left text-xs font-bold text-text-primary uppercase tracking-wider">
                      Project
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-bold text-text-primary uppercase tracking-wider">
                      Status
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-bold text-text-primary uppercase tracking-wider">
                      Algorithm
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-bold text-text-primary uppercase tracking-wider">
                      Accuracy
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-bold text-text-primary uppercase tracking-wider">
                      Predictions
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-bold text-text-primary uppercase tracking-wider">
                      Response Time
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-bold text-text-primary uppercase tracking-wider">
                      Last Trained
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-bold text-text-primary uppercase tracking-wider">
                      Drift
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y-2 divide-[var(--color-border)]">
                  {filteredMetrics.map((metric) => (
                    <tr
                      key={metric.project_id}
                      className="hover:bg-bg-primary transition-colors cursor-pointer border-l-4 border-transparent hover:border-primary"
                      onClick={() => navigate(`/monitoring/${metric.project_id}`)}
                    >
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-text-primary">
                          {metric.project_name}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span
                          className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${
                            metric.status === "active"
                              ? "bg-green-500/10 text-green-400"
                              : metric.status === "idle"
                              ? "bg-gray-500/10 text-gray-400"
                              : "bg-red-500/10 text-red-400"
                          }`}
                        >
                          {metric.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-text-primary">
                        {metric.algorithm ? (
                          <span className="px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full bg-blue-500/10 text-blue-400">
                            {metric.algorithm.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
                          </span>
                        ) : (
                          <span className="text-text-muted">N/A</span>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-text-primary">
                        {metric.accuracy
                          ? `${(metric.accuracy * 100).toFixed(1)}%`
                          : "N/A"}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-text-primary">
                        {metric.total_predictions.toLocaleString()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-text-primary">
                        {metric.avg_response_time.toFixed(0)}ms
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-text-muted">
                        {new Date(metric.last_trained).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {metric.drift_detected ? (
                          <span className="px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full bg-yellow-500/10 text-yellow-400">
                            Detected
                          </span>
                        ) : (
                          <span className="text-sm text-text-muted">No</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
}
