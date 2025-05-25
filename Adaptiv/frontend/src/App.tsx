import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from 'antd';
import './App.css';

// Auth components
import Login from './components/auth/Login';
import Register from './components/auth/Register';
import AuthDebug from './components/auth/AuthDebug';

// Main components
import Dashboard from './components/dashboard/Dashboard';
import BusinessProfile from './components/profile/BusinessProfile';
import MainLayout from './components/layout/MainLayout';
import PriceRecommendations from './components/pricing/PriceRecommendations';
import CompetitorAnalysis from './components/competitor/CompetitorAnalysis';
import CompetitorDetail from './components/competitor/CompetitorDetail';
import ProductDetail from './components/products/ProductDetail';
import AgentDashboard from './components/agents/AgentDashboard';

// Integration components
import SquareCallback from './components/integrations/SquareCallback';
import SquareOrderTester from './components/integrations/SquareOrderTester';
import SquareIntegrationPage from './components/integrations/SquareIntegrationPage';

// Auth context
import { AuthProvider, useAuth } from './context/AuthContext';

const ProtectedRoute = ({ children }: { children: JSX.Element }) => {
  const { isAuthenticated, loading } = useAuth();
  
  // Don't redirect immediately while still loading authentication state
  if (loading) {
    // Show a simple loading indicator while checking auth
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <div>Loading...</div>
      </div>
    );
  }
  
  // Only redirect after loading is complete and we know user isn't authenticated
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return children;
};

function App() {
  return (
    <AuthProvider>
      <Layout style={{ minHeight: '100vh' }}>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/auth-debug" element={<AuthDebug />} />
          <Route path="/integrations/square/callback" element={<SquareCallback />} />
          <Route path="/" element={
            <ProtectedRoute>
              <MainLayout />
            </ProtectedRoute>
          }>
            <Route index element={<Dashboard />} />
            <Route path="profile" element={<BusinessProfile />} />
            <Route path="price-recommendations" element={<PriceRecommendations />} />
            <Route path="competitor-analysis" element={<CompetitorAnalysis />} />
            <Route path="competitor/:competitorId" element={<CompetitorDetail />} />
            <Route path="product/:productId" element={<ProductDetail />} />
            <Route path="agents" element={<AgentDashboard />} />
            <Route path="square-test" element={<SquareOrderTester />} />
            <Route path="integrations/square" element={<SquareIntegrationPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Layout>
    </AuthProvider>
  );
}

export default App;
