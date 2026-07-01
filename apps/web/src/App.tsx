import { AuthProvider } from "@/features/auth/authStore";
import { useAuth } from "@/features/auth/useAuth";
import LoginPage from "@/features/auth/LoginPage";
import AgentWorkspace from "@/features/agent/AgentWorkspace";

function AppShell() {
  const { user, logout, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="app-shell">
        <div className="app-loading" role="status" aria-label="加载中">
          <span className="app-loading-spinner" />
          正在恢复会话...
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
        <h1 className="app-title">HR 智能助手</h1>
        <span className="app-subtitle">招聘工作台</span>
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
            退出登录
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
