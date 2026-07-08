import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./auth/AuthContext";
import { RequireAuth } from "./auth/RequireAuth";
import { DashboardLayout } from "./components/DashboardLayout";
import { LoginPage } from "./pages/auth/LoginPage";
import { ClassListPage } from "./pages/dashboard/ClassListPage";
import { ParticipantsPage } from "./pages/dashboard/ParticipantsPage";
import { PinPage } from "./pages/dashboard/PinPage";
import { QrCodePage } from "./pages/dashboard/QrCodePage";
import { SchedulePage } from "./pages/dashboard/SchedulePage";
import { SessionDetailPage } from "./pages/dashboard/SessionDetailPage";
import { StatsPage } from "./pages/dashboard/StatsPage";
import { CheckinWizard } from "./pages/public/CheckinWizard";

export function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/c/:classId" element={<CheckinWizard />} />
          <Route path="/login" element={<LoginPage />} />

          <Route element={<RequireAuth />}>
            <Route element={<DashboardLayout />}>
              <Route path="/dashboard" element={<ClassListPage />} />
              <Route path="/dashboard/classes/:classId/schedule" element={<SchedulePage />} />
              <Route path="/dashboard/classes/:classId/sessions/:date" element={<SessionDetailPage />} />
              <Route path="/dashboard/classes/:classId/stats" element={<StatsPage />} />
              <Route path="/dashboard/classes/:classId/participants" element={<ParticipantsPage />} />
              <Route path="/dashboard/classes/:classId/pin" element={<PinPage />} />
              <Route path="/dashboard/classes/:classId/qr" element={<QrCodePage />} />
            </Route>
          </Route>

          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

function NotFound() {
  return (
    <div className="page centered">
      <h1>ページが見つかりません</h1>
    </div>
  );
}
