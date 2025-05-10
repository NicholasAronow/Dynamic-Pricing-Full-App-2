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
import PriceRecommendations from './components/pricing/PriceRecommendations';
import CompetitorAnalysis from './components/competitor/CompetitorAnalysis';
import CompetitorDetail from './components/competitor/CompetitorDetail';
import ProductDetail from './components/products/ProductDetail';

// Auth context
import { AuthProvider, useAuth } from './context/AuthContext';

const ProtectedRoute = ({ children }: { children: JSX.Element }) => {
  const { isAuthenticated } = useAuth();
  
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
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Layout>
    </AuthProvider>
  );
}

export default App;
