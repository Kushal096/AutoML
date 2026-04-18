import { useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import Layout from "@/components/Layout";
import useAuth from "@/hooks/useAuth";
import { api } from "@/lib/api";
import { 
  ArrowLeft, 
  Activity, 
  AlertTriangle, 
  TrendingUp, 
  BarChart3,
  Clock,
  Database,
  Code,
  Globe,
  Zap,
  CheckCircle2,
  XCircle,
  Layers,
  Target,
  Users,
  FileText,
  ChevronDown,
  ChevronUp,
  Info
} from "lucide-react";

export default function ProjectMonitoringDetails() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const { accessToken } = useAuth();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [monitoringData, setMonitoringData] = useState<any>(null);
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    confusionMatrix: false,
    classificationReport: false,
    featureImportance: false,
    modelVersions: true,
    driftHistory: false,
  });

  useEffect(() => {
    if (!accessToken || !projectId) return;

    const fetchMonitoringDetails = async () => {
      try {
        const data = await api.getProjectMonitoringDetails(accessToken, projectId);
        setMonitoringData(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load monitoring details");
      } finally {
        setLoading(false);
      }
    };

    fetchMonitoringDetails();
  }, [accessToken, projectId]);

  const toggleSection = (section: string) => {
    setExpandedSections(prev => ({ ...prev, [section]: !prev[section] }));
  };

  if (loading) {
    return (
      <Layout>
        <div className="p-8">
          <div className="animate-pulse space-y-4">
            <div className="h-8 bg-bg-secondary rounded w-1/4"></div>
            <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="h-32 bg-bg-secondary rounded"></div>
              ))}
            </div>
          </div>
        </div>
      </Layout>
    );
  }

  if (error || !monitoringData) {
    return (
      <Layout>
        <div className="p-8">
          <div className="bg-red-500/10 border-2 border-red-500 rounded-lg p-4">
            <p className="text-red-400">{error || "Failed to load monitoring details"}</p>
          </div>
        </div>
      </Layout>
    );
  }

  const {
    project_name,
    project_status,
    latest_model,
    model_versions,
    datasets,
    prediction_stats,
    drift_history,
    drift_alerts,
    metrics_history,
    performance,
    last_updated
  } = monitoringData;

  const latestMetrics = latest_model?.metrics || {};
  const confusionMatrix = latestMetrics.confusion_matrix || [];
  const classificationReport = latestMetrics.classification_report || {};
  const featureImportances = latestMetrics.feature_importances || {};
  const topFeatures = latestMetrics.top_features || {};

  return (
    <Layout>
      <div className="p-8 max-w-[1600px] mx-auto">
        {/* Header */}
        <div className="mb-8 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate("/monitoring")}
              className="p-2 hover:bg-bg-secondary rounded-lg transition-colors border-2 border-border"
            >
              <ArrowLeft className="w-5 h-5 text-text-primary" />
            </button>
            <div>
              <h1 className="text-3xl font-bold text-text-primary mb-1">
                {project_name}
              </h1>
              <div className="flex items-center gap-3 text-sm text-text-muted">
                <span className={`px-2 py-1 rounded border ${
                  project_status === 'trained' 
                    ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40'
                    : project_status === 'training'
                    ? 'bg-blue-500/20 text-blue-400 border-blue-500/40'
                    : 'bg-zinc-500/20 text-zinc-300 border-zinc-500/40'
                }`}>
                  {project_status}
                </span>
                {last_updated && (
                  <span className="flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    Updated {new Date(last_updated).toLocaleString()}
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Key Performance Indicators */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 mb-8">
          <div className="card border-2 border-border bg-bg-secondary p-5 hover:border-emerald-500/50 transition-all">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs text-text-muted font-semibold uppercase tracking-wide">Accuracy</span>
              <Target className="w-5 h-5 text-emerald-400" />
            </div>
            <div className="text-3xl font-bold text-emerald-400 mb-1">
              {performance?.accuracy ? `${(performance.accuracy * 100).toFixed(2)}%` : "N/A"}
            </div>
            <div className="text-xs text-text-muted">
              {latestMetrics.model_type?.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase()) || 'N/A'}
            </div>
          </div>

          <div className="card border-2 border-border bg-bg-secondary p-5 hover:border-blue-500/50 transition-all">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs text-text-muted font-semibold uppercase tracking-wide">Precision</span>
              <TrendingUp className="w-5 h-5 text-blue-400" />
            </div>
            <div className="text-3xl font-bold text-blue-400 mb-1">
              {performance?.precision ? `${(performance.precision * 100).toFixed(2)}%` : "N/A"}
            </div>
            <div className="text-xs text-text-muted">Weighted Average</div>
          </div>

          <div className="card border-2 border-border bg-bg-secondary p-5 hover:border-purple-500/50 transition-all">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs text-text-muted font-semibold uppercase tracking-wide">Recall</span>
              <Activity className="w-5 h-5 text-purple-400" />
            </div>
            <div className="text-3xl font-bold text-purple-400 mb-1">
              {performance?.recall ? `${(performance.recall * 100).toFixed(2)}%` : "N/A"}
            </div>
            <div className="text-xs text-text-muted">Weighted Average</div>
          </div>

          <div className="card border-2 border-border bg-bg-secondary p-5 hover:border-cyan-500/50 transition-all">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs text-text-muted font-semibold uppercase tracking-wide">F1 Score</span>
              <BarChart3 className="w-5 h-5 text-cyan-400" />
            </div>
            <div className="text-3xl font-bold text-cyan-400 mb-1">
              {performance?.f1_score ? `${(performance.f1_score * 100).toFixed(2)}%` : "N/A"}
            </div>
            <div className="text-xs text-text-muted">Harmonic Mean</div>
          </div>

          <div className="card border-2 border-border bg-bg-secondary p-5 hover:border-amber-500/50 transition-all">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs text-text-muted font-semibold uppercase tracking-wide">ROC AUC</span>
              <Zap className="w-5 h-5 text-amber-400" />
            </div>
            <div className="text-3xl font-bold text-amber-400 mb-1">
              {latestMetrics.roc_auc ? latestMetrics.roc_auc.toFixed(4) : "N/A"}
            </div>
            <div className="text-xs text-text-muted">Area Under Curve</div>
          </div>
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
          {/* Left Column - Model Details */}
          <div className="lg:col-span-2 space-y-6">
            {/* Model Information */}
            <div className="card border-2 border-border bg-bg-secondary p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-bold text-text-primary flex items-center gap-2">
                  <Code className="w-5 h-5" />
                  Model Information
                </h2>
                {latest_model && (
                  <span className="px-3 py-1 bg-emerald-500/20 text-emerald-400 text-xs font-semibold rounded border border-emerald-500/40">
                    Version {latest_model.version}
                  </span>
                )}
              </div>
              
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                <div className="bg-bg-primary/50 rounded-lg p-3">
                  <div className="text-xs text-text-muted mb-1">Algorithm</div>
                  <div className="text-sm font-semibold text-text-primary">
                    {performance?.algorithm 
                      ? performance.algorithm.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase())
                      : latestMetrics.algorithm?.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase()) || "N/A"}
                  </div>
                </div>
                <div className="bg-bg-primary/50 rounded-lg p-3">
                  <div className="text-xs text-text-muted mb-1">Features</div>
                  <div className="text-sm font-semibold text-text-primary">
                    {latestMetrics.n_features || "N/A"}
                  </div>
                </div>
                <div className="bg-bg-primary/50 rounded-lg p-3">
                  <div className="text-xs text-text-muted mb-1">Train Samples</div>
                  <div className="text-sm font-semibold text-text-primary">
                    {latestMetrics.n_train_samples?.toLocaleString() || "N/A"}
                  </div>
                </div>
                <div className="bg-bg-primary/50 rounded-lg p-3">
                  <div className="text-xs text-text-muted mb-1">Test Samples</div>
                  <div className="text-sm font-semibold text-text-primary">
                    {latestMetrics.n_test_samples?.toLocaleString() || "N/A"}
                  </div>
                </div>
              </div>

              {latestMetrics.cross_validation && (
                <div className="bg-bg-primary/50 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-semibold text-text-primary">Cross-Validation</span>
                    <span className="text-xs text-text-muted">
                      {latestMetrics.cross_validation.scores?.length || 0} folds
                    </span>
                  </div>
                  <div className="flex items-center gap-4">
                    <div>
                      <div className="text-xs text-text-muted">Mean Score</div>
                      <div className="text-lg font-bold text-emerald-400">
                        {(latestMetrics.cross_validation.mean_score * 100).toFixed(2)}%
                      </div>
                    </div>
                    <div>
                      <div className="text-xs text-text-muted">Std Deviation</div>
                      <div className="text-lg font-bold text-text-primary">
                        ±{(latestMetrics.cross_validation.std_score * 100).toFixed(2)}%
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Confusion Matrix */}
            {confusionMatrix.length > 0 && (
              <div className="card border-2 border-border bg-bg-secondary p-6">
                <button
                  onClick={() => toggleSection('confusionMatrix')}
                  className="w-full flex items-center justify-between mb-4"
                >
                  <h2 className="text-xl font-bold text-text-primary flex items-center gap-2">
                    <BarChart3 className="w-5 h-5" />
                    Confusion Matrix
                  </h2>
                  {expandedSections.confusionMatrix ? (
                    <ChevronUp className="w-5 h-5 text-text-muted" />
                  ) : (
                    <ChevronDown className="w-5 h-5 text-text-muted" />
                  )}
                </button>
                
                {expandedSections.confusionMatrix && (
                  <div className="space-y-4">
                    <div className="bg-bg-primary/50 rounded-lg p-4">
                      <div className="grid grid-cols-3 gap-2 text-center">
                        <div></div>
                        <div className="text-sm font-semibold text-text-primary">Predicted: No</div>
                        <div className="text-sm font-semibold text-text-primary">Predicted: Yes</div>
                        <div className="text-sm font-semibold text-text-primary">Actual: No</div>
                        <div className="p-3 bg-emerald-500/20 text-emerald-400 font-bold rounded border border-emerald-500/40">
                          {confusionMatrix[0]?.[0] || 0}
                        </div>
                        <div className="p-3 bg-red-500/20 text-red-400 font-bold rounded border border-red-500/40">
                          {confusionMatrix[0]?.[1] || 0}
                        </div>
                        <div className="text-sm font-semibold text-text-primary">Actual: Yes</div>
                        <div className="p-3 bg-red-500/20 text-red-400 font-bold rounded border border-red-500/40">
                          {confusionMatrix[1]?.[0] || 0}
                        </div>
                        <div className="p-3 bg-emerald-500/20 text-emerald-400 font-bold rounded border border-emerald-500/40">
                          {confusionMatrix[1]?.[1] || 0}
                        </div>
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div className="bg-bg-primary/50 rounded-lg p-3">
                        <div className="text-text-muted mb-1">True Negatives</div>
                        <div className="text-lg font-bold text-emerald-400">{confusionMatrix[0]?.[0] || 0}</div>
                      </div>
                      <div className="bg-bg-primary/50 rounded-lg p-3">
                        <div className="text-text-muted mb-1">True Positives</div>
                        <div className="text-lg font-bold text-emerald-400">{confusionMatrix[1]?.[1] || 0}</div>
                      </div>
                      <div className="bg-bg-primary/50 rounded-lg p-3">
                        <div className="text-text-muted mb-1">False Positives</div>
                        <div className="text-lg font-bold text-red-400">{confusionMatrix[0]?.[1] || 0}</div>
                      </div>
                      <div className="bg-bg-primary/50 rounded-lg p-3">
                        <div className="text-text-muted mb-1">False Negatives</div>
                        <div className="text-lg font-bold text-red-400">{confusionMatrix[1]?.[0] || 0}</div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Classification Report */}
            {Object.keys(classificationReport).length > 0 && (
              <div className="card border-2 border-border bg-bg-secondary p-6">
                <button
                  onClick={() => toggleSection('classificationReport')}
                  className="w-full flex items-center justify-between mb-4"
                >
                  <h2 className="text-xl font-bold text-text-primary flex items-center gap-2">
                    <FileText className="w-5 h-5" />
                    Classification Report
                  </h2>
                  {expandedSections.classificationReport ? (
                    <ChevronUp className="w-5 h-5 text-text-muted" />
                  ) : (
                    <ChevronDown className="w-5 h-5 text-text-muted" />
                  )}
                </button>
                
                {expandedSections.classificationReport && (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b-2 border-border">
                          <th className="text-left p-2 text-text-primary font-semibold">Class</th>
                          <th className="text-right p-2 text-text-primary font-semibold">Precision</th>
                          <th className="text-right p-2 text-text-primary font-semibold">Recall</th>
                          <th className="text-right p-2 text-text-primary font-semibold">F1-Score</th>
                          <th className="text-right p-2 text-text-primary font-semibold">Support</th>
                        </tr>
                      </thead>
                      <tbody>
                        {Object.entries(classificationReport).map(([key, value]: [string, any]) => {
                          if (typeof value === 'object' && value.precision !== undefined) {
                            return (
                              <tr key={key} className="border-b border-border/50">
                                <td className="p-2 font-semibold text-text-primary">{key === '0' ? 'No Churn' : key === '1' ? 'Churn' : key}</td>
                                <td className="p-2 text-right text-text-primary">{(value.precision * 100).toFixed(2)}%</td>
                                <td className="p-2 text-right text-text-primary">{(value.recall * 100).toFixed(2)}%</td>
                                <td className="p-2 text-right text-text-primary">{(value['f1-score'] * 100).toFixed(2)}%</td>
                                <td className="p-2 text-right text-text-muted">{value.support?.toFixed(0) || 'N/A'}</td>
                              </tr>
                            );
                          }
                          return null;
                        })}
                        {classificationReport['macro avg'] && (
                          <tr className="border-t-2 border-border bg-bg-primary/30">
                            <td className="p-2 font-semibold text-text-primary">Macro Avg</td>
                            <td className="p-2 text-right text-text-primary">
                              {((classificationReport['macro avg'].precision || 0) * 100).toFixed(2)}%
                            </td>
                            <td className="p-2 text-right text-text-primary">
                              {((classificationReport['macro avg'].recall || 0) * 100).toFixed(2)}%
                            </td>
                            <td className="p-2 text-right text-text-primary">
                              {((classificationReport['macro avg']['f1-score'] || 0) * 100).toFixed(2)}%
                            </td>
                            <td className="p-2 text-right text-text-muted">
                              {classificationReport['macro avg'].support?.toFixed(0) || 'N/A'}
                            </td>
                          </tr>
                        )}
                        {classificationReport['weighted avg'] && (
                          <tr className="border-t border-border bg-bg-primary/30">
                            <td className="p-2 font-semibold text-text-primary">Weighted Avg</td>
                            <td className="p-2 text-right text-text-primary">
                              {((classificationReport['weighted avg'].precision || 0) * 100).toFixed(2)}%
                            </td>
                            <td className="p-2 text-right text-text-primary">
                              {((classificationReport['weighted avg'].recall || 0) * 100).toFixed(2)}%
                            </td>
                            <td className="p-2 text-right text-text-primary">
                              {((classificationReport['weighted avg']['f1-score'] || 0) * 100).toFixed(2)}%
                            </td>
                            <td className="p-2 text-right text-text-muted">
                              {classificationReport['weighted avg'].support?.toFixed(0) || 'N/A'}
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}

            {/* Feature Importance */}
            {Object.keys(topFeatures).length > 0 && (
              <div className="card border-2 border-border bg-bg-secondary p-6">
                <button
                  onClick={() => toggleSection('featureImportance')}
                  className="w-full flex items-center justify-between mb-4"
                >
                  <h2 className="text-xl font-bold text-text-primary flex items-center gap-2">
                    <TrendingUp className="w-5 h-5" />
                    Feature Importance
                  </h2>
                  {expandedSections.featureImportance ? (
                    <ChevronUp className="w-5 h-5 text-text-muted" />
                  ) : (
                    <ChevronDown className="w-5 h-5 text-text-muted" />
                  )}
                </button>
                
                {expandedSections.featureImportance && (
                  <div className="space-y-3">
                    {Object.entries(topFeatures).slice(0, 10).map(([feature, importance]: [string, any]) => (
                      <div key={feature} className="bg-bg-primary/50 rounded-lg p-3">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-sm font-semibold text-text-primary capitalize">
                            {feature.replace(/_/g, ' ')}
                          </span>
                          <span className="text-sm font-bold text-primary">
                            {(importance * 100).toFixed(2)}%
                          </span>
                        </div>
                        <div className="w-full bg-bg-secondary rounded-full h-2 overflow-hidden">
                          <div
                            className="h-full bg-primary transition-all"
                            style={{ width: `${importance * 100}%` }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Model Versions */}
            {model_versions && model_versions.length > 0 && (
              <div className="card border-2 border-border bg-bg-secondary p-6">
                <div className="flex items-center justify-between mb-4">
                  <button
                    onClick={() => toggleSection('modelVersions')}
                    className="flex-1 flex items-center justify-between"
                  >
                    <h2 className="text-xl font-bold text-text-primary flex items-center gap-2">
                      <Layers className="w-5 h-5" />
                      Model Versions ({model_versions.length})
                    </h2>
                    {expandedSections.modelVersions ? (
                      <ChevronUp className="w-5 h-5 text-text-muted" />
                    ) : (
                      <ChevronDown className="w-5 h-5 text-text-muted" />
                    )}
                  </button>
                  {model_versions.length >= 2 && (
                    <button
                      onClick={() => navigate(`/projects/${projectId}/compare`)}
                      className="ml-4 px-4 py-2 bg-primary hover:bg-primary/90 text-white rounded-lg text-sm font-medium transition-colors flex items-center gap-2"
                    >
                      <BarChart3 className="w-4 h-4" />
                      Compare Models
                    </button>
                  )}
                </div>
                
                {expandedSections.modelVersions && (
                  <div className="space-y-4">
                    {model_versions.map((version: any) => (
                      <div
                        key={version.version}
                        className={`bg-bg-primary/50 rounded-lg p-5 border-2 ${
                          version.status === "latest"
                            ? "border-emerald-500/40 bg-emerald-500/5"
                            : "border-border"
                        }`}
                      >
                        <div className="flex items-center justify-between mb-4">
                          <div className="flex items-center gap-3">
                            <div className={`w-12 h-12 rounded-lg flex items-center justify-center font-bold text-lg ${
                              version.status === "latest"
                                ? "bg-emerald-500/20 text-emerald-400 border-2 border-emerald-500/40"
                                : "bg-bg-secondary text-text-muted border-2 border-border"
                            }`}>
                              v{version.version}
                            </div>
                            <div>
                              <div className="text-base font-bold text-text-primary flex items-center gap-2">
                                Version {version.version}
                                {version.status === "latest" && (
                                  <span className="px-2 py-0.5 bg-emerald-500/20 text-emerald-400 text-xs font-semibold rounded border border-emerald-500/40">
                                    Latest
                                  </span>
                                )}
                              </div>
                              <div className="text-xs text-text-muted mt-1">
                                {version.created_at
                                  ? new Date(version.created_at).toLocaleString()
                                  : "Unknown date"}
                              </div>
                            </div>
                          </div>
                        </div>
                        
                        {version.metrics && (
                          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                            {version.metrics.accuracy && (
                              <div className="bg-bg-secondary rounded-lg p-3">
                                <div className="text-xs text-text-muted mb-1">Accuracy</div>
                                <div className="text-lg font-bold text-emerald-400">
                                  {(version.metrics.accuracy * 100).toFixed(2)}%
                                </div>
                              </div>
                            )}
                            {version.metrics.precision && (
                              <div className="bg-bg-secondary rounded-lg p-3">
                                <div className="text-xs text-text-muted mb-1">Precision</div>
                                <div className="text-lg font-bold text-blue-400">
                                  {(version.metrics.precision * 100).toFixed(2)}%
                                </div>
                              </div>
                            )}
                            {version.metrics.recall && (
                              <div className="bg-bg-secondary rounded-lg p-3">
                                <div className="text-xs text-text-muted mb-1">Recall</div>
                                <div className="text-lg font-bold text-purple-400">
                                  {(version.metrics.recall * 100).toFixed(2)}%
                                </div>
                              </div>
                            )}
                            {version.metrics.f1_score && (
                              <div className="bg-bg-secondary rounded-lg p-3">
                                <div className="text-xs text-text-muted mb-1">F1 Score</div>
                                <div className="text-lg font-bold text-cyan-400">
                                  {(version.metrics.f1_score * 100).toFixed(2)}%
                                </div>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Right Column - Sidebar */}
          <div className="space-y-6">
            {/* Dataset Information */}
            <div className="card border-2 border-border bg-bg-secondary p-6">
              <h2 className="text-lg font-bold text-text-primary mb-4 flex items-center gap-2">
                <Database className="w-5 h-5" />
                Datasets
              </h2>
              <div className="space-y-3">
                <div className="bg-bg-primary/50 rounded-lg p-4">
                  <div className="text-xs text-text-muted mb-1">Total Datasets</div>
                  <div className="text-2xl font-bold text-primary">
                    {datasets?.count || 0}
                  </div>
                </div>
                <div className="bg-bg-primary/50 rounded-lg p-4">
                  <div className="text-xs text-text-muted mb-1">Total Rows</div>
                  <div className="text-2xl font-bold text-primary">
                    {datasets?.total_rows?.toLocaleString() || 0}
                  </div>
                </div>
              </div>
            </div>

            {/* Prediction Statistics */}
            <div className="card border-2 border-border bg-bg-secondary p-6">
              <h2 className="text-lg font-bold text-text-primary mb-4 flex items-center gap-2">
                <Activity className="w-5 h-5" />
                Predictions
              </h2>
              <div className="space-y-3">
                <div className="bg-bg-primary/50 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs text-text-muted">Total</span>
                    <Zap className="w-4 h-4 text-yellow-400" />
                  </div>
                  <div className="text-2xl font-bold text-yellow-400">
                    {prediction_stats?.total_predictions?.toLocaleString() || 0}
                  </div>
                </div>
                <div className="bg-bg-primary/50 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs text-text-muted">SDK</span>
                    <Code className="w-4 h-4 text-blue-400" />
                  </div>
                  <div className="text-xl font-bold text-blue-400">
                    {prediction_stats?.sdk_predictions?.toLocaleString() || 0}
                  </div>
                  {prediction_stats?.total_predictions > 0 && (
                    <div className="text-xs text-text-muted mt-1">
                      {((prediction_stats.sdk_predictions / prediction_stats.total_predictions) * 100).toFixed(1)}%
                    </div>
                  )}
                </div>
                <div className="bg-bg-primary/50 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs text-text-muted">Web</span>
                    <Globe className="w-4 h-4 text-green-400" />
                  </div>
                  <div className="text-xl font-bold text-green-400">
                    {prediction_stats?.web_predictions?.toLocaleString() || 0}
                  </div>
                  {prediction_stats?.total_predictions > 0 && (
                    <div className="text-xs text-text-muted mt-1">
                      {((prediction_stats.web_predictions / prediction_stats.total_predictions) * 100).toFixed(1)}%
                    </div>
                  )}
                </div>
                <div className="bg-bg-primary/50 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs text-text-muted">Response Time</span>
                    <Clock className="w-4 h-4 text-purple-400" />
                  </div>
                  <div className="text-xl font-bold text-purple-400">
                    {performance?.avg_response_time_ms || 0}ms
                  </div>
                </div>
              </div>
            </div>

            {/* Drift Status */}
            <div className="card border-2 border-border bg-bg-secondary p-6">
              <h2 className="text-lg font-bold text-text-primary mb-4 flex items-center gap-2">
                <AlertTriangle className="w-5 h-5" />
                Drift Detection
              </h2>
              <div className="space-y-3">
                <div className="bg-bg-primary/50 rounded-lg p-4">
                  <div className="text-xs text-text-muted mb-1">Status</div>
                  <div className={`text-lg font-bold ${
                    drift_history?.summary?.drift_alerts > 0
                      ? 'text-red-400'
                      : drift_history?.summary?.avg_drift_score > 0.05
                      ? 'text-yellow-400'
                      : 'text-emerald-400'
                  }`}>
                    {drift_history?.summary?.drift_alerts > 0
                      ? 'Alert'
                      : drift_history?.summary?.avg_drift_score > 0.05
                      ? 'Warning'
                      : 'Healthy'}
                  </div>
                </div>
                <div className="bg-bg-primary/50 rounded-lg p-4">
                  <div className="text-xs text-text-muted mb-1">Total Checks</div>
                  <div className="text-xl font-bold text-text-primary">
                    {drift_history?.summary?.total_checks || 0}
                  </div>
                </div>
                <div className="bg-bg-primary/50 rounded-lg p-4">
                  <div className="text-xs text-text-muted mb-1">Avg Drift Score</div>
                  <div className="text-xl font-bold text-text-primary">
                    {drift_history?.summary?.avg_drift_score?.toFixed(4) || '0.0000'}
                  </div>
                </div>
                <div className="bg-bg-primary/50 rounded-lg p-4">
                  <div className="text-xs text-text-muted mb-1">Alerts</div>
                  <div className="text-xl font-bold text-yellow-400">
                    {drift_history?.summary?.drift_alerts || 0}
                  </div>
                </div>
              </div>
            </div>

            {/* Class Distribution */}
            {latestMetrics.class_distribution && (
              <div className="card border-2 border-border bg-bg-secondary p-6">
                <h2 className="text-lg font-bold text-text-primary mb-4 flex items-center gap-2">
                  <Users className="w-5 h-5" />
                  Class Distribution
                </h2>
                <div className="space-y-3">
                  {Object.entries(latestMetrics.class_distribution).map(([label, count]: [string, any]) => (
                    <div key={label} className="bg-bg-primary/50 rounded-lg p-4">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-semibold text-text-primary">
                          {label === '0' ? 'No Churn' : label === '1' ? 'Churn' : label}
                        </span>
                        <span className="text-lg font-bold text-primary">
                          {Number(count).toLocaleString()}
                        </span>
                      </div>
                      <div className="w-full bg-bg-secondary rounded-full h-2 overflow-hidden">
                        <div
                          className={`h-full ${
                            label === '0' ? 'bg-emerald-400' : 'bg-red-400'
                          }`}
                          style={{
                            width: `${(Number(count) / (latestMetrics.n_train_samples || 1)) * 100}%`
                          }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Drift Alerts */}
            {drift_alerts && drift_alerts.length > 0 && (
              <div className="card border-2 border-yellow-500/50 bg-yellow-500/10 p-6">
                <h2 className="text-lg font-bold text-yellow-400 mb-4 flex items-center gap-2">
                  <AlertTriangle className="w-5 h-5" />
                  Active Alerts ({drift_alerts.length})
                </h2>
                <div className="space-y-3">
                  {drift_alerts.slice(0, 5).map((alert: any, idx: number) => (
                    <div
                      key={idx}
                      className="bg-bg-primary/50 rounded-lg p-3 border border-yellow-500/30"
                    >
                      <div className="text-sm font-semibold text-text-primary mb-1">
                        {alert.feature}
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-text-muted">
                          {new Date(alert.detected_at).toLocaleDateString()}
                        </span>
                        <span className={`px-2 py-1 rounded text-xs font-semibold ${
                          alert.severity === "critical"
                            ? "bg-red-500/20 text-red-400"
                            : "bg-yellow-500/20 text-yellow-400"
                        }`}>
                          {alert.severity}
                        </span>
                      </div>
                      <div className="text-xs text-yellow-400 mt-1">
                        Score: {(alert.drift_score * 100).toFixed(2)}%
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </Layout>
  );
}
