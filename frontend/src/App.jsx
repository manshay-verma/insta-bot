import React, { Suspense, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore } from './store/useAuthStore';
import { useSocketStore } from './store/useSocketStore';
import { Loader2 } from 'lucide-react';
import NotificationCenter from './components/NotificationCenter';
import './index.css';

// Lazy load pages for optimization
const Login = React.lazy(() => import('./pages/Login'));
const Register = React.lazy(() => import('./pages/Register'));
const Dashboard = React.lazy(() => import('./pages/Dashboard'));
const AccountList = React.lazy(() => import('./pages/AccountList'));
const BotControls = React.lazy(() => import('./pages/BotControls'));
const DownloadCenter = React.lazy(() => import('./pages/DownloadCenter'));
const Settings = React.lazy(() => import('./pages/Settings'));
const Analytics = React.lazy(() => import('./pages/Analytics'));
const Help = React.lazy(() => import('./pages/Help'));
const ExportCenter = React.lazy(() => import('./pages/ExportCenter'));
const RateLimits = React.lazy(() => import('./pages/RateLimits'));
const MediaGallery = React.lazy(() => import('./pages/MediaGallery'));

// Loading Screen
const LoadingScreen = () => (
  <div style={{ 
    minHeight: '100vh', 
    display: 'flex', 
    alignItems: 'center', 
    justifyContent: 'center',
    backgroundColor: 'hsl(var(--background))' 
  }}>
    <Loader2 className="animate-spin" size={40} color="hsl(var(--primary))" />
  </div>
);

// Protected Route Component
const ProtectedRoute = ({ children }) => {
  const { isAuthenticated } = useAuthStore();
  return isAuthenticated ? children : <Navigate to="/login" />;
};

const App = () => {
  const { isAuthenticated } = useAuthStore();
  const { connect, disconnect } = useSocketStore();

  useEffect(() => {
    if (isAuthenticated) {
      // Connect to websocket when authenticated
      const wsUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws/updates/';
      connect(wsUrl);
    } else {
      disconnect();
    }

    return () => disconnect();
  }, [isAuthenticated]);

  return (
    <BrowserRouter>
      <Suspense fallback={<LoadingScreen />}>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          
          <Route 
            path="/" 
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            } 
          />
          
          <Route 
            path="/accounts" 
            element={
              <ProtectedRoute>
                <AccountList />
              </ProtectedRoute>
            } 
          />
          
          <Route 
            path="/bot" 
            element={
              <ProtectedRoute>
                <BotControls />
              </ProtectedRoute>
            } 
          />
          
          <Route 
            path="/downloads" 
            element={
              <ProtectedRoute>
                <DownloadCenter />
              </ProtectedRoute>
            } 
          />

          <Route 
            path="/gallery" 
            element={
              <ProtectedRoute>
                <MediaGallery />
              </ProtectedRoute>
            } 
          />
          
          <Route 
            path="/analytics" 
            element={
              <ProtectedRoute>
                <Analytics />
              </ProtectedRoute>
            } 
          />

          <Route 
            path="/rate-limits" 
            element={
              <ProtectedRoute>
                <RateLimits />
              </ProtectedRoute>
            } 
          />
          
          <Route 
            path="/settings" 
            element={
              <ProtectedRoute>
                <Settings />
              </ProtectedRoute>
            } 
          />
          
          <Route 
            path="/export" 
            element={
              <ProtectedRoute>
                <ExportCenter />
              </ProtectedRoute>
            } 
          />
          
          <Route 
            path="/help" 
            element={ <Help /> } 
          />
          
          {/* Catch-all route */}
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </Suspense>
      <NotificationCenter />
    </BrowserRouter>
  );
};

export default App;
