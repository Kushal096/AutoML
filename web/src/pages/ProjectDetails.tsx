import { useState, useEffect, useCallback } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import Layout from '@/components/Layout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import useAuth from '@/hooks/useAuth';
import { api, type ProjectResponse, type System } from '@/lib/api';
import { ArrowLeft, Calendar, Zap, Upload, PlayCircle, BarChart3, AlertCircle, Loader2, CheckCircle2, FileText } from 'lucide-react';

export default function ProjectDetails() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const { accessToken } = useAuth();
  const [project, setProject] = useState<ProjectResponse | null>(null);
  const [system, setSystem] = useState<System | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Upload dataset state
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadContext, setUploadContext] = useState('');
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadResponse, setUploadResponse] = useState<any>(null);
  
  // Train model state
  const [training, setTraining] = useState(false);
  const [trainSuccess, setTrainSuccess] = useState(false);
  const [trainError, setTrainError] = useState<string | null>(null);
  const [trainingStatus, setTrainingStatus] = useState<any>(null);
  const [modelMetrics, setModelMetrics] = useState<any>(null);
  const [pollingTraining, setPollingTraining] = useState(false);
  const [datasets, setDatasets] = useState<any[]>([]);
  const [models, setModels] = useState<any[]>([]);

  // Function to refetch project details and related data
  const refetchProjectData = useCallback(async () => {
    if (!accessToken || !projectId) return;

    try {
      // Fetch project details
      const projectData = await api.getProject(accessToken, projectId);
      setProject(projectData);

      // Fetch system details
      const systemsData = await api.getSystems(accessToken);
      const matchedSystem = systemsData.find(s => s.id === projectData.system_id);
      if (matchedSystem) {
        setSystem(matchedSystem);
      }

      // Fetch datasets
      try {
        const datasetsData = await api.listDatasets(accessToken, projectId);
        setDatasets(Array.isArray(datasetsData) ? datasetsData : []);
      } catch (err) {
        console.error('Failed to fetch datasets:', err);
        setDatasets([]);
      }

      // Fetch models
      try {
        const modelsData = await api.getModels(accessToken, projectId);
        setModels(Array.isArray(modelsData) ? modelsData : []);
      } catch (err) {
        console.error('Failed to fetch models:', err);
        setModels([]);
      }
    } catch (err) {
      console.error('Failed to refetch project data:', err);
    }
  }, [accessToken, projectId]);

  useEffect(() => {
    if (!accessToken || !projectId) return;

    const fetchProjectDetails = async () => {
      setLoading(true);
      await refetchProjectData();
      setLoading(false);
    };

    fetchProjectDetails();
  }, [accessToken, projectId, refetchProjectData]);

  // Poll for training status when auto-training starts
  useEffect(() => {
    if (!pollingTraining || !accessToken || !projectId) return;

    const pollTrainingStatus = async () => {
      try {
        const status = await api.getTrainingStatus(accessToken, projectId);
        setTrainingStatus(status);

        // If training completed, fetch model metrics and refresh project data
        if (status.status === 'completed') {
          setPollingTraining(false);
          setTraining(false);
          setTrainSuccess(true);
          
          // Fetch latest model with metrics
          try {
            const model = await api.getLatestModel(accessToken, projectId);
            setModelMetrics(model);
          } catch (err) {
            console.error('Failed to fetch model metrics:', err);
          }

          // Refresh project data to show updated status and new models
          await refetchProjectData();
        } else if (status.status === 'failed') {
          setPollingTraining(false);
          setTraining(false);
          setTrainError(status.message || 'Training failed');
          
          // Still refresh project data to show current status
          await refetchProjectData();
        }
      } catch (err) {
        console.error('Failed to poll training status:', err);
      }
    };

    // Poll immediately, then every 3 seconds
    pollTrainingStatus();
    const interval = setInterval(pollTrainingStatus, 3000);

    return () => clearInterval(interval);
  }, [pollingTraining, accessToken, projectId]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setUploadFile(e.target.files[0]);
      setUploadSuccess(false);
      setUploadError(null);
    }
  };

  const handleUploadDataset = async () => {
    if (!uploadFile || !accessToken || !projectId) {
      setUploadError('Please select a file to upload');
      return;
    }

    setUploading(true);
    setUploadProgress(0);
    setUploadError(null);
    setUploadSuccess(false);

    // Simulate progress (since actual upload progress requires XHR)
    const progressInterval = setInterval(() => {
      setUploadProgress((prev) => {
        if (prev >= 95) {
          clearInterval(progressInterval);
          return 95;
        }
        return prev + 5;
      });
    }, 150);

    try {
      const response = await api.uploadDataset(accessToken, projectId, uploadFile, uploadContext);
      clearInterval(progressInterval);
      setUploadProgress(100);
      setUploadResponse(response);
      setUploadSuccess(true);
      setUploadFile(null);
      setUploadContext('');
      // Reset file input
      const fileInput = document.getElementById('dataset-file') as HTMLInputElement;
      if (fileInput) fileInput.value = '';
      
      // Immediately refresh project data to show updated status and new dataset
      await refetchProjectData();
      
      // If auto-training is enabled, start polling for training status
      if (response.suggested_system_type) {
        setPollingTraining(true);
        setTraining(true);
      }
    } catch (err) {
      clearInterval(progressInterval);
      setUploadError(err instanceof Error ? err.message : 'Failed to upload dataset');
    } finally {
      setTimeout(() => {
        setUploading(false);
        setUploadProgress(0);
      }, 500);
    }
  };

  const handleTrainModel = async () => {
    if (!accessToken || !projectId) return;

    setTraining(true);
    setTrainError(null);
    setTrainSuccess(false);

    try {
      await api.trainModel(accessToken, projectId);
      setTrainSuccess(true);
    } catch (err) {
      setTrainError(err instanceof Error ? err.message : 'Failed to start training');
    } finally {
      setTraining(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'created':
        return 'bg-blue-500/20 text-blue-300 border-blue-500/40';
      case 'training':
        return 'bg-yellow-500/20 text-yellow-300 border-yellow-500/40';
      case 'deployed':
        return 'bg-primary/20 text-primary border-primary/40';
      case 'failed':
        return 'bg-red-500/20 text-red-300 border-red-500/40';
      default:
        return 'bg-zinc-500/20 text-zinc-300 border-zinc-500/40';
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (loading) {
    return (
      <Layout>
        <div className="p-8">
          <div className="max-w-6xl mx-auto">
            <div className="animate-pulse space-y-6">
              <div className="h-12 bg-bg-secondary rounded-lg w-1/3"></div>
              <div className="h-64 bg-bg-secondary rounded-lg"></div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="h-40 bg-bg-secondary rounded-lg"></div>
                <div className="h-40 bg-bg-secondary rounded-lg"></div>
                <div className="h-40 bg-bg-secondary rounded-lg"></div>
              </div>
            </div>
          </div>
        </div>
      </Layout>
    );
  }

  if (error || !project) {
    return (
      <Layout>
        <div className="p-8">
          <div className="max-w-6xl mx-auto">
            <div className="bg-red-500/10 border-2 border-red-500 rounded-lg p-6 text-red-400 flex items-center gap-3">
              <AlertCircle className="w-6 h-6" />
              <div>
                <h3 className="font-semibold mb-1">Error Loading Project</h3>
                <p className="text-sm">{error || 'Project not found'}</p>
              </div>
            </div>
            <Button onClick={() => navigate('/projects')} className="mt-4">
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Projects
            </Button>
          </div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="p-8">
        <div className="max-w-[1560px] mx-auto">
          {/* Header */}
          <div className="mb-8">
            <Button
              onClick={() => navigate('/projects')}
              variant="ghost"
              className="mb-4 -ml-2 text-text-muted hover:text-text-primary"
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Projects
            </Button>
            <div className="flex items-start justify-between">
              <div>
                <h1 className="text-3xl font-bold text-text-primary mb-2">
                  {project.name}
                </h1>
                <div className="flex items-center gap-3">
                  <span className={`px-3 py-1.5 rounded-full text-xs font-bold border-2 ${getStatusColor(project.status)} uppercase tracking-wide`}>
                    {project.status}
                  </span>
                  {system && (
                    <span className="text-sm text-text-muted">
                      Using {system.name}
                    </span>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Main Info Card */}
          <div className="card border-2 border-border bg-bg-secondary rounded-xl p-8 mb-6">
            <h2 className="text-lg font-bold text-text-primary mb-6">Project Information</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <p className="text-xs text-text-muted mb-2 uppercase tracking-wide font-semibold">Project ID</p>
                <p className="text-sm text-text-primary font-mono bg-bg-primary px-3 py-2 rounded-lg border border-border">
                  {project.id}
                </p>
              </div>
              <div>
                <p className="text-xs text-text-muted mb-2 uppercase tracking-wide font-semibold">System ID</p>
                <p className="text-sm text-text-primary font-mono bg-bg-primary px-3 py-2 rounded-lg border border-border">
                  {project.system_id}
                </p>
              </div>
              <div>
                <p className="text-xs text-text-muted mb-2 uppercase tracking-wide font-semibold">Created</p>
                <p className="text-sm text-text-primary flex items-center gap-2">
                  <Calendar className="w-4 h-4" />
                  {formatDate(project.created_at)}
                </p>
              </div>
              <div>
                <p className="text-xs text-text-muted mb-2 uppercase tracking-wide font-semibold">Last Updated</p>
                <p className="text-sm text-text-primary flex items-center gap-2">
                  <Calendar className="w-4 h-4" />
                  {formatDate(project.updated_at)}
                </p>
              </div>
            </div>
          </div>

          {/* System Details Card */}
          {system && (
            <div className="card border-2 border-border bg-bg-secondary rounded-xl p-8 mb-6">
              <div className="flex items-start gap-4">
                <div className="w-14 h-14 rounded-xl bg-amber-500/20 border-2 border-amber-500/40 flex items-center justify-center shrink-0">
                  <Zap className="w-7 h-7 text-amber-300" strokeWidth={2.5} />
                </div>
                <div className="flex-1">
                  <h2 className="text-lg font-bold text-text-primary mb-2">{system.name}</h2>
                  <p className="text-sm text-text-muted leading-relaxed mb-4">
                    {system.description}
                  </p>
                  {system.default_pipeline && (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {system.default_pipeline.algorithms && (
                        <div className="p-3 bg-bg-primary border border-border rounded-lg">
                          <p className="text-xs text-text-muted mb-2 uppercase tracking-wide font-semibold">Algorithms</p>
                          <div className="flex flex-wrap gap-1.5">
                            {system.default_pipeline.algorithms.map((algo: string, idx: number) => (
                              <span key={idx} className="px-2 py-1 bg-indigo-500/20 text-indigo-300 text-xs font-semibold rounded border border-indigo-500/40">
                                {algo.replace(/_/g, ' ')}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                      {system.default_pipeline.metrics && (
                        <div className="p-3 bg-bg-primary border border-border rounded-lg">
                          <p className="text-xs text-text-muted mb-2 uppercase tracking-wide font-semibold">Metrics</p>
                          <div className="flex flex-wrap gap-1.5">
                            {system.default_pipeline.metrics.map((metric: string, idx: number) => (
                              <span key={idx} className="px-2 py-1 bg-rose-500/20 text-rose-300 text-xs font-semibold rounded border border-rose-500/40">
                                {metric.toUpperCase()}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Upload Dataset Section */}
          <div className="card border-2 border-border bg-bg-secondary rounded-2xl p-10 mb-6">
            <div className="flex items-start gap-4 mb-8">
              <div className="w-14 h-14 rounded-2xl bg-blue-500/20 border-2 border-blue-500/40 flex items-center justify-center shrink-0">
                <Upload className="w-7 h-7 text-blue-300" strokeWidth={2.5} />
              </div>
              <div className="flex-1">
                <h2 className="text-xl font-bold text-text-primary mb-2">Upload and Train Dataset</h2>
                <p className="text-sm text-text-muted leading-relaxed">Upload training data for your model (CSV or Excel format)</p>
              </div>
            </div>

            <div className="space-y-4">
              <div>
                <Label htmlFor="dataset-file" className="text-sm font-semibold mb-2 block">
                  Dataset File *
                </Label>
                <Input
                  id="dataset-file"
                  type="file"
                  accept=".csv,.xlsx,.xls"
                  onChange={handleFileChange}
                  disabled={uploading}
                  className="cursor-pointer"
                />
                {uploadFile && (
                  <div className="mt-2 flex items-center gap-2 text-sm text-text-muted">
                    <FileText className="w-4 h-4" />
                    <span>{uploadFile.name} ({(uploadFile.size / 1024).toFixed(2)} KB)</span>
                  </div>
                )}
              </div>

              <div>
                <Label htmlFor="context" className="text-sm font-semibold mb-2 block">
                  Context (Optional)
                </Label>
                <Input
                  id="context"
                  type="text"
                  placeholder="e.g., Customer churn data from Q4 2025"
                  value={uploadContext}
                  onChange={(e) => setUploadContext(e.target.value)}
                  disabled={uploading}
                />
                <p className="text-xs text-text-muted mt-1">
                  Provide additional context about the dataset to help with processing
                </p>
              </div>

              {uploadSuccess && uploadResponse && (
                <div className="bg-emerald-500/10 border-2 border-emerald-500 rounded-lg p-4 space-y-3">
                  <div className="flex items-center gap-2 text-emerald-400 text-sm font-semibold">
                    <CheckCircle2 className="w-5 h-5" />
                    Dataset uploaded successfully!
                  </div>
                  

                  {/* LLM Analysis */}
                  {uploadResponse.llm_analysis && (
                    <div className="bg-bg-primary/50 rounded-lg p-4 space-y-2">
                      <div className="flex items-center gap-2 text-sm font-semibold text-text-primary mb-2">
                        <Zap className="w-4 h-4 text-yellow-400" />
                        AI Analysis
                      </div>
                      
                      {uploadResponse.suggested_system_type && (
                        <div className="text-sm">
                          <span className="text-text-muted">Detected System:</span>
                          <span className="ml-2 text-emerald-400 font-semibold">{uploadResponse.suggested_system_type}</span>
                          {uploadResponse.llm_analysis.confidence && (
                            <span className="ml-2 text-text-muted">
                              ({(uploadResponse.llm_analysis.confidence * 100).toFixed(0)}% confidence)
                            </span>
                          )}
                        </div>
                      )}
                      
                    
                    </div>
                  )}
                </div>
              )}

              {uploadError && (
                <div className="bg-red-500/10 border-2 border-red-500 rounded-lg p-3 flex items-center gap-2 text-red-400 text-sm">
                  <AlertCircle className="w-4 h-4" />
                  {uploadError}
                </div>
              )}

              <Button
                onClick={handleUploadDataset}
                disabled={!uploadFile || uploading}
                className="w-full border-2 border-blue-500 bg-blue-500 hover:bg-blue-600 text-white relative overflow-hidden"
              >
                {uploading && (
                  <div 
                    className="absolute left-0 top-0 h-full bg-blue-600/30 transition-all duration-300 ease-out"
                    style={{ width: `${uploadProgress}%` }}
                  />
                )}
                {uploading ? (
                  <div className="relative z-10 flex items-center justify-center w-full">
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    <span className="flex items-center gap-2">
                      {uploadProgress < 40 ? (
                        <>
                          Uploading Dataset
                          <span className="text-xs opacity-75">({uploadProgress}%)</span>
                        </>
                      ) : (
                        <>
                          Training Model
                          <span className="text-xs opacity-75">({uploadProgress}%)</span>
                        </>
                      )}
                    </span>
                  </div>
                ) : (
                  <>
                    <Upload className="w-4 h-4 mr-2" />
                    Upload Dataset
                  </>
                )}
              </Button>
            </div>
          </div>

          {/* Datasets & Models Summary */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            {/* Datasets Card */}
            <div className="card border-2 border-border bg-bg-secondary rounded-xl p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-blue-500/20 border-2 border-blue-500/40 flex items-center justify-center">
                    <FileText className="w-5 h-5 text-blue-300" />
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-text-muted uppercase tracking-wide">Datasets</h3>
                    <p className="text-2xl font-bold text-text-primary">{datasets.length}</p>
                  </div>
                </div>
              </div>
              {datasets.length > 0 && (
                <div className="space-y-2">
                  {datasets.slice(0, 3).map((dataset: any) => (
                    <div key={dataset.id} className="text-sm text-text-muted bg-bg-primary px-3 py-2 rounded-lg border border-border">
                      <p className="font-medium text-text-primary truncate">{dataset.name}</p>
                      <p className="text-xs">
                        {dataset.row_count ? `${dataset.row_count.toLocaleString()} rows` : 'Processing...'}
                      </p>
                    </div>
                  ))}
                  {datasets.length > 3 && (
                    <p className="text-xs text-text-muted text-center">+{datasets.length - 3} more</p>
                  )}
                </div>
              )}
            </div>

            {/* Models Card */}
            <div className="card border-2 border-border bg-bg-secondary rounded-xl p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-purple-500/20 border-2 border-purple-500/40 flex items-center justify-center">
                    <BarChart3 className="w-5 h-5 text-purple-300" />
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-text-muted uppercase tracking-wide">Models</h3>
                    <p className="text-2xl font-bold text-text-primary">{models.length}</p>
                  </div>
                </div>
              </div>
              {models.length > 0 && (
                <div className="space-y-2">
                  {models.slice(0, 3).map((model: any) => (
                    <div key={model.id || model.model_id} className="text-sm text-text-muted bg-bg-primary px-3 py-2 rounded-lg border border-border">
                      <p className="font-medium text-text-primary">
                        Version {model.version || 'N/A'}
                        {model.metrics?.accuracy && (
                          <span className="ml-2 text-xs text-emerald-400">
                            ({((model.metrics.accuracy || 0) * 100).toFixed(1)}%)
                          </span>
                        )}
                      </p>
                      <p className="text-xs">
                        {model.created_at ? new Date(model.created_at).toLocaleDateString() : 'N/A'}
                      </p>
                    </div>
                  ))}
                  {models.length > 3 && (
                    <p className="text-xs text-text-muted text-center">+{models.length - 3} more</p>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* View Metrics Section */}
          <div className="card border-2 border-border bg-bg-secondary rounded-xl p-8">
            <div className="flex items-start gap-4 mb-6">
              <div className="w-12 h-12 rounded-xl bg-purple-500/20 border-2 border-purple-500/40 flex items-center justify-center shrink-0">
                <BarChart3 className="w-6 h-6 text-purple-300" strokeWidth={2.5} />
              </div>
              <div className="flex-1">
                <h2 className="text-lg font-bold text-text-primary mb-1">View Metrics</h2>
                <p className="text-sm text-text-muted">Analyze model performance and training metrics</p>
              </div>
            </div>

            <Button
              variant="outline"
              className="w-full border-2"
              onClick={() => navigate(`/monitoring/${projectId}`)}
            >
              <BarChart3 className="w-4 h-4 mr-2" />
              View Metrics Dashboard
            </Button>
          </div>
        </div>
      </div>
    </Layout>
  );
}
