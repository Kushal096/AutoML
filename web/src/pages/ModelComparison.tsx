import { useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import Layout from "@/components/Layout";
import useAuth from "@/hooks/useAuth";
import { api } from "@/lib/api";
import { 
  ArrowLeft, 
  TrendingUp,
  TrendingDown,
  BarChart3,
  Award,
  Activity,
  Layers,
  Database,
  ChevronDown,
  ChevronUp,
  Calendar,
  Zap
} from "lucide-react";

export default function ModelComparison() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const { accessToken } = useAuth();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [models, setModels] = useState<any[]>([]);
  const [selectedModel1, setSelectedModel1] = useState<string>("");
  const [selectedModel2, setSelectedModel2] = useState<string>("");
  const [comparisonData, setComparisonData] = useState<any>(null);
  const [comparing, setComparing] = useState(false);
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    metrics: true,
    features: false,
    confusion: false,
    training: false,
  });

  useEffect(() => {
    if (!accessToken || !projectId) return;

    const fetchModels = async () => {
      try {
        const data = await api.getAllModels(accessToken, projectId);
        setModels(data.models || []);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load models");
      } finally {
        setLoading(false);
      }
    };

    fetchModels();
  }, [accessToken, projectId]);

  const handleCompare = async () => {
    if (!selectedModel1 || !selectedModel2) {
      setError("Please select both models to compare");
      return;
    }

    if (selectedModel1 === selectedModel2) {
      setError("Please select two different models");
      return;
    }

    setComparing(true);
    setError(null);

    try {
      const data = await api.compareModels(accessToken, projectId!, selectedModel1, selectedModel2);
      setComparisonData(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to compare models");
    } finally {
      setComparing(false);
    }
  };

  const toggleSection = (section: string) => {
    setExpandedSections(prev => ({ ...prev, [section]: !prev[section] }));
  };

  const formatMetric = (value: number | null | undefined): string => {
    if (value === null || value === undefined) return "N/A";
    if (typeof value === "number") {
      if (value < 0.01) return value.toExponential(2);
      return value.toFixed(4);
    }
    return String(value);
  };

  if (loading) {
    return (
      <Layout>
        <div className="p-8 max-w-6xl mx-auto">
          <div className="animate-pulse space-y-6">
            <div className="h-8 bg-bg-secondary rounded w-1/3"></div>
            <div className="h-32 bg-bg-secondary rounded"></div>
          </div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="p-8 max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <button
            onClick={() => navigate(`/projects/${projectId}`)}
            className="flex items-center gap-2 text-text-secondary hover:text-text-primary mb-6 transition-colors text-sm"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Project
          </button>
          <h1 className="text-3xl font-bold text-text-primary mb-2">Model Comparison</h1>
          <p className="text-text-secondary">Compare performance metrics between model versions</p>
        </div>

        {/* Model Selection */}
        <div className="bg-bg-secondary border border-border rounded-xl p-6 mb-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
            <div>
              <label className="block text-sm font-medium text-text-secondary mb-2">
                Model 1
              </label>
              <select
                value={selectedModel1}
                onChange={(e) => setSelectedModel1(e.target.value)}
                className="w-full px-4 py-2.5 bg-bg-primary border border-border rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all"
              >
                <option value="">Select Model 1</option>
                {models.map((model) => (
                  <option key={model.id} value={model.id}>
                    Version {model.version} - {new Date(model.created_at).toLocaleDateString()}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-text-secondary mb-2">
                Model 2
              </label>
              <select
                value={selectedModel2}
                onChange={(e) => setSelectedModel2(e.target.value)}
                className="w-full px-4 py-2.5 bg-bg-primary border border-border rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all"
              >
                <option value="">Select Model 2</option>
                {models.map((model) => (
                  <option key={model.id} value={model.id}>
                    Version {model.version} - {new Date(model.created_at).toLocaleDateString()}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <button
            onClick={handleCompare}
            disabled={comparing || !selectedModel1 || !selectedModel2}
            className="w-full md:w-auto px-6 py-2.5 bg-primary hover:bg-primary/90 text-white rounded-lg font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-2"
          >
            {comparing ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"></div>
                Comparing...
              </>
            ) : (
              <>
                <BarChart3 className="w-4 h-4" />
                Compare Models
              </>
            )}
          </button>
        </div>

        {error && (
          <div className="bg-red-500/10 border border-red-500/50 rounded-lg p-4 mb-6">
            <p className="text-red-400 text-sm">{error}</p>
          </div>
        )}

        {/* Comparison Results */}
        {comparisonData && (
          <div className="space-y-6">
            {/* Winner & Summary */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Winner Card */}
              {comparisonData.winner && comparisonData.winner !== "tie" && (
                <div className={`lg:col-span-1 rounded-xl p-6 border ${
                  comparisonData.winner === "model_2" 
                    ? "bg-green-500/5 border-green-500/30" 
                    : "bg-blue-500/5 border-blue-500/30"
                }`}>
                  <div className="flex items-start gap-3">
                    <Award className={`w-5 h-5 mt-0.5 ${
                      comparisonData.winner === "model_2" ? "text-green-400" : "text-blue-400"
                    }`} />
                    <div className="flex-1">
                      <p className="text-xs font-medium text-text-secondary mb-1">Winner</p>
                      <p className="text-lg font-semibold text-text-primary mb-2">
                        {comparisonData.winner === "model_2" ? "Model 2" : "Model 1"}
                      </p>
                      <p className="text-sm text-text-secondary leading-relaxed">
                        {comparisonData.recommendation}
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Summary Stats */}
              {comparisonData.summary && (
                <div className={`lg:col-span-${comparisonData.winner === "tie" ? "3" : "2"} bg-bg-secondary border border-border rounded-xl p-6`}>
                  <div className="flex items-center gap-2 mb-4">
                    <Activity className="w-4 h-4 text-text-secondary" />
                    <h3 className="text-sm font-semibold text-text-secondary uppercase tracking-wide">Summary</h3>
                  </div>
                  <div className="grid grid-cols-4 gap-4">
                    <div>
                      <p className="text-xs text-text-secondary mb-1">Metrics</p>
                      <p className="text-xl font-bold text-text-primary">
                        {comparisonData.summary.total_metrics_compared}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-text-secondary mb-1">Improved</p>
                      <p className="text-xl font-bold text-green-400">
                        {comparisonData.summary.metrics_improved}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-text-secondary mb-1">Degraded</p>
                      <p className="text-xl font-bold text-red-400">
                        {comparisonData.summary.metrics_degraded}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-text-secondary mb-1">Trend</p>
                      <p className={`text-xl font-bold capitalize ${
                        comparisonData.summary.overall_trend === "improvement" 
                          ? "text-green-400" 
                          : comparisonData.summary.overall_trend === "degradation"
                          ? "text-red-400"
                          : "text-yellow-400"
                      }`}>
                        {comparisonData.summary.overall_trend}
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Model Details */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Model 1 */}
              <div className="bg-bg-secondary border border-border rounded-xl p-6">
                <div className="flex items-center justify-between mb-6">
                  <h3 className="text-lg font-semibold text-text-primary">
                    Model 1
                  </h3>
                  <span className="px-3 py-1 bg-blue-500/10 text-blue-400 text-xs font-semibold rounded-full border border-blue-500/30">
                    v{comparisonData.model_1.version}
                  </span>
                </div>
                <div className="space-y-3">
                  <div className="flex items-center justify-between py-2 border-b border-border/50">
                    <span className="text-sm text-text-secondary">Created</span>
                    <span className="text-sm text-text-primary font-medium">
                      {new Date(comparisonData.model_1.created_at).toLocaleDateString()}
                    </span>
                  </div>
                  <div className="flex items-center justify-between py-2 border-b border-border/50">
                    <span className="text-sm text-text-secondary">Stage</span>
                    <span className="text-sm text-text-primary font-medium capitalize">
                      {comparisonData.model_1.deployment_stage}
                    </span>
                  </div>
                  <div className="flex items-center justify-between py-2 border-b border-border/50">
                    <span className="text-sm text-text-secondary">Predictions</span>
                    <span className="text-sm text-text-primary font-medium">
                      {comparisonData.model_1.total_predictions.toLocaleString()}
                    </span>
                  </div>
                  {comparisonData.model_1.training_duration && (
                    <div className="flex items-center justify-between py-2 border-b border-border/50">
                      <span className="text-sm text-text-secondary">Training Time</span>
                      <span className="text-sm text-text-primary font-medium">
                        {comparisonData.model_1.training_duration.toFixed(1)}s
                      </span>
                    </div>
                  )}
                  <div className="flex items-center justify-between py-2">
                    <span className="text-sm text-text-secondary">Datasets</span>
                    <span className="text-sm text-text-primary font-medium">
                      {comparisonData.model_1.training_datasets}
                    </span>
                  </div>
                </div>
              </div>

              {/* Model 2 */}
              <div className="bg-bg-secondary border border-border rounded-xl p-6">
                <div className="flex items-center justify-between mb-6">
                  <h3 className="text-lg font-semibold text-text-primary">
                    Model 2
                  </h3>
                  <span className="px-3 py-1 bg-emerald-500/10 text-emerald-400 text-xs font-semibold rounded-full border border-emerald-500/30">
                    v{comparisonData.model_2.version}
                  </span>
                </div>
                <div className="space-y-3">
                  <div className="flex items-center justify-between py-2 border-b border-border/50">
                    <span className="text-sm text-text-secondary">Created</span>
                    <span className="text-sm text-text-primary font-medium">
                      {new Date(comparisonData.model_2.created_at).toLocaleDateString()}
                    </span>
                  </div>
                  <div className="flex items-center justify-between py-2 border-b border-border/50">
                    <span className="text-sm text-text-secondary">Stage</span>
                    <span className="text-sm text-text-primary font-medium capitalize">
                      {comparisonData.model_2.deployment_stage}
                    </span>
                  </div>
                  <div className="flex items-center justify-between py-2 border-b border-border/50">
                    <span className="text-sm text-text-secondary">Predictions</span>
                    <span className="text-sm text-text-primary font-medium">
                      {comparisonData.model_2.total_predictions.toLocaleString()}
                    </span>
                  </div>
                  {comparisonData.model_2.training_duration && (
                    <div className="flex items-center justify-between py-2 border-b border-border/50">
                      <span className="text-sm text-text-secondary">Training Time</span>
                      <span className="text-sm text-text-primary font-medium">
                        {comparisonData.model_2.training_duration.toFixed(1)}s
                      </span>
                    </div>
                  )}
                  <div className="flex items-center justify-between py-2">
                    <span className="text-sm text-text-secondary">Datasets</span>
                    <span className="text-sm text-text-primary font-medium">
                      {comparisonData.model_2.training_datasets}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Metrics Comparison */}
            {comparisonData.comparison?.metrics && (
              <div className="bg-bg-secondary border border-border rounded-xl p-6">
                <button
                  onClick={() => toggleSection("metrics")}
                  className="w-full flex items-center justify-between mb-4"
                >
                  <h3 className="text-lg font-semibold text-text-primary flex items-center gap-2">
                    <BarChart3 className="w-5 h-5" />
                    Performance Metrics
                  </h3>
                  {expandedSections.metrics ? (
                    <ChevronUp className="w-5 h-5 text-text-secondary" />
                  ) : (
                    <ChevronDown className="w-5 h-5 text-text-secondary" />
                  )}
                </button>
                {expandedSections.metrics && (
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead>
                        <tr className="border-b border-border">
                          <th className="text-left py-3 px-4 text-xs font-semibold text-text-secondary uppercase tracking-wide">Metric</th>
                          <th className="text-right py-3 px-4 text-xs font-semibold text-text-secondary uppercase tracking-wide">Model 1</th>
                          <th className="text-right py-3 px-4 text-xs font-semibold text-text-secondary uppercase tracking-wide">Model 2</th>
                          <th className="text-right py-3 px-4 text-xs font-semibold text-text-secondary uppercase tracking-wide">Change</th>
                        </tr>
                      </thead>
                      <tbody>
                        {Object.entries(comparisonData.comparison.metrics).map(([metric, data]: [string, any]) => (
                          <tr key={metric} className="border-b border-border/30 hover:bg-bg-primary/30 transition-colors">
                            <td className="py-3 px-4 text-sm text-text-primary font-medium capitalize">
                              {metric.replace(/_/g, " ")}
                            </td>
                            <td className="py-3 px-4 text-right text-sm text-text-secondary font-mono">
                              {formatMetric(data.model_1)}
                            </td>
                            <td className="py-3 px-4 text-right text-sm text-text-secondary font-mono">
                              {formatMetric(data.model_2)}
                            </td>
                            <td className={`py-3 px-4 text-right text-sm font-medium flex items-center justify-end gap-1 ${
                              data.improved ? "text-green-400" : "text-red-400"
                            }`}>
                              {data.improved ? (
                                <TrendingUp className="w-4 h-4" />
                              ) : (
                                <TrendingDown className="w-4 h-4" />
                              )}
                              {data.percent_change > 0 ? "+" : ""}{data.percent_change.toFixed(2)}%
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}

            {/* Feature Importance */}
            {comparisonData.comparison?.feature_importance?.available && (
              <div className="bg-bg-secondary border border-border rounded-xl p-6">
                <button
                  onClick={() => toggleSection("features")}
                  className="w-full flex items-center justify-between mb-4"
                >
                  <h3 className="text-lg font-semibold text-text-primary flex items-center gap-2">
                    <Layers className="w-5 h-5" />
                    Feature Importance
                  </h3>
                  {expandedSections.features ? (
                    <ChevronUp className="w-5 h-5 text-text-secondary" />
                  ) : (
                    <ChevronDown className="w-5 h-5 text-text-secondary" />
                  )}
                </button>
                {expandedSections.features && (
                  <div className="space-y-3">
                    <p className="text-sm text-text-secondary mb-4">
                      {comparisonData.comparison.feature_importance.common_features} common features compared
                    </p>
                    {comparisonData.comparison.feature_importance.top_changes && (
                      <div className="space-y-2">
                        {Object.entries(comparisonData.comparison.feature_importance.top_changes).map(
                          ([feature, data]: [string, any]) => (
                            <div key={feature} className="bg-bg-primary border border-border/50 rounded-lg p-4">
                              <div className="flex items-center justify-between mb-2">
                                <span className="text-sm font-medium text-text-primary">{feature}</span>
                                <span className={`text-sm font-semibold ${
                                  data.percent_change > 0 ? "text-green-400" : "text-red-400"
                                }`}>
                                  {data.percent_change > 0 ? "+" : ""}{data.percent_change.toFixed(2)}%
                                </span>
                              </div>
                              <div className="flex items-center justify-between text-xs text-text-secondary">
                                <span>v{comparisonData.model_1.version}: {formatMetric(data.model_1)}</span>
                                <span>v{comparisonData.model_2.version}: {formatMetric(data.model_2)}</span>
                              </div>
                            </div>
                          )
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Confusion Matrix */}
            {comparisonData.comparison?.confusion_matrix?.available && (
              <div className="bg-bg-secondary border border-border rounded-xl p-6">
                <button
                  onClick={() => toggleSection("confusion")}
                  className="w-full flex items-center justify-between mb-4"
                >
                  <h3 className="text-lg font-semibold text-text-primary flex items-center gap-2">
                    <BarChart3 className="w-5 h-5" />
                    Confusion Matrix
                  </h3>
                  {expandedSections.confusion ? (
                    <ChevronUp className="w-5 h-5 text-text-secondary" />
                  ) : (
                    <ChevronDown className="w-5 h-5 text-text-secondary" />
                  )}
                </button>
                {expandedSections.confusion && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                      <p className="text-xs font-medium text-text-secondary mb-3 uppercase tracking-wide">Model 1</p>
                      <div className="bg-bg-primary border border-border rounded-lg p-4">
                        <div className="grid grid-cols-2 gap-3">
                          {comparisonData.comparison.confusion_matrix.model_1.matrix.flat().map(
                            (val: number, idx: number) => (
                              <div key={idx} className="p-3 bg-bg-secondary rounded text-center text-text-primary font-semibold">
                                {val}
                              </div>
                            )
                          )}
                        </div>
                      </div>
                    </div>
                    <div>
                      <p className="text-xs font-medium text-text-secondary mb-3 uppercase tracking-wide">Model 2</p>
                      <div className="bg-bg-primary border border-border rounded-lg p-4">
                        <div className="grid grid-cols-2 gap-3">
                          {comparisonData.comparison.confusion_matrix.model_2.matrix.flat().map(
                            (val: number, idx: number) => (
                              <div key={idx} className="p-3 bg-bg-secondary rounded text-center text-text-primary font-semibold">
                                {val}
                              </div>
                            )
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Training Data */}
            {comparisonData.comparison?.training_data?.available && (
              <div className="bg-bg-secondary border border-border rounded-xl p-6">
                <button
                  onClick={() => toggleSection("training")}
                  className="w-full flex items-center justify-between mb-4"
                >
                  <h3 className="text-lg font-semibold text-text-primary flex items-center gap-2">
                    <Database className="w-5 h-5" />
                    Training Data
                  </h3>
                  {expandedSections.training ? (
                    <ChevronUp className="w-5 h-5 text-text-secondary" />
                  ) : (
                    <ChevronDown className="w-5 h-5 text-text-secondary" />
                  )}
                </button>
                {expandedSections.training && (
                  <div className="grid grid-cols-3 gap-6">
                    <div>
                      <p className="text-xs font-medium text-text-secondary mb-2 uppercase tracking-wide">Model 1</p>
                      <p className="text-2xl font-bold text-text-primary">
                        {comparisonData.comparison.training_data.model_1.dataset_count}
                      </p>
                      <p className="text-xs text-text-secondary mt-1">datasets</p>
                    </div>
                    <div>
                      <p className="text-xs font-medium text-text-secondary mb-2 uppercase tracking-wide">Model 2</p>
                      <p className="text-2xl font-bold text-text-primary">
                        {comparisonData.comparison.training_data.model_2.dataset_count}
                      </p>
                      <p className="text-xs text-text-secondary mt-1">datasets</p>
                    </div>
                    <div>
                      <p className="text-xs font-medium text-text-secondary mb-2 uppercase tracking-wide">Overlap</p>
                      <p className="text-2xl font-bold text-text-primary">
                        {comparisonData.comparison.training_data.dataset_overlap_percent.toFixed(1)}%
                      </p>
                      <p className="text-xs text-text-secondary mt-1">
                        {comparisonData.comparison.training_data.common_datasets.length} shared
                      </p>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </Layout>
  );
}
