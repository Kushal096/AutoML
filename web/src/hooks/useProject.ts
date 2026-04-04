import { ProjectContext } from "@/contexts/ProjectContext";
import { useContext } from "react";

const useProject = () => {
  const context = useContext(ProjectContext);
  if (context === undefined) {
    throw new Error("useProject must be used within a ProjectProvider");
  }
  return context;
};

export default useProject;
