import { useState, useEffect } from 'react';
import Layout from '@/components/Layout';
import useAuth from '@/hooks/useAuth';
import { api, type DashboardOverview, type DashboardAnalytics } from '@/lib/api';
import { AlertCircle, TrendingUp, FolderOpen, Database, Activity, Target, Zap, BarChart3 } from 'lucide-react';
import { 
  BarChart, 
  Bar, 
  LineChart, 
  Line, 
  PieChart, 
  Pie, 
  Cell,
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend, 
  ResponsiveContainer 
} from 'recharts';

export default function Dashboard() {
  const { accessToken } = useAuth();
  const [data, setData] = useState<DashboardOverview | null>(null);
  const [analytics, setAnalytics] = useState<DashboardAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!accessToken) return;

    const fetchDashboard = async () => {
      try {
        const [overview, analyticsData] = await Promise.all([
          api.getDashboardOverview(accessToken),
          api.getDashboardAnalytics(accessToken, 30)
        ]);
        setData(overview);
        setAnalytics(analyticsData);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load dashboard');
      } finally {
        setLoading(false);
      }
    };

    fetchDashboard();
  }, [accessToken]);

  if (loading) {
    return (
      <Layout>
        <div className="p-8">
          <div className="animate-pulse space-y-6">
            <div className="h-8 bg-bg-secondary rounded w-64"></div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="h-32 bg-bg-secondary rounded"></div>
              ))}
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {[1, 2].map((i) => (
                <div key={i} className="h-80 bg-bg-secondary rounded"></div>
              ))}
            </div>
          </div>
        </div>
      </Layout>
    );
  }

  if (error || !data) {
    return (
      <Layout>
        <div className="p-8">
          <div className="bg-red-500/10 border-2 border-red-500 rounded-lg p-4 text-red-400 text-sm">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4" />
              {error || 'No data available'}
            </div>
          </div>
        </div>
      </Layout>
    );
  }

  // Prepare chart data with null checks
  const projectsData = [
    { name: 'Total', value: data.summary?.projects?.total_projects || 0 },
    { name: 'Active', value: data.summary?.projects?.active_projects || 0 },
    { name: 'Training', value: data.summary?.projects?.training_projects || 0 },
    { name: 'New', value: data.summary?.projects?.new_projects || 0 },
  ];

  // Convert analytics trends to chart data
  const trendsData = analytics?.trends ? Object.keys(analytics.trends.projects_created || {}).map(date => ({
    date: new Date(date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    projects: analytics.trends.projects_created[date] || 0,
    models: analytics.trends.models_trained[date] || 0,
    predictions: analytics.trends.predictions_served[date] || 0,
  })) : [];

  const activityData = analytics?.totals ? [
    { name: 'Projects', value: analytics.totals.projects || 0 },
    { name: 'Models', value: analytics.totals.models || 0 },
    { name: 'Predictions', value: analytics.totals.predictions || 0 },
  ] : [
    { name: 'Projects', value: data.recent_activity?.new_projects_7d || 0 },
    { name: 'Models', value: data.recent_activity?.new_models_7d || 0 },
    { name: 'Predictions', value: data.recent_activity?.predictions_7d || 0 },
  ];

  const performanceData = data.top_models?.slice(0, 5).map((model) => ({
    name: model.project_name?.substring(0, 20) || 'Unknown',
    accuracy: model.accuracy ? (model.accuracy * 100).toFixed(1) : 0,
  })) || [];

  const featureTypesData = data.summary?.features?.feature_types ? [
    { name: 'Categorical', value: data.summary.features.feature_types.categorical || 0 },
    { name: 'Numerical', value: data.summary.features.feature_types.numerical || 0 },
  ] : [];

  const COLORS = ['#10b981', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#ec4899'];

  const getHealthColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'excellent': return 'text-emerald-400 bg-emerald-500/20 border-emerald-500/40';
      case 'good': return 'text-blue-400 bg-blue-500/20 border-blue-500/40';
      case 'warning': return 'text-yellow-400 bg-yellow-500/20 border-yellow-500/40';
      default: return 'text-zinc-400 bg-zinc-500/20 border-zinc-500/40';
    }
  };

  return (
    <Layout>
      <div className="p-8">
        {/* Page Header */}
        <div className="mb-8">
          <div className="flex justify-between items-start mb-2">
            <div>
              <h1 className="text-3xl font-bold text-text-primary mb-2">Dashboard Overview</h1>
              <p className="text-text-muted">
                Welcome back, <span className="text-primary font-semibold">{data.user?.name || 'User'}</span>
              </p>
            </div>
            {data.health && (
              <div className={`px-4 py-2 rounded-lg border font-semibold text-sm ${getHealthColor(data.health.status)}`}>
                Health: {data.health.score || 0}/100 ({data.health.status || 'unknown'})
              </div>
            )}
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <div className="card border-2 border-border bg-bg-secondary p-4">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 rounded-lg bg-orange-500/20 border border-orange-500/40 flex items-center justify-center">
                <FolderOpen className="w-5 h-5 text-orange-400" strokeWidth={2.5} />
              </div>
              <div>
                <p className="text-xs text-text-muted font-medium uppercase tracking-wide">Total Projects</p>
                <p className="text-2xl font-bold text-text-primary">{data.summary?.projects?.total_projects || 0}</p>
              </div>
            </div>
            <p className="text-xs text-text-muted">
              {data.summary?.projects?.active_projects || 0} active
            </p>
          </div>

          <div className="card border-2 border-border bg-bg-secondary p-4">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 rounded-lg bg-blue-500/20 border border-blue-500/40 flex items-center justify-center">
                <Target className="w-5 h-5 text-blue-400" strokeWidth={2.5} />
              </div>
              <div>
                <p className="text-xs text-text-muted font-medium uppercase tracking-wide">Total Models</p>
                <p className="text-2xl font-bold text-text-primary">{data.summary?.models?.total_models || 0}</p>
              </div>
            </div>
            <p className="text-xs text-text-muted">
              {data.summary?.models?.total_versions || 0} versions
            </p>
          </div>

          <div className="card border-2 border-border bg-bg-secondary p-4">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 rounded-lg bg-purple-500/20 border border-purple-500/40 flex items-center justify-center">
                <Database className="w-5 h-5 text-purple-400" strokeWidth={2.5} />
              </div>
              <div>
                <p className="text-xs text-text-muted font-medium uppercase tracking-wide">Datasets</p>
                <p className="text-2xl font-bold text-text-primary">{data.summary?.datasets?.total_datasets || 0}</p>
              </div>
            </div>
            <p className="text-xs text-text-muted">
              {data.summary?.datasets?.total_rows_processed?.toLocaleString() || 0} rows
            </p>
          </div>

          <div className="card border-2 border-border bg-bg-secondary p-4">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 rounded-lg bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center">
                <Activity className="w-5 h-5 text-emerald-400" strokeWidth={2.5} />
              </div>
              <div>
                <p className="text-xs text-text-muted font-medium uppercase tracking-wide">Predictions</p>
                <p className="text-2xl font-bold text-text-primary">{data.summary?.predictions_served || 0}</p>
              </div>
            </div>
            <p className="text-xs text-text-muted">
              {data.recent_activity?.predictions_7d || 0} last 7 days
            </p>
          </div>
        </div>

        {/* Charts Row 1 */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          {/* Projects Distribution */}
          <div className="card border-2 border-border bg-bg-secondary p-6">
            <h3 className="text-lg font-bold text-text-primary mb-4 flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-orange-400" />
              Projects Overview
            </h3>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={projectsData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                <XAxis dataKey="name" stroke="#a1a1aa" tick={{ fill: '#a1a1aa', fontSize: 12 }} />
                <YAxis stroke="#a1a1aa" tick={{ fill: '#a1a1aa', fontSize: 12 }} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#18181b', border: '2px solid #27272a', borderRadius: '8px' }}
                  labelStyle={{ color: '#e4e4e7' }}
                  itemStyle={{ color: '#fb923c' }}
                />
                <Bar dataKey="value" fill="#fb923c" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Recent Activity */}
          <div className="card border-2 border-border bg-bg-secondary p-6">
            <h3 className="text-lg font-bold text-text-primary mb-4 flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-cyan-400" />
              Activity Totals ({analytics?.period_days || 30} Days)
            </h3>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={activityData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                <XAxis dataKey="name" stroke="#a1a1aa" tick={{ fill: '#a1a1aa', fontSize: 12 }} />
                <YAxis stroke="#a1a1aa" tick={{ fill: '#a1a1aa', fontSize: 12 }} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#18181b', border: '2px solid #27272a', borderRadius: '8px' }}
                  labelStyle={{ color: '#e4e4e7' }}
                  itemStyle={{ color: '#3b82f6' }}
                />
                <Bar dataKey="value" fill="#3b82f6" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Charts Row 2 */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          {/* Trends Over Time */}
          {trendsData.length > 0 && (
            <div className="card border-2 border-border bg-bg-secondary p-6">
              <h3 className="text-lg font-bold text-text-primary mb-4 flex items-center gap-2">
                <Activity className="w-5 h-5 text-purple-400" />
                Activity Trends
              </h3>
              <ResponsiveContainer width="100%" height={250}>
                <LineChart data={trendsData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                  <XAxis dataKey="date" stroke="#a1a1aa" tick={{ fill: '#a1a1aa', fontSize: 10 }} />
                  <YAxis stroke="#a1a1aa" tick={{ fill: '#a1a1aa', fontSize: 12 }} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#18181b', border: '2px solid #27272a', borderRadius: '8px' }}
                    labelStyle={{ color: '#e4e4e7' }}
                  />
                  <Legend wrapperStyle={{ color: '#a1a1aa', fontSize: 12 }} />
                  <Line type="monotone" dataKey="projects" stroke="#fb923c" strokeWidth={2} name="Projects" />
                  <Line type="monotone" dataKey="models" stroke="#3b82f6" strokeWidth={2} name="Models" />
                  <Line type="monotone" dataKey="predictions" stroke="#a78bfa" strokeWidth={2} name="Predictions" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
          {/* Model Performance */}
          {performanceData.length > 0 && (
            <div className="card border-2 border-border bg-bg-secondary p-6">
              <h3 className="text-lg font-bold text-text-primary mb-4 flex items-center gap-2">
                <Zap className="w-5 h-5 text-amber-400" />
                Top Models Performance
              </h3>
              <ResponsiveContainer width="100%" height={250}>
                <LineChart data={performanceData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                  <XAxis dataKey="name" stroke="#a1a1aa" tick={{ fill: '#a1a1aa', fontSize: 10 }} />
                  <YAxis stroke="#a1a1aa" tick={{ fill: '#a1a1aa', fontSize: 12 }} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#18181b', border: '2px solid #27272a', borderRadius: '8px' }}
                    labelStyle={{ color: '#e4e4e7' }}
                    itemStyle={{ color: '#fbbf24' }}
                  />
                  <Legend wrapperStyle={{ color: '#a1a1aa', fontSize: 12 }} />
                  <Line type="monotone" dataKey="accuracy" stroke="#fbbf24" strokeWidth={2} dot={{ r: 4 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Feature Types Distribution */}
          {featureTypesData.length > 0 && (
            <div className="card border-2 border-border bg-bg-secondary p-6">
              <h3 className="text-lg font-bold text-text-primary mb-4">Feature Types Distribution</h3>
              <ResponsiveContainer width="100%" height={250}>
                <PieChart>
                  <Pie
                    data={featureTypesData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {featureTypesData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#18181b', border: '2px solid #27272a', borderRadius: '8px' }}
                    labelStyle={{ color: '#e4e4e7' }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>

        {/* Performance Metrics */}
        {data.performance && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <div className="card border-2 border-border bg-bg-secondary p-4">
              <p className="text-xs text-text-muted font-medium uppercase tracking-wide mb-1">Avg Accuracy</p>
              <p className="text-2xl font-bold text-cyan-400">
                {data.performance.avg_accuracy ? (data.performance.avg_accuracy * 100).toFixed(1) : 0}%
              </p>
            </div>
            <div className="card border-2 border-border bg-bg-secondary p-4">
              <p className="text-xs text-text-muted font-medium uppercase tracking-wide mb-1">Max Accuracy</p>
              <p className="text-2xl font-bold text-emerald-400">
                {data.performance.max_accuracy ? (data.performance.max_accuracy * 100).toFixed(1) : 0}%
              </p>
            </div>
            <div className="card border-2 border-border bg-bg-secondary p-4">
              <p className="text-xs text-text-muted font-medium uppercase tracking-wide mb-1">Avg F1 Score</p>
              <p className="text-2xl font-bold text-blue-400">
                {data.performance.avg_f1_score ? (data.performance.avg_f1_score * 100).toFixed(1) : 0}%
              </p>
            </div>
            <div className="card border-2 border-border bg-bg-secondary p-4">
              <p className="text-xs text-text-muted font-medium uppercase tracking-wide mb-1">Drift Alerts</p>
              <p className="text-2xl font-bold text-yellow-400">
                {analytics?.totals?.drift_checks || data.monitoring?.drift_alerts || 0}
              </p>
              <p className="text-xs text-text-muted mt-1">
                {analytics?.period_days || 30} days
              </p>
            </div>
          </div>
        )}

        {/* Health Factors */}
        {data.health?.factors && data.health.factors.length > 0 && (
          <div className="card border-2 border-border bg-bg-secondary p-6">
            <h3 className="text-lg font-bold text-text-primary mb-4">Health Factors</h3>
            <div className="flex flex-wrap gap-2">
              {data.health.factors.map((factor, idx) => (
                <span
                  key={idx}
                  className={`px-3 py-1.5 text-sm font-medium rounded-lg border ${
                    idx % 5 === 0 ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40' :
                    idx % 5 === 1 ? 'bg-blue-500/20 text-blue-300 border-blue-500/40' :
                    idx % 5 === 2 ? 'bg-purple-500/20 text-purple-300 border-purple-500/40' :
                    idx % 5 === 3 ? 'bg-orange-500/20 text-orange-300 border-orange-500/40' :
                    'bg-cyan-500/20 text-cyan-300 border-cyan-500/40'
                  }`}
                >
                  {factor}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
}
