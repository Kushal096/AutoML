import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Layout from '@/components/Layout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import useAuth from '@/hooks/useAuth';
import useProject from '@/hooks/useProject';
import { api, type ProjectResponse, type System } from '@/lib/api';
import { Plus, FolderOpen, Trash2, AlertCircle, FolderPlus } from 'lucide-react';

export default function Projects() {
  const navigate = useNavigate();
  const { accessToken, logout } = useAuth();
  const { selectedSystemId, clearSelectedSystem } = useProject();
  const [projects, setProjects] = useState<ProjectResponse[]>([]);
  const [systems, setSystems] = useState<System[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingProject, setEditingProject] = useState<ProjectResponse | null>(null);
  const [formData, setFormData] = useState({
    name: '',
  });
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (selectedSystemId && !showCreateModal) {
      setShowCreateModal(true);
    }
  }, [selectedSystemId]);

  useEffect(() => {
    if (!accessToken) return;

    const fetchData = async () => {
      try {
        const [projectsData, systemsData] = await Promise.all([
          api.getProjects(accessToken),
          api.getSystems(accessToken),
        ]);
        // Filter out deleted projects
        const activeProjects = projectsData.filter(p => p.status !== 'deleted');
        setProjects(activeProjects);
        setSystems(systemsData);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load data');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [accessToken]);

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!accessToken) return;

    setSubmitting(true);
    setError(null);

    try {
      const newProject = await api.createProject(accessToken, formData);
      // Only add if not deleted (shouldn't be, but just in case)
      if (newProject.status !== 'deleted') {
        setProjects([newProject, ...projects]);
      }
      setShowCreateModal(false);
      setFormData({ name: '' });
      clearSelectedSystem();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create project');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteProject = async (projectId: string) => {
    if (!confirm('Are you sure you want to delete this project?')) return;
    if (!accessToken) return;

    try {
      await api.deleteProject(accessToken, projectId);
      // Remove the project from the list (it will be marked as deleted)
      setProjects(projects.filter(p => p.id !== projectId));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete project');
    }
  };

  const handleCloseModal = () => {
    setShowCreateModal(false);
    setEditingProject(null);
    setFormData({ name: '' });
    clearSelectedSystem();
  };

  const getSystemName = (systemId: string) => {
    return systems.find(s => s.id === systemId)?.name || 'Unknown System';
  };

  return (
    <Layout>
      <div className="p-8">
        {/* Page Header */}
        <div className="flex justify-between items-start mb-8">
          <div>
            <h1 className="text-3xl font-bold text-text-primary mb-2">My Projects</h1>
            <p className="text-text-muted flex items-center gap-2">
              <span className="px-3 py-1 bg-primary/20 text-primary border-2 border-primary/40 rounded-lg font-semibold text-sm shadow-sm">
                {projects.length} Projects
              </span>
            </p>
          </div>
          <Button onClick={() => setShowCreateModal(true)} className="shadow-lg shadow-primary/30 border-2 border-primary">
            <Plus className="w-4 h-4 mr-2" />
            Create New Project
          </Button>
        </div>

        {error && (
          <div className="bg-red-500/10 border-2 border-red-500 rounded-lg p-4 mb-6 text-red-400 text-sm shadow-lg shadow-red-500/20">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4" />
              {error}
            </div>
          </div>
        )}

        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {[1, 2, 3].map((i) => (
              <div key={i} className="card h-72 bg-bg-secondary border-2 border-border animate-pulse rounded-xl"></div>
            ))}
          </div>
        ) : projects.length === 0 ? (
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
                d="M9 13h6m-3-3v6m-9 1V7a2 2 0 012-2h6l2 2h6a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z"
              />
            </svg>
            <h3 className="mt-2 text-sm font-semibold text-text-primary">No projects</h3>
            <p className="mt-1 text-sm text-text-muted">
              Get started by creating a new project.
            </p>
            <div className="mt-6">
              <Button onClick={() => setShowCreateModal(true)}>
                Create Project
              </Button>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {projects.map((project) => (
              <div
                key={project.id}
                className="group card border-2 border-border hover:border-primary transition-all duration-200 overflow-hidden bg-bg-secondary hover:-translate-y-1 rounded-xl shadow-lg shadow-black/20 hover:shadow-xl hover:shadow-primary/10"
              >
                {/* Header */}
                <div className="relative bg-bg-primary p-6 border-b-2 border-border">
                  <div className="flex justify-between items-start">
                    <div className="flex items-center gap-3 flex-1 min-w-0">
                      <div className="w-10 h-10 rounded-lg bg-emerald-500/30 border border-emerald-500/50 flex items-center justify-center shrink-0">
                        <FolderOpen className="w-5 h-5 text-emerald-300" strokeWidth={2.5} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <h3 className="text-sm font-bold text-text-primary truncate group-hover:text-emerald-300 transition-colors">
                          {project.name}
                        </h3>
                        <p className="text-xs text-text-muted">Project</p>
                      </div>
                    </div>
                    <button
                      onClick={() => handleDeleteProject(project.id)}
                      className="p-1.5 hover:bg-red-500/20 rounded-lg transition-colors border border-transparent hover:border-red-500/50 shrink-0"
                      title="Delete project"
                    >
                      <Trash2 className="w-4 h-4 text-red-400" />
                    </button>
                  </div>
                </div>

                {/* Content */}
                <div className="p-6">
                  <div className="mb-5">
                    <div className="text-[10px] font-bold text-text-muted mb-1.5 uppercase tracking-wide">System</div>
                    <span className="inline-block px-2 py-1 bg-blue-500/20 text-blue-300 text-xs font-semibold rounded border border-blue-500/40">
                      {getSystemName(project.system_id)}
                    </span>
                  </div>

                  {project.status && (
                    <div className="mb-5">
                      <div className="text-[10px] font-bold text-text-muted mb-1.5 uppercase tracking-wide">Status</div>
                      <span className={`inline-block px-2 py-1 text-xs font-semibold rounded border ${
                        project.status === 'active' 
                          ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                          : 'bg-zinc-500/20 text-zinc-300 border-zinc-500/40'
                      }`}>
                        {project.status}
                      </span>
                    </div>
                  )}

                  <div className="mb-6">
                    <div className="text-[10px] font-bold text-text-muted mb-1.5 uppercase tracking-wide">Created</div>
                    <p className="text-xs text-text-secondary">
                      {new Date(project.created_at).toLocaleDateString('en-US', { 
                        month: 'short', 
                        day: 'numeric', 
                        year: 'numeric' 
                      })}
                    </p>
                  </div>

                  {/* Actions */}
                  <div className="flex gap-2">
                    <Button
                      onClick={() => navigate(`/projects/${project.id}`)}
                      className="flex-1 text-xs font-bold bg-primary text-white border-2 border-primary h-8"
                      size="sm"
                    >
                      View Details
                    </Button>
                    <Button
                      onClick={() => {
                        setEditingProject(project);
                        setFormData({ name: project.name });
                        setShowCreateModal(true);
                      }}
                      variant="outline"
                      size="sm"
                      className="text-xs border-2 h-8"
                    >
                      Edit
                    </Button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Create/Edit Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-bg-secondary border-2 border-border rounded-2xl p-10 w-full max-w-md shadow-2xl">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-lg bg-emerald-500/20 border-2 border-emerald-500/40 flex items-center justify-center">
                <FolderPlus className="w-5 h-5 text-emerald-300" />
              </div>
              <h2 className="text-xl font-bold text-text-primary">
                {editingProject ? 'Edit Project' : 'Create New Project'}
              </h2>
            </div>
            <form onSubmit={handleCreateProject} className="space-y-4">
              <div>
                <Label className='pb-2' htmlFor="name">Project Name</Label>
                <Input
                  id="name"
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
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
                <Button type="submit" className="flex-1 shadow-lg shadow-primary/30 border-2 border-primary" disabled={submitting}>
                  {submitting ? 'Creating...' : editingProject ? 'Update' : 'Create'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </Layout>
  );
}