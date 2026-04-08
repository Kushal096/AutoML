import { useState, useEffect, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { api, type System } from '@/lib/api';
import useAuth from '@/hooks/useAuth';
import useProject from '@/hooks/useProject';
import { ArrowLeft, Zap, CheckCircle2, TriangleAlert } from 'lucide-react';

interface FormData {
  name: string;
  system_id: string;
}

interface FormErrors {
  name?: string;
  system_id?: string;
  general?: string;
}

export default function CreateProject() {
  const navigate = useNavigate();
  const { accessToken } = useAuth();
  const { selectedSystemId, clearSelectedSystem } = useProject();
  const [formData, setFormData] = useState<FormData>({
    name: '',
    system_id: selectedSystemId || '',
  });
  const [errors, setErrors] = useState<FormErrors>({});
  const [isLoading, setIsLoading] = useState(false);
  const [systems, setSystems] = useState<System[]>([]);
  const [loadingSystems, setLoadingSystems] = useState(true);

  useEffect(() => {
    if (!accessToken) {
      return;
    }

    // Fetch available systems
    const fetchSystems = async () => {
      try {
        const systemsData = await api.getSystems(accessToken);
        setSystems(systemsData);
      } catch (error) {
        setErrors({
          general: error instanceof Error ? error.message : 'Failed to load systems',
        });
      } finally {
        setLoadingSystems(false);
      }
    };

    fetchSystems();
  }, [accessToken]);

  // Clear selected system when component unmounts
  useEffect(() => {
    return () => {
      clearSelectedSystem();
    };
  }, [clearSelectedSystem]);

  const validateForm = (): boolean => {
    const newErrors: FormErrors = {};

    if (!formData.name.trim()) {
      newErrors.name = 'Project name is required';
    } else if (formData.name.length < 3) {
      newErrors.name = 'Project name must be at least 3 characters';
    }

    if (!formData.system_id) {
      newErrors.system_id = 'Please select a system';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }

    setIsLoading(true);
    setErrors({});

    try {
      const apiKey = localStorage.getItem('apiKey');
      if (!apiKey) {
        return;
      }
      if (!accessToken) {
        return;
      }

      // await api.createProject(accessToken,{

      // }
      //   );
      const result = await api.createProject(accessToken, {
        name: formData.name,
        system_id: formData.system_id,
      });
      
      console.log('Project created:', result);
      // Navigate to projects list
      navigate('/projects');
      
    } catch (error) {
      setErrors({
        general: error instanceof Error ? error.message : 'Failed to create project',
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value,
    }));
    // Clear error for this field when user starts typing
    if (errors[name as keyof FormErrors]) {
      setErrors(prev => ({
        ...prev,
        [name]: undefined,
      }));
    }
  };

  const handleBack = () => {
    navigate('/dashboard');
  };

  return (
    <div className="min-h-screen w-full bg-bg-primary">
      {/* Header */}
      <div className="border-b-2 border-border bg-bg-secondary">
        <div className="max-w-[1560px] mx-auto px-8 py-6">
          <Button
            onClick={handleBack}
            variant="ghost"
            className="mb-4 -ml-2 text-text-muted hover:text-text-primary"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Dashboard
          </Button>
          <div>
            <h1 className="text-3xl font-bold text-text-primary mb-2">Create New Project</h1>
            <p className="text-sm text-text-muted">
              Configure your ML project and select a system to get started
            </p>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-[1560px] mx-auto px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Form Section */}
          <div className="lg:col-span-2">
            <div className="card border-2 border-border bg-bg-secondary p-8">
              <form onSubmit={handleSubmit}>
                {errors.general && (
                  <div className="bg-red-500/10 border-2 border-[var(--color-error)] rounded-lg p-4 mb-6 text-[var(--color-error)] text-sm flex items-start gap-3">
                    {/* <span className="text-lg">Tria</span> */}
                    <TriangleAlert className="w-4 h-4 mt-0.5" />
                    <span>{errors.general}</span>
                  </div>
                )}

                {/* Project Name */}
                <div className="mb-6">
                  <Label htmlFor="name" className="text-sm font-semibold text-text-primary mb-2 block">
                    Project Name *
                  </Label>
                  <Input
                    type="text"
                    id="name"
                    name="name"
                    value={formData.name}
                    onChange={handleChange}
                    placeholder="e.g., Customer Recommendation Engine"
                    disabled={isLoading}
                    className="w-full text-base"
                  />
                  {errors.name && (
                    <div className="form-error mt-2 text-xs">{errors.name}</div>
                  )}
                  <p className="text-xs text-text-muted mt-2">
                    Choose a clear, descriptive name for easy identification
                  </p>
                </div>

                {/* System Selection */}
                <div className="mb-8">
                  <Label className="text-sm font-semibold text-text-primary mb-3 block">
                    Select ML System *
                  </Label>
                  {loadingSystems ? (
                    <div className="space-y-3">
                      {[1, 2, 3].map((i) => (
                        <div
                          key={i}
                          className="h-24 bg-bg-elevated rounded-lg border-2 border-border animate-pulse"
                        />
                      ))}
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {systems.map((system) => (
                        <div
                          key={system.id}
                          onClick={() => {
                            setFormData((prev) => ({ ...prev, system_id: system.id }));
                            setErrors((prev) => ({ ...prev, system_id: undefined }));
                          }}
                          className={`relative p-5 rounded-lg border-2 cursor-pointer transition-all duration-200 group ${
                            formData.system_id === system.id
                              ? 'border-[var(--color-primary)] bg-[var(--color-primary)]/5 shadow-lg shadow-[var(--color-primary)]/10'
                              : 'border-border bg-bg-elevated hover:border-primary/50 hover:bg-bg-elevated'
                          }`}
                        >
                          <div className="flex items-start gap-4">
                            <div
                              className={`w-12 h-12 rounded-xl flex items-center justify-center shrink-0 transition-all ${
                                formData.system_id === system.id
                                  ? 'bg-[var(--color-primary)] text-white'
                                  : 'bg-zinc-800 text-zinc-400 group-hover:bg-zinc-700'
                              }`}
                            >
                              <Zap className="w-6 h-6" strokeWidth={2.5} />
                            </div>
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center justify-between mb-2">
                                <h4 className="text-base font-bold text-text-primary">
                                  {system.name}
                                </h4>
                                {formData.system_id === system.id && (
                                  <CheckCircle2 className="w-5 h-5 text-[var(--color-primary)]" strokeWidth={2.5} />
                                )}
                              </div>
                              <p className="text-sm text-text-muted leading-relaxed">
                                {system.description}
                              </p>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                  {errors.system_id && (
                    <div className="form-error mt-2 text-xs">{errors.system_id}</div>
                  )}
                </div>

                {/* Action Buttons */}
                <div className="flex gap-3 pt-6 border-t-2 border-border">
                  <Button
                    type="submit"
                    disabled={isLoading || loadingSystems}
                    className="flex-1 bg-[var(--color-primary)] hover:bg-[var(--color-primary-hover)] text-white font-semibold py-6 text-base"
                  >
                    {isLoading ? 'Creating Project...' : 'Create Project'}
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={handleBack}
                    disabled={isLoading}
                    className="px-8 py-6 border-2"
                  >
                    Cancel
                  </Button>
                </div>
              </form>
            </div>
          </div>

          {/* Info Sidebar */}
          <div className="lg:col-span-1">
            <div className="card border-2 border-border bg-bg-secondary p-6 sticky top-8">
              <h3 className="text-lg font-bold text-text-primary mb-4">Quick Guide</h3>
              <div className="space-y-4">
                <div className="flex gap-3">
                  <div className="w-8 h-8 rounded-full bg-[var(--color-primary)]/20 border-2 border-[var(--color-primary)] flex items-center justify-center shrink-0 text-[var(--color-primary)] font-bold text-sm">
                    1
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-text-primary mb-1">Name Your Project</p>
                    <p className="text-xs text-text-muted leading-relaxed">
                      Choose a descriptive name that reflects your project's purpose
                    </p>
                  </div>
                </div>
                <div className="flex gap-3">
                  <div className="w-8 h-8 rounded-full bg-[var(--color-primary)]/20 border-2 border-[var(--color-primary)] flex items-center justify-center shrink-0 text-[var(--color-primary)] font-bold text-sm">
                    2
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-text-primary mb-1">Select ML System</p>
                    <p className="text-xs text-text-muted leading-relaxed">
                      Pick the machine learning system that best fits your use case
                    </p>
                  </div>
                </div>
                <div className="flex gap-3">
                  <div className="w-8 h-8 rounded-full bg-[var(--color-primary)]/20 border-2 border-[var(--color-primary)] flex items-center justify-center shrink-0 text-[var(--color-primary)] font-bold text-sm">
                    3
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-text-primary mb-1">Create & Deploy</p>
                    <p className="text-xs text-text-muted leading-relaxed">
                      Once created, you can upload data and start training your models
                    </p>
                  </div>
                </div>
              </div>

              <div className="mt-6 pt-6 border-t-2 border-border">
                <p className="text-xs text-text-muted leading-relaxed">
                  💡 <strong className="text-text-primary">Tip:</strong> You can manage and configure your project settings after creation from the Projects dashboard.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
