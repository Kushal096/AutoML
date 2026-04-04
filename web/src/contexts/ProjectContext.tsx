import { createContext, useContext, useState, ReactNode } from 'react';

interface ProjectContextType {
  selectedSystemId: string | null;
  setSelectedSystemId: (systemId: string | null) => void;
  clearSelectedSystem: () => void;
}

export const ProjectContext = createContext<ProjectContextType | undefined>(undefined);

export function ProjectProvider({ children }: { children: ReactNode }) {
  const [selectedSystemId, setSelectedSystemId] = useState<string | null>(null);

  const clearSelectedSystem = () => {
    setSelectedSystemId(null);
  };

  const value = {
    selectedSystemId,
    setSelectedSystemId,
    clearSelectedSystem,
  };

  return <ProjectContext.Provider value={value}>{children}</ProjectContext.Provider>;
}
