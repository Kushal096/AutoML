import { useNavigate, useLocation } from "react-router-dom";
import { Button } from "@/components/ui/button";
import useAuth from "@/hooks/useAuth";
import ChatAssistant from "@/components/ChatAssistant";
import {
  LayoutDashboard,
  FolderOpen,
  Activity,
  Database,
  Box,
  Settings,
  LogOut,
  Zap,
  User,
  Sparkles,
  Book,
} from "lucide-react";

interface LayoutProps {
  children: React.ReactNode;
}

export default function Layout({ children }: LayoutProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuth();

  const navItems = [
    {
      path: "/dashboard",
      label: "Dashboard",
      icon: LayoutDashboard,
    },
    {
      path: "/systems",
      label: "ML Systems",
      icon: Sparkles,
    },
    {
      path: "/projects",
      label: "My Projects",
      icon: FolderOpen,
    },
    {
      path: "/monitoring",
      label: "Monitoring",
      icon: Activity,
    },
    {
      path: "/docs",
      label: "Documentation",
      icon: Book,
    },
  ];

  const isActive = (path: string) => {
    if (path === "/projects" && location.pathname.startsWith("/projects")) {
      return true;
    }
    return location.pathname === path;
  };

  return (
    <div className="min-h-screen w-full bg-bg-primary">
      {/* Sidebar */}
      <aside className="fixed left-0 top-0 w-64 bg-bg-secondary border-r-2 border-border flex flex-col h-screen shadow-xl z-50">
        {/* Logo Section */}
        <div className="p-6 border-b-2 border-border shrink-0">
          <div className="flex items-center gap-3">
            <div className="flex-1 min-w-0">
              <h1 className="text-base font-bold text-text-primary m-0 truncate">
                GatiLabs
              </h1>
              <p className="text-xs text-text-muted m-0 truncate">
                ML Platform
              </p>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="p-4 space-y-2 overflow-y-auto flex flex-col items-stretch">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.path}
                onClick={() => navigate(item.path)}
                className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200 ${
                  isActive(item.path)
                    ? "text-[var(--color-primary)] bg-transparent pl-3"
                    : "text-text-muted hover:text-text-primary border-l-4 border-transparent"
                }`}
              >
                <Icon className="w-5 h-5 shrink-0" />
                <span className="font-medium text-sm">{item.label}</span>
              </button>
            );
          })}
        </nav>

        {/* Bottom Section - Pushed to bottom with mt-auto */}
        <div className="mt-auto border-t-2 border-border shrink-0">
          {/* User Section */}
          <div className="p-4 bg-bg-primary border-b-2 border-border">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-primary/20 border-2 border-primary flex items-center justify-center shrink-0">
                <User className="w-5 h-5 text-primary" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-text-primary truncate">
                  {user?.name || "User"}
                </p>
                <p className="text-xs text-text-muted truncate">
                  {user?.email || "user@example.com"}
                </p>
              </div>
            </div>
          </div>

          <div className="p-4 space-y-2 flex flex-col">
            <button
              onClick={() => navigate("/settings")}
              className="flex items-center gap-3 px-4 py-3 rounded-lg text-text-muted hover:bg-bg-primary hover:text-text-primary transition-all duration-200 border-2 border-transparent hover:border-border"
            >
              <Settings className="w-5 h-5 shrink-0" />
              <span className="font-medium text-sm">Settings</span>
            </button>
            <Button
              onClick={logout}
              variant="outline"
              className="w-full justify-start border-2 border-red-500/30 text-red-400 hover:bg-red-500/10 hover:border-red-500 hover:text-red-400"
            >
              <LogOut className="w-4 h-4 mr-2" />
              Logout
            </Button>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="ml-64 min-h-screen">{children}</main>
      
      {/* AI Chat Assistant - Available on all pages */}
      <ChatAssistant />
    </div>
  );
}
