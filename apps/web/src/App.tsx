import { AuthProvider } from "@/features/auth/authStore";
import { useAuth } from "@/features/auth/useAuth";
import LoginPage from "@/features/auth/LoginPage";
import AgentWorkspace from "@/features/agent/AgentWorkspace";

function AppShell() {
  const { user, logout, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="app-shell">
        <div className="app-loading" role="status" aria-label="Loading">
          <span className="app-loading-spinner" />
          Restoring session...
        </div>
      </div>
    );
  }

  if (!user) {
    return <LoginPage />;
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <h1 className="app-title">HR Agent</h1>
        <span className="app-subtitle">Recruitment Workspace</span>
        <div className="app-header-right">
          <span className="app-user-label">
            {user.email}
            <span className="app-user-role"> ({user.role})</span>
          </span>
          <button
            type="button"
            className="app-logout-btn"
            onClick={logout}
          >
            Sign Out
          </button>
        </div>
      </header>
      <AgentWorkspace />
    </div>
  );
}

function App() {
  return (
    <AuthProvider>
      <AppShell />
    </AuthProvider>
  );
}

export default App;
