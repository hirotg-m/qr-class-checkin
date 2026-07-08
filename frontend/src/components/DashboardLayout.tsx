import { Link, Outlet } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export function DashboardLayout() {
  const { logout } = useAuth();

  return (
    <div>
      <nav className="dashboard-nav">
        <Link to="/dashboard" className="dashboard-nav-brand">
          ← ダッシュボード
        </Link>
        <button type="button" className="link-button" onClick={logout}>
          ログアウト
        </button>
      </nav>
      <Outlet />
    </div>
  );
}
