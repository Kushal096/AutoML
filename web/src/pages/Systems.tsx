import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Layout from '@/components/Layout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import useAuth from '@/hooks/useAuth';
// import useProject from '@/hooks/useProject';
import { api, type System } from '@/lib/api';
import { AlertCircle, Brain, TrendingUp, Users, ShoppingCart, ArrowRight, FolderPlus } from 'lucide-react';

export default function Systems() {
  const navigate = useNavigate();
  const { user, logout, accessToken } = useAuth();
  // const { setSelectedSystemId } = useProject();
  const [systems, setSystems] = useState<System[]>([]);
  const [loadingSystems, setLoadingSystems] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedSystem, setSelectedSystem] = useState<System | null>(null);
  const [projectName, setProjectName] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!accessToken) {
      return;
    }

    const fetchSystems = async () => {
      try {
        const systemsData = await api.getSystems(accessToken);
        setSystems(systemsData);
      } catch (error) {
        setError(error instanceof Error ? error.message : 'Failed to load systems');
      } finally {
        setLoadingSystems(false);
      }
    };

    fetchSystems();
  }, [accessToken]);

  const handleLogout = () => {
    logout();
  };

  const handleCreateProject = (system: System) => {
    setSelectedSystem(system);
    setProjectName('');
    setError(null);
    setShowCreateModal(true);
  };

  const handleSubmitProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!accessToken || !selectedSystem) return;

    setSubmitting(true);
    setError(null);

    try {
      const newProject = await api.createProject(accessToken, {
        name: projectName,
      });
      setShowCreateModal(false);
      setProjectName('');
      setSelectedSystem(null);
      // Navigate to the new project details
      navigate(`/projects/${newProject.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create project');
    } finally {
      setSubmitting(false);
    }
  };

  const handleCloseModal = () => {
    setShowCreateModal(false);
    setProjectName('');
    setSelectedSystem(null);
    setError(null);
  };

  const getSystemIcon = (systemName: string) => {
    const name = systemName.toLowerCase();
    if (name.includes('recommendation')) return ShoppingCart;
    if (name.includes('churn')) return Users;
    if (name.includes('prediction')) return TrendingUp;
    return Brain;
  };

  const getSystemImage = (systemName: string) => {
    const name = systemName.toLowerCase();
    if (name.includes('recommendation')) {
      return 'https://images.unsplash.com/photo-1556742049-0cfed4f6a45d?w=400&h=300&fit=crop';
    }
    if (name.includes('churn')) {
      return 'https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=400&h=300&fit=crop';
    }
    return 'https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=400&h=300&fit=crop';
  };

  return (
    <Layout>
      <div className="p-8">
        {/* Page Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-text-primary mb-2">Available ML Systems</h1>
          <p className="text-text-muted">
            Select a system to create a new project and start training models
          </p>
        </div>

        {error && (
          <div className="bg-red-500/10 border-2 border-red-500 rounded-lg p-4 mb-6 text-red-400 text-sm shadow-lg shadow-red-500/20">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4" />
              {error}
            </div>
          </div>
        )}

        {loadingSystems ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div key={i} className="card h-80 bg-bg-secondary border-2 border-border animate-pulse rounded-xl"></div>
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {systems.map((system) => {
              const SystemIcon = getSystemIcon(system.name);
              return (
                <div
                  key={system.id}
                  className="group card transition-all rounded-xl duration-300 border-2 border-border hover:border-primary flex flex-col overflow-hidden bg-bg-secondary hover:-translate-y-1 shadow-lg shadow-black/20 hover:shadow-xl hover:shadow-primary/10"
                >
                  {/* Hero Image - Edge to Edge */}
                  <div className="relative w-full h-44 overflow-hidden">
                    <img 
                      src={getSystemImage(system.name)} 
                      alt={system.name}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/30 to-transparent"></div>
                    
                    {/* Floating Icon Badge */}
                    <div className="absolute top-3 right-3 w-10 h-10 rounded-lg bg-emerald-500/20 border border-emerald-500/40 backdrop-blur-sm flex items-center justify-center">
                      <SystemIcon className="w-5 h-5 text-emerald-300" strokeWidth={2.5} />
                    </div>

                    {/* System Name Overlay */}
                    <div className="absolute bottom-3 left-3 right-3">
                      <h3 className="text-base font-bold text-white drop-shadow-lg">
                        {system.name}
                      </h3>
                    </div>
                  </div>
                  
                  <div className="p-5 flex-1 flex flex-col">
                    <p className="text-xs text-text-muted leading-relaxed mb-4 line-clamp-2">
                      {system.description}
                    </p>
                    
                    {/* Features - Compact Display */}
                    <div className="space-y-2.5 mb-5 flex-1">
                      {system.default_pipeline?.algorithms && system.default_pipeline.algorithms.length > 0 && (
                        <div>
                          <div className="text-[10px] font-bold text-text-muted mb-1.5 uppercase tracking-wide">Algorithms</div>
                          <div className="flex flex-wrap gap-1">
                            {system.default_pipeline.algorithms.slice(0, 2).map((algo, idx) => (
                              <span
                                key={idx}
                                className="px-2 py-0.5 bg-blue-500/20 text-blue-300 text-[10px] font-semibold rounded border border-blue-500/40"
                              >
                                {algo.replace(/_/g, ' ')}
                              </span>
                            ))}
                            {system.default_pipeline.algorithms.length > 2 && (
                              <span className="px-2 py-0.5 bg-border text-text-muted text-[10px] font-semibold rounded">
                                +{system.default_pipeline.algorithms.length - 2}
                              </span>
                            )}
                          </div>
                        </div>
                      )}
                      
                      {system.default_pipeline?.metrics && system.default_pipeline.metrics.length > 0 && (
                        <div>
                          <div className="text-[10px] font-bold text-text-muted mb-1.5 uppercase tracking-wide">Metrics</div>
                          <div className="flex flex-wrap gap-1">
                            {system.default_pipeline.metrics.slice(0, 3).map((metric, idx) => (
                              <span
                                key={idx}
                                className="px-2 py-0.5 bg-emerald-500/20 text-emerald-300 text-[10px] font-semibold rounded border border-emerald-500/40"
                              >
                                {metric.toUpperCase()}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                    
                    {/* CTA Button */}
                    <Button
                      onClick={() => handleCreateProject(system)}
                      className="w-full text-xs font-bold bg-primary text-white border-2 border-primary transition-all duration-300 group/btn h-9"
                      size="sm"
                    >
                      <span className="flex items-center justify-center gap-1.5">
                        Start Project
                        <ArrowRight className="w-3.5 h-3.5 group-hover/btn:translate-x-1 transition-transform" strokeWidth={2.5} />
                      </span>
                    </Button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Create Project Modal */}
      {showCreateModal && selectedSystem && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-bg-secondary border-2 border-border rounded-xl p-8 w-full max-w-md shadow-2xl">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-lg bg-primary/20 border-2 border-primary/40 flex items-center justify-center">
                <FolderPlus className="w-5 h-5 text-primary" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-text-primary">Create New Project</h2>
                <p className="text-xs text-text-muted mt-1">System: {selectedSystem.name}</p>
              </div>
            </div>
            <form onSubmit={handleSubmitProject} className="space-y-4">
              <div className="flex flex-col gap-2">
                <Label htmlFor="name">Project Name</Label>
                <Input
                  id="name"
                  type="text"
                  value={projectName}
                  onChange={(e) => setProjectName(e.target.value)}
                  placeholder="Enter project name"
                  required
                  autoFocus
                />
              </div>
              {error && (
                <div className="bg-red-500/10 border-2 border-red-500 rounded-lg p-3 text-red-400 text-sm">
                  <div className="flex items-center gap-2">
                    <AlertCircle className="w-4 h-4" />
                    {error}
                  </div>
                </div>
              )}
              <div className="flex gap-3 pt-4">
                <Button
                  type="button"
                  onClick={handleCloseModal}
                  variant="outline"
                  className="flex-1 border-2"
                  disabled={submitting}
                >
                  Cancel
                </Button>
                <Button 
                  type="submit" 
                  className="flex-1 border-2 border-primary" 
                  disabled={submitting}
                >
                  {submitting ? 'Creating...' : 'Create Project'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </Layout>
  );
}
