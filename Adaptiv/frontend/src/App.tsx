import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from 'antd';
import './App.css';

// Auth components
import Login from './components/auth/Login';
import Register from './components/auth/Register';

// Main components
import Dashboard from './components/dashboard/Dashboard';
import BusinessProfile from './components/profile/BusinessProfile';
import MainLayout from './components/layout/MainLayout';
import PriceRecommendations from './components/menu/PriceRecommendations';
import CompetitorDetail from './components/competitor/CompetitorDetail';
import Competitors from './components/competitor/Competitors';
import ProductDetail from './components/products/ProductDetail';
import DynamicPricingAgents from './components/agents/DynamicPricingAgents';
import Costs from './components/costs/Costs';

// Subscription components
import PricingPlans from './components/subscriptions/PricingPlans';
import SubscriptionSuccess from './components/subscriptions/SubscriptionSuccess';
import SubscriptionCancel from './components/subscriptions/SubscriptionCancel';
import SubscriptionManagement from './components/subscriptions/SubscriptionManagement';


// Integration components
import SquareCallback from './components/integrations/Square/SquareCallback';
import SquareOrderTester from './components/integrations/Square/SquareOrderTester';
import SquareIntegrationPage from './components/integrations/Square/SquareIntegrationPage';

// Contexts
import { AuthProvider, useAuth } from './context/AuthContext';
import { SubscriptionProvider } from './contexts/SubscriptionContext';

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
      <SubscriptionProvider>
        <Layout style={{ minHeight: '100vh' }}>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/integrations/square/callback" element={<SquareCallback />} />
            
            {/* Subscription Routes - accessible without protected layout */}
            <Route path="/subscription-success" element={
              <ProtectedRoute>
                <SubscriptionSuccess />
              </ProtectedRoute>
            } />
            <Route path="/subscription-cancel" element={
              <ProtectedRoute>
                <SubscriptionCancel />
              </ProtectedRoute>
            } />
            
            <Route path="/" element={
              <ProtectedRoute>
                <MainLayout />
              </ProtectedRoute>
            }>
              <Route index element={<Dashboard />} />
              <Route path="profile" element={<BusinessProfile />} />
              <Route path="price-recommendations" element={<PriceRecommendations />} />
              <Route path="costs" element={<Costs />} />
              <Route path="competitors" element={<Competitors />} />
              <Route path="competitor/:competitorId" element={<CompetitorDetail />} />
              <Route path="product/:productId" element={<ProductDetail />} />
              <Route path="agents" element={<DynamicPricingAgents />} />
              
              {/* Subscription Management Routes */}
              <Route path="subscription-plans" element={<PricingPlans />} />
              <Route path="subscription-management" element={<SubscriptionManagement />} />
              
              <Route path="square-test" element={<SquareOrderTester />} />
              <Route path="integrations/square" element={<SquareIntegrationPage />} />
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Layout>
      </SubscriptionProvider>
    </AuthProvider>
  );
}

export default App;
