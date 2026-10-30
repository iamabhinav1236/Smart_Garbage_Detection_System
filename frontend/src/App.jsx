import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { NotificationProvider } from './context/NotificationContext';
import { wsService } from './services/websocket';

// Components
import Navbar from './components/Navbar';
import Sidebar from './components/Sidebar';

// Pages
import WelcomePage from './pages/WelcomePage';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import BinsPage from './pages/BinsPage';
import AddBinPage from './pages/AddBinPage';
import EditBinPage from './pages/EditBinPage';
import BinDetailsPage from './pages/BinDetailsPage';
import AnalyticsPage from './pages/AnalyticsPage';
import AlertsPage from './pages/AlertsPage';
import CaretakerSettingsPage from './pages/CaretakerSettingsPage';
import SystemSettingsPage from './pages/SystemSettingsPage';

// Import all styles
import './styles/global.css';
import './styles/navbar.css';
import './styles/sidebar.css';
import './styles/dashboard.css';
import './styles/cards.css';
import './styles/camera.css';
import './styles/forms.css';
import './styles/tables.css';
import './styles/roi.css';
import './styles/responsive.css';

// Protected Layout
const AppLayout = ({ children }) => {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  useEffect(() => {
    // Connect WebSocket when inside app
    wsService.connect();
    return () => {
      wsService.disconnect();
    };
  }, []);

  return (
    <div className="app-layout">
      <Sidebar isCollapsed={sidebarCollapsed} />
      <div className={`main-content ${sidebarCollapsed ? 'sidebar-collapsed' : ''}`}>
        <Navbar
          onToggleSidebar={() => setSidebarCollapsed(!sidebarCollapsed)}
          isSidebarCollapsed={sidebarCollapsed}
        />
        <main>{children}</main>
      </div>
    </div>
  );
};

const ProtectedRoute = ({ children }) => {
  const { isAuthenticated } = useAuth();
  const location = useLocation();
  if (!isAuthenticated) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  return <AppLayout>{children}</AppLayout>;
};

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <NotificationProvider>
          <Routes>
            {/* Public Entry Pages */}
            <Route path="/" element={<WelcomePage />} />
            <Route path="/login" element={<LoginPage />} />

            {/* Portal Pages */}
            <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
            <Route path="/bins" element={<ProtectedRoute><BinsPage /></ProtectedRoute>} />
            <Route path="/bins/new" element={<ProtectedRoute><AddBinPage /></ProtectedRoute>} />
            <Route path="/bins/:id/edit" element={<ProtectedRoute><EditBinPage /></ProtectedRoute>} />
            <Route path="/bins/:id" element={<ProtectedRoute><BinDetailsPage /></ProtectedRoute>} />
            <Route path="/analytics" element={<ProtectedRoute><AnalyticsPage /></ProtectedRoute>} />
            <Route path="/alerts" element={<ProtectedRoute><AlertsPage /></ProtectedRoute>} />
            <Route path="/settings/email" element={<ProtectedRoute><CaretakerSettingsPage /></ProtectedRoute>} />
            <Route path="/settings/system" element={<ProtectedRoute><SystemSettingsPage /></ProtectedRoute>} />

            {/* Fallback */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </NotificationProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
