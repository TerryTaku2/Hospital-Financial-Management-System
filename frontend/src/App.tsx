import type { ReactNode } from 'react';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import Layout from './components/Layout';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import PatientsPage from './pages/PatientsPage';
import OPDPage from './pages/OPDPage';
import IPDPage from './pages/IPDPage';
import AppointmentsPage from './pages/AppointmentsPage';
import SetupPage from './pages/SetupPage';

function Protected({ children }: { children: ReactNode }) {
  return (
    <ProtectedRoute>
      <Layout>{children}</Layout>
    </ProtectedRoute>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/"
            element={
              <Protected>
                <DashboardPage />
              </Protected>
            }
          />
          <Route
            path="/patients"
            element={
              <Protected>
                <PatientsPage />
              </Protected>
            }
          />
          <Route
            path="/opd"
            element={
              <Protected>
                <OPDPage />
              </Protected>
            }
          />
          <Route
            path="/ipd"
            element={
              <Protected>
                <IPDPage />
              </Protected>
            }
          />
          <Route
            path="/appointments"
            element={
              <Protected>
                <AppointmentsPage />
              </Protected>
            }
          />
          <Route
            path="/setup"
            element={
              <Protected>
                <SetupPage />
              </Protected>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
